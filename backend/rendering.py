"""Portable, metre-based scene data for local Blender rendering; never sends data externally."""
import shapely
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from . import parameters as P
from .facades import strip
from .metrics.heat import check_position
from .model import _kept, crown_radius


def _parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [p for g in getattr(geom, "geoms", []) for p in _parts(g)]


def _surface(geom, origin, base=0.0, height=0.0):
    ox, oy = origin
    rows = []
    for poly in _parts(geom):
        poly = orient(poly, sign=1.0)
        def coords(ring):
            return [[float(x - ox), float(y - oy)] for x, y, *_ in ring.coords[:-1]]
        triangles = [coords(orient(t, sign=1.0).exterior)
                     for t in shapely.get_parts(shapely.constrained_delaunay_triangles(poly))]
        rows.append(dict(rings=[coords(poly.exterior), *[coords(r) for r in poly.interiors]],
                         triangles=triangles, base=base, height=float(height)))
    return rows


def scene_package(L, trees, year, canopies, pergola, facades, title):
    centre = L["corridor"].centroid
    origin = (centre.x, centre.y)
    context = L["corridor"].buffer(P.RENDER_CONTEXT_M)
    surfaces = []
    offset = P.RENDER_STYLE["surface_offset_m"]
    for name, geom, base, height in (
        ("ground", context, 0, 0),
        ("road", L["road"].intersection(context), offset, 0),
        ("green", L["unpaved"].intersection(context), offset * 2, 0),
        ("water", L.get("water", Polygon()).intersection(context), offset * 3, 0),
        ("structure", canopies, P.CANOPY_HEIGHT_M, P.CANOPY_THICKNESS_M),
        ("structure", pergola, P.PERGOLA_HEIGHT_M, P.CANOPY_THICKNESS_M),
    ):
        surfaces.extend(dict(material=name, **s) for s in _surface(geom, origin, base, height))
    by_height = {}
    for footprint, height in L["buildings"]:
        if footprint.intersects(context):
            by_height.setdefault(height, []).append(footprint)
    for height, footprints in by_height.items():
        surfaces.extend(dict(material="building", **s)
                        for s in _surface(shapely.union_all(footprints), origin, 0, height))
    for band in facades["bands"].itertuples():
        surfaces.extend(dict(material="leaf", **s)
                        for s in _surface(strip(band), origin, band.band_bottom, band.green_h))
    vegetation = [dict(x=float(t.x - centre.x), y=float(t.y - centre.y), r=float(t.r), status="existing")
                  for t in _kept(trees, L).itertuples()]
    for frame, status in ((trees, "proposal"), (L.get("committed"), "committed")):
        if frame is None or frame.empty:
            continue
        for t in frame.itertuples():
            planted = getattr(t, "planting_year", P.BASE_YEAR)
            if planted > year:
                continue
            radius = float(crown_radius([t.size_class], year, planted)[0])
            vegetation.append(dict(x=float(t.x - centre.x), y=float(t.y - centre.y), r=radius, status=status))
    minx, miny, maxx, maxy = L["corridor"].bounds
    return dict(schema_version=1, title=title, year=year, crs="EPSG:28992", origin_rd=list(origin),
                disclaimer="INDICATIVE: massing, materials and vegetation are not a surveyed architectural design.",
                reference=L["reference"], surfaces=surfaces, trees=vegetation,
                size=[maxx - minx, maxy - miny], sun=check_position(),
                crown_base=P.CROWN_BASE, crown_top=P.CROWN_TOP,
                style=P.RENDER_STYLE,
                render=dict(width=P.RENDER_WIDTH, height=P.RENDER_HEIGHT, samples=P.RENDER_SAMPLES))
