"""Built shelter geometry: building canopies and the road pergola.

All geometry is in RD (EPSG:28992). Every number comes from backend/parameters.py,
or from the arguments the dashboard passes in.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from . import parameters as P

EMPTY = Polygon()


def _parts(geom):
    if geom is None or geom.is_empty:
        return []
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


# ---------------------------------------------------------------------------
# Canopies
# ---------------------------------------------------------------------------
def facade_canopies(footprint, width=P.CANOPY_WIDTH_M, extension_pct=P.CANOPY_EXTENSION_PCT,
                    min_facade=P.CANOPY_MIN_FACADE_M):
    """Canopy strips along every outer facade of one building footprint.

    Each facade gets a rectangle `width` deep, measured outward. Its length is the facade
    length plus `extension_pct` % of that length, split evenly over both ends, so the
    canopy runs past the building corners.
    Returns (canopy geometry, total facade length that got a canopy).
    """
    rects, facade_len = [], 0.0
    for poly in _parts(footprint):
        ring = list(orient(poly, sign=1.0).exterior.coords)   # counter-clockwise: outside is to the right
        for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            if length < min_facade:
                continue
            ux, uy = dx / length, dy / length
            nx, ny = uy, -ux                                  # outward normal
            ext = length * extension_pct / 100.0 / 2.0
            a = (x0 - ux * ext, y0 - uy * ext)
            b = (x1 + ux * ext, y1 + uy * ext)
            rects.append(Polygon([a, b, (b[0] + nx * width, b[1] + ny * width),
                                  (a[0] + nx * width, a[1] + ny * width)]))
            facade_len += length
    return (unary_union(rects) if rects else EMPTY), facade_len


def building_canopies(L: dict, min_height=P.CANOPY_MIN_BUILDING_HEIGHT_M, width=P.CANOPY_WIDTH_M,
                      extension_pct=P.CANOPY_EXTENSION_PCT, avoid_road=P.CANOPY_AVOID_ROAD):
    """Canopies on every building taller than `min_height`.

    Canopies are cut back where they would run into any building footprint and, if
    `avoid_road`, where they would overhang the carriageway.
    Returns dict(geom, per_building=[(footprint, height, canopy)], facade_m, n_buildings).
    """
    tall = [(b, h) for b, h in L["buildings"] if h > min_height]
    all_fp = L["bld_union"] if L.get("bld_union") is not None else (unary_union([b for b, _ in L["buildings"]]) if L["buildings"] else EMPTY)
    cut = all_fp
    if avoid_road and not L["road"].is_empty:
        cut = unary_union([all_fp, L["road"]])
    per, facade_m = [], 0.0
    for b, h in tall:
        geom, flen = facade_canopies(b, width, extension_pct)
        geom = geom.difference(cut) if not cut.is_empty else geom
        if geom.is_empty:
            continue
        per.append((b, h, geom))
        facade_m += flen
    geom = unary_union([g for _, _, g in per]) if per else EMPTY
    return dict(geom=geom, per_building=per, facade_m=facade_m, n_buildings=len(per))


# ---------------------------------------------------------------------------
# Road pergola
# ---------------------------------------------------------------------------
def _equivalent_width(poly):
    """Width of the rectangle with the same area and perimeter (good for long road strips)."""
    a, p = poly.area, poly.length
    half = p / 2.0
    disc = half * half - 4.0 * a
    return (half - math.sqrt(max(disc, 0.0))) / 2.0


def _length_band(poly, length_pct):
    """A band across `poly`, centred on its middle, covering `length_pct` % of its long axis."""
    rect = poly.minimum_rotated_rectangle
    c = list(rect.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
    e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    ax = e1 if math.hypot(*e1) >= math.hypot(*e2) else e2
    length = math.hypot(*ax)
    ux, uy = ax[0] / length, ax[1] / length
    nx, ny = -uy, ux
    cx, cy = rect.centroid.x, rect.centroid.y
    half_l = length * length_pct / 100.0 / 2.0
    big = length + 1000.0
    return Polygon([(cx - ux * half_l - nx * big, cy - uy * half_l - ny * big),
                    (cx + ux * half_l - nx * big, cy + uy * half_l - ny * big),
                    (cx + ux * half_l + nx * big, cy + uy * half_l + ny * big),
                    (cx - ux * half_l + nx * big, cy - uy * half_l + ny * big)])


def road_pergola(road, width_pct=P.PERGOLA_ROAD_PCT, length_pct=P.PERGOLA_LENGTH_PCT):
    """Pergola strip over the middle of the carriageway.

    Per road polygon: the strip is `width_pct` % of the road width, centred on the road
    axis (made with an inward buffer), and covers `length_pct` % of the road length,
    centred on the middle of that road section.
    """
    if width_pct <= 0 or length_pct <= 0 or road is None or road.is_empty:
        return EMPTY
    strips = []
    for poly in _parts(road):
        w = _equivalent_width(poly)
        inset = w * (1.0 - min(width_pct, 100.0) / 100.0) / 2.0
        strip = poly.buffer(-inset, join_style="mitre") if inset > 0 else poly
        if strip.is_empty:
            continue
        if length_pct < 100.0:
            strip = strip.intersection(_length_band(poly, length_pct))
        strips.append(strip)
    return unary_union(strips) if strips else EMPTY


# The covered-ground analysis moved to backend/metrics/covered_ground.py
from .metrics.covered_ground import covered_ground  # noqa: E402,F401
