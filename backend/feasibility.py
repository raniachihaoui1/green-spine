"""Conservative rooting-space screening. Unknown evidence is never a construction approval."""
import math

import shapely
from shapely.geometry import Point, Polygon

from . import parameters as P


def rootable_ground(L):
    blocked = shapely.union_all([L.get("bld_union", Polygon()), L["road"],
                                L["utilities"], L.get("water", Polygon()),
                                L.get("underground", Polygon())])
    return L["corridor"].difference(blocked)


def rooting_space(x, y, size_class, paved, L, available, allow_engineering, reserved=()):
    cls = P.TREE_CLASSES[size_class]
    point = Point(x, y)
    zones = [(g, props) for g, props in L.get("soil_zones", []) if g.covers(point)]
    if len(zones) > 1:
        raise ValueError("Overlapping soil zones: rooting depth is ambiguous.")
    depth = P.SOIL_ASSUMED_USABLE_DEPTH_M
    surveyed = False
    if zones:
        zone, props = zones[0]
        value = props.get("usable_depth_m")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("Soil zones need a non-negative usable_depth_m after groundwater allowance.")
        if not props.get("source"):
            raise ValueError("Soil zones need a source for their usable rooting depth.")
        depth, surveyed = float(value), True
    if depth < cls["root_depth"]:
        return None, "Insufficient usable rooting depth"
    potential = point.buffer(cls["r_mature"]).intersection(available)
    if reserved:
        indices = shapely.STRtree(reserved).query(potential, predicate="intersects")
        if len(indices):
            potential = potential.difference(shapely.union_all([reserved[i] for i in indices]))
    if zones:
        potential = potential.intersection(zone)
    natural = potential.intersection(L["unpaved"])
    engineered = paved or natural.area * depth < cls["soil_m3"]
    if engineered and not allow_engineering:
        return None, "Requires engineered rooting space"
    root = potential if engineered else natural
    if root.area * depth < cls["soil_m3"]:
        return None, "Insufficient unallocated rooting volume"
    # Reserve the entire candidate root zone, conservatively preventing double allocation.
    return dict(engineered=engineered, soil_m3=cls["soil_m3"],
                available_soil_m3=root.area * depth, usable_depth_m=depth,
                depth_evidence="surveyed" if surveyed else "assumed",
                root_zone_wkt=root.wkt, root_area_m2=root.area,
                feasibility="conditional",
                reason="Confirm utilities, groundwater, compaction and access"
                       + ("; provide engineered rooting space" if engineered else "")), None


def unsealed_ground(trees, L):
    """Mapped open ground plus proposed pits, clipped once to public, non-road ground."""
    ground = rootable_ground(L)
    surface = L["corridor"].difference(shapely.union_all([
        L.get("bld_union", Polygon()), L["road"], L.get("water", Polygon())]))
    pits = []
    for t in trees.itertuples():
        if bool(getattr(t, "paved", getattr(t, "engineered", False))):
            pits.append(Point(t.x, t.y).buffer(math.sqrt(P.ECO_TREE_PIT_M2 / math.pi)))
    return shapely.union_all([L["unpaved"].intersection(surface),
                              shapely.union_all(pits).intersection(ground)])
