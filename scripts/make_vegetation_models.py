"""Build small low-poly 3D models for the Green Spine map: large tree, small tree, medium bush, low vegetation.

    python scripts/make_vegetation_models.py          (needs trimesh: pip install trimesh)

Writes to data/processed/vegetation_models/ (models are symbolic, not species-specific):
  <name>.glb          glTF, Y-up, one PBR material per colour (Blender, glTF viewers)
  <name>.obj          Z-up, metres, origin at the base centre (Rhino)
  <name>_foliage.glb  crown only, white, for the dashboard: deck.gl's ScenegraphLayer colours it with get_color
  <name>_trunk.glb    trunk only, white (trees only)
  models.json         reference sizes; backend/view.py scales the models with these
Sizes follow the tree classes (large > 18 m, small 6-12 m); bush and vegetation sizes are STARTING VALUES.
"""
import json
from pathlib import Path

import numpy as np
import trimesh

OUT = Path(__file__).resolve().parents[1] / "data" / "processed" / "vegetation_models"
RNG = np.random.default_rng(42)
BARK = [101, 76, 52, 255]
GREENS = {"large": [46, 110, 52, 255], "small": [86, 150, 70, 255],
          "bush": [70, 125, 60, 255], "veg": [140, 175, 85, 255]}


def blob(radius, height, center, color, subdiv=1, jitter=0.12):
    """Low-poly ellipsoid with a slightly irregular surface."""
    m = trimesh.creation.icosphere(subdivisions=subdiv, radius=1.0)
    v = m.vertices * (1 + RNG.uniform(-jitter, jitter, (len(m.vertices), 1)))
    v[:, :2] *= radius
    v[:, 2] *= height / 2
    m.vertices = v + center
    m.visual.vertex_colors = np.tile(color, (len(v), 1))
    return m


def trunk(height, diameter, sections=7):
    m = trimesh.creation.cylinder(radius=diameter / 2, height=height, sections=sections)
    m.apply_translation([0, 0, height / 2])
    m.visual.vertex_colors = np.tile(BARK, (len(m.vertices), 1))
    return m


def shade(color, f):
    return [int(min(255, c * f)) for c in color[:3]] + [255]


def large_tree():
    # 20 m tall, crown 12 m across, clear stem 6 m
    parts = [trunk(9.0, 0.7), blob(6.0, 11.0, [0, 0, 13.5], GREENS["large"], subdiv=2)]
    for a in np.linspace(0, 2 * np.pi, 4, endpoint=False):
        parts.append(blob(3.2, 5.0, [3.0 * np.cos(a), 3.0 * np.sin(a), 11.0 + RNG.uniform(-1, 1)],
                          shade(GREENS["large"], RNG.uniform(0.85, 1.1))))
    return parts, dict(height_m=20.0, crown_d_m=12.0, size_class="large")


def small_tree():
    # 8 m tall, crown 5 m across, clear stem 2.5 m
    parts = [trunk(4.0, 0.25), blob(2.5, 5.0, [0, 0, 5.5], GREENS["small"], subdiv=2)]
    return parts, dict(height_m=8.0, crown_d_m=5.0, size_class="small")


def medium_bush():
    # 2 m tall, 3 m across, multi-stem shrub without a visible trunk
    parts = [blob(1.1, 1.8, [0, 0, 0.95], GREENS["bush"])]
    for a in np.linspace(0, 2 * np.pi, 5, endpoint=False):
        r = RNG.uniform(0.55, 0.8)
        parts.append(blob(r, r * 1.5, [0.85 * np.cos(a), 0.85 * np.sin(a), r * 0.75],
                          shade(GREENS["bush"], RNG.uniform(0.85, 1.15))))
    return parts, dict(height_m=2.0, crown_d_m=3.0, size_class="bush")


def low_vegetation():
    # 2 x 2 m tile of grasses and herbs, up to 0.5 m
    parts = []
    for _ in range(30):
        x, y = RNG.uniform(-0.85, 0.85, 2)
        h = RNG.uniform(0.25, 0.5)
        c = trimesh.creation.cone(radius=RNG.uniform(0.12, 0.22), height=h, sections=5)
        c.apply_translation([x, y, 0])
        c.visual.vertex_colors = np.tile(shade(GREENS["veg"], RNG.uniform(0.8, 1.15)), (len(c.vertices), 1))
        parts.append(c)
    base = trimesh.creation.box(extents=[2.0, 2.0, 0.05])
    base.apply_translation([0, 0, 0.025])
    base.visual.vertex_colors = np.tile(shade(GREENS["veg"], 0.75), (len(base.vertices), 1))
    return parts + [base], dict(height_m=0.5, crown_d_m=2.0, size_class="vegetation")


def is_bark(m):
    return list(m.visual.vertex_colors[0]) == BARK


def to_scene(parts, transform):
    """glTF scene with one mesh per colour and a PBR material each. deck.gl's ScenegraphLayer ignores
    vertex colours, so the colours must sit in the materials."""
    groups = {}
    for m in parts:
        groups.setdefault(tuple(int(c) for c in m.visual.vertex_colors[0]), []).append(m)
    scene = trimesh.Scene()
    for i, (rgba, ms) in enumerate(groups.items()):
        g = trimesh.util.concatenate(ms)
        g.apply_transform(transform)
        mat = trimesh.visual.material.PBRMaterial(baseColorFactor=list(rgba), metallicFactor=0.0, roughnessFactor=0.9)
        g.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(g, geom_name=f"part_{i}")
    return scene


MODELS = {"large_tree": large_tree, "small_tree": small_tree,
          "medium_bush": medium_bush, "low_vegetation": low_vegetation}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    z_up_to_y_up = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    for name, fn in MODELS.items():
        parts, info = fn()
        mesh = trimesh.util.concatenate(parts)
        mesh.export(OUT / f"{name}.obj")                    # Z-up, metres (pydeck SimpleMeshLayer, Rhino)
        to_scene(parts, z_up_to_y_up).export(OUT / f"{name}.glb")   # Y-up glTF (Blender, viewers)
        files = [f"{name}.obj", f"{name}.glb"]
        # plain white parts for the map, coloured per tree in the dashboard (status, soil)
        for part, sel in (("foliage", [m for m in parts if not is_bark(m)]), ("trunk", [m for m in parts if is_bark(m)])):
            if sel:
                g = trimesh.util.concatenate([m.copy() for m in sel])
                g.apply_transform(z_up_to_y_up)
                g.visual = trimesh.visual.ColorVisuals(g, vertex_colors=[255, 255, 255, 255])
                g.export(OUT / f"{name}_{part}.glb")
                files.append(f"{name}_{part}.glb")
        info.update(faces=int(len(mesh.faces)), bounds_m=np.round(mesh.bounds, 2).tolist(),
                    files=files)
        meta[name] = info
        print(f"{name:15s} {len(mesh.faces):5d} faces  height {mesh.bounds[1][2]:.1f} m")
    (OUT / "models.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
