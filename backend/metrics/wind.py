"""Wind index: share of tall-building facade along the corridor that has shelter next to it.

A geometric proxy, not a wind simulation. Method: backend/metrics/WIND_INDEX.md.
Parameters: backend/parameters.py, section 9.
"""
import shapely
from shapely.geometry import LineString
from shapely.ops import unary_union
from .. import parameters as P
from ..model import canopy_geometry


def tall_facades(L: dict):
    """Exterior walls of buildings taller than WIND_TALL_BUILDING_M within WIND_CORRIDOR_REACH_M of the corridor.
    Cached in L, because the buildings do not change between options."""
    key = ("tall_facades", P.WIND_TALL_BUILDING_M, P.WIND_CORRIDOR_REACH_M)
    if key not in L:
        L[key] = _tall_facades(L)
    return L[key]


def _tall_facades(L: dict):
    reach = L["corridor"].buffer(P.WIND_CORRIDOR_REACH_M)
    walls, n = [], 0
    for b, h in L["buildings"]:
        if h <= P.WIND_TALL_BUILDING_M or not b.intersects(reach):
            continue
        n += 1
        for p in (b.geoms if hasattr(b, "geoms") else [b]):
            walls.append(LineString(p.exterior.coords))
    lines = unary_union(walls).intersection(reach) if walls else None
    return lines, n


def wind_index(trees, L: dict, year: int, canopies=None, crowns=None) -> dict:
    """Share of tall-building facade length along the corridor with a tree crown within
    WIND_SHELTER_REACH_M (index_pct), and with a tree crown or a building canopy (with_canopies_pct).
    The canopies line every tall facade by design, so they are reported separately."""
    lines, n = tall_facades(L)
    if lines is None or lines.is_empty:
        return dict(index_pct=None, with_canopies_pct=None, n_buildings=0, facade_m=0.0, sheltered_m=0.0)
    crowns = canopy_geometry(trees, L, year) if crowns is None else crowns
    near = shapely.box(*lines.bounds).buffer(P.WIND_SHELTER_REACH_M)
    zone = crowns.intersection(near).buffer(P.WIND_SHELTER_REACH_M)
    by_trees = lines.intersection(zone).length
    with_can = by_trees
    if canopies is not None and not canopies.is_empty:
        with_can = lines.intersection(unary_union([zone, canopies.intersection(near).buffer(P.WIND_SHELTER_REACH_M)])).length
    return dict(index_pct=100.0 * by_trees / lines.length, with_canopies_pct=100.0 * with_can / lines.length,
                n_buildings=n, facade_m=lines.length, sheltered_m=by_trees)
