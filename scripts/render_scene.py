"""Render exported scene JSON locally with Blender 4.5+. No pip packages are needed.

blender --background --python scripts/render_scene.py -- --scene scene.json --output proposal
Writes a self-contained .blend and a denoised Cycles .png. Materials and trees are illustrative.
"""
import argparse
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector


def material(name, color, style):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = style["roughness"]
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = style["noise_scale"]
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = style["bump_strength"]
    bump.inputs["Distance"].default_value = style["bump_distance_m"]
    mat.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    mat.node_tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def mesh_object(name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj


def surface_mesh(surface):
    vertices, faces = [], []
    base, top = surface["base"], surface["base"] + surface["height"]
    for triangle in surface["triangles"]:
        start = len(vertices)
        vertices.extend((x, y, top) for x, y in triangle)
        faces.append(tuple(range(start, start + len(triangle))))
    if surface["height"]:
        for ring in surface["rings"]:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                start = len(vertices)
                vertices.extend([(a[0], a[1], base), (b[0], b[1], base),
                                 (b[0], b[1], top), (a[0], a[1], top)])
                faces.append(tuple(range(start, start + 4)))
    return vertices, faces


def tree_templates(data, materials):
    rng = random.Random(data["style"]["seed"])
    style = data["style"]
    lower, upper = data["crown_base"], data["crown_top"]
    vertices, faces = [], []
    for _ in range(style["leaf_count"]):
        z = rng.uniform(-1, 1)
        theta = rng.uniform(0, math.tau)
        radial = math.sqrt(1 - z * z) * math.sqrt(rng.random())
        point = Vector((radial * math.cos(theta), radial * math.sin(theta),
                        (upper + lower) / 2 + z * (upper - lower) / 2))
        side = Vector((math.cos(theta), math.sin(theta), rng.uniform(-1, 1))).normalized()
        other = side.cross(Vector((0, 0, 1))).normalized()
        size = style["leaf_size_radius_ratio"]
        start = len(vertices)
        for direction in (side, other, -side, -other):
            vertex = point + direction * size
            radius = math.hypot(vertex.x, vertex.y)
            if radius > 1:
                vertex.x /= radius
                vertex.y /= radius
            vertex.z = max(lower, min(upper, vertex.z))
            vertices.append(tuple(vertex))
        faces.extend([(start, start + 1, start + 2), (start, start + 2, start + 3)])
    foliage = mesh_object("Illustrative foliage template", vertices, faces, materials["leaf"])
    verts, quads = [], []

    def branch(a, b, radius):
        axis = (b - a).normalized()
        u = axis.cross(Vector((0, 1, 0))).normalized()
        v = axis.cross(u).normalized()
        start = len(verts)
        sides = style["cylinder_sides"]
        for p, taper in ((a, 1), (b, 0.45)):
            for j in range(sides):
                t = math.tau * j / sides
                verts.append(tuple(p + radius * taper * (u * math.cos(t) + v * math.sin(t))))
        for j in range(sides):
            k = (j + 1) % sides
            quads.append((start + j, start + k, start + sides + k, start + sides + j))

    branch(Vector((0, 0, 0)), Vector((0, 0, upper)), style["trunk_radius_ratio"])
    for j in range(style["branch_count"]):
        angle = j * math.tau / style["branch_count"]
        z = rng.uniform(lower, upper)
        reach = math.sqrt(max(0, 1 - ((z - (upper + lower) / 2) / ((upper - lower) / 2)) ** 2))
        branch(Vector((0, 0, max(lower, z - lower / 2))),
               Vector((reach * math.cos(angle), reach * math.sin(angle), z)),
               style["trunk_radius_ratio"] / 3)
    wood = mesh_object("Illustrative branch template", verts, quads, materials["bark"])
    return foliage, wood


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    data = json.loads(args.scene.read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        raise ValueError("Unsupported scene data version")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    style = data["style"]
    mats = {name: material(name, style[name], style)
            for name in ("ground", "road", "green", "building", "leaf", "bark", "water", "structure", "backdrop")}
    span = max(data["size"])
    bpy.ops.mesh.primitive_plane_add(size=span * style["backdrop_span_ratio"],
                                    location=(0, 0, -style["surface_offset_m"]))
    bpy.context.object.name = "Studio backdrop - not site data"
    bpy.context.object.data.materials.append(mats["backdrop"])
    for surface in data["surfaces"]:
        vertices, faces = surface_mesh(surface)
        mesh_object(surface["material"], vertices, faces, mats[surface["material"]])
    templates = tree_templates(data, mats)
    for tree in data["trees"]:
        for template in templates:
            obj = bpy.data.objects.new(tree["status"], template.data)
            bpy.context.collection.objects.link(obj)
            obj.location = (tree["x"], tree["y"], 0)
            obj.scale = (tree["r"],) * 3
    for obj in templates:
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = data["render"]["samples"]
    scene.cycles.use_denoising = True
    scene.render.resolution_x = data["render"]["width"]
    scene.render.resolution_y = data["render"]["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(data["sun"]["alt"])
    sky.sun_rotation = math.radians(data["sun"]["az"])
    sky.sun_disc = False
    background = nodes.get("Background")
    background.inputs["Strength"].default_value = style["sky_strength"]
    scene.world.node_tree.links.new(sky.outputs["Color"], background.inputs["Color"])
    sun = bpy.data.lights.new("21 June 15:00 solar position", "SUN")
    sun.energy, sun.angle = style["sun_energy"], style["sun_angle_rad"]
    light = bpy.data.objects.new("Sun", sun)
    bpy.context.collection.objects.link(light)
    alt, az = math.radians(data["sun"]["alt"]), math.radians(data["sun"]["az"])
    direction = Vector((-math.sin(az) * math.cos(alt), -math.cos(az) * math.cos(alt), -math.sin(alt)))
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera = bpy.data.objects.new("Fixed comparison camera", bpy.data.cameras.new("Camera"))
    bpy.context.collection.objects.link(camera)
    camera.location = (0, -span * style["aerial_distance_ratio"], span * style["aerial_height_ratio"])
    camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = span * style["camera_margin_ratio"]
    camera.data.clip_end = span * 10
    scene.camera = camera
    scene.render.use_stamp = True
    scene.render.use_stamp_note = True
    scene.render.stamp_note_text = f"{data['title']} | {data['year']} | {data['disclaimer']}"
    scene.render.stamp_font_size = style["stamp_font_px"]
    scene.render.stamp_foreground = (0.05, 0.08, 0.06, 1)
    scene.render.stamp_background = (1, 1, 1, 0.8)
    for flag in ("date", "time", "frame", "camera", "scene", "filename", "render_time", "memory", "hostname"):
        setattr(scene.render, f"use_stamp_{flag}", False)
    scene["source_reference"] = json.dumps(data["reference"])
    scene["origin_rd"] = data["origin_rd"]
    scene["assessment_disclaimer"] = data["disclaimer"]
    scene.render.filepath = str(args.output.with_suffix(".png").resolve())
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.with_suffix(".blend").resolve()))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
