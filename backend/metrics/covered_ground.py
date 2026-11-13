"""Covered-ground metric: how much ground the building canopies and road pergola shelter.

Method: backend/metrics/CANOPY.md. Geometry comes from backend/cover.py.
"""
from shapely.geometry import Polygon
from shapely.ops import unary_union
from .. import parameters as P

EMPTY = Polygon()


def covered_ground(L: dict, canopy, pergola, crowns=None, *,
                   canopy_green=P.CANOPY_GREEN_FRACTION, pergola_green=P.PERGOLA_GREEN_FRACTION,
                   canopy_sun=P.CANOPY_SUN_FACTOR, canopy_rain=P.CANOPY_RAIN_FACTOR,
                   pergola_sun=P.PERGOLA_SUN_FACTOR, pergola_rain=P.PERGOLA_RAIN_FACTOR) -> dict:
    """How much ground the canopies and pergola cover, inside the corridor.

    canopy, pergola: shapely geometries. crowns: optional tree crown geometry for the
    selected year, used only for the combined 'sheltered route' figure.
    Areas in m2, volumes in m3, shares in %.
    """
    corr = L["corridor"]
    bld = L["bld_union"] if L.get("bld_union") is not None else (unary_union([b for b, _ in L["buildings"]]) if L["buildings"] else EMPTY)
    public = corr.difference(bld) if not bld.is_empty else corr
    road = L["road"]

    per_c = pergola.intersection(public) if not pergola.is_empty else EMPTY
    can_c = canopy.intersection(public).difference(per_c) if not canopy.is_empty else EMPTY
    built = unary_union([g for g in (can_c, per_c) if not g.is_empty]) if (not can_c.is_empty or not per_c.is_empty) else EMPTY
    built_area = built.area
    walk_ground = can_c.difference(road) if not road.is_empty and not can_c.is_empty else can_c

    green_can = can_c.area * canopy_green
    green_per = per_c.area * pergola_green
    green_m2 = green_can + green_per
    sun_m2 = can_c.area * canopy_sun + per_c.area * pergola_sun
    rain_m2 = can_c.area * canopy_rain + per_c.area * pergola_rain

    # Sheltered route: centreline under canopies/pergola, and with tree crowns added
    line = L["centreline"]
    walk = line.buffer(P.WALK_ZONE_HALF_WIDTH_M, cap_style="flat").intersection(corr)
    reach = P.SHADE_REACH_M
    def route_pct(g):
        if g is None or g.is_empty:
            return 0.0
        return 100.0 * line.intersection(g.buffer(reach)).length / line.length
    all_cover = unary_union([g for g in (built, crowns) if g is not None and not g.is_empty]) \
        if (not built.is_empty or (crowns is not None and not crowns.is_empty)) else EMPTY

    return dict(
        canopy_m2=can_c.area,
        canopy_total_m2=canopy.area,
        pergola_m2=per_c.area,
        covered_m2=built_area,
        covered_public_pct=100.0 * built_area / public.area if public.area else 0.0,
        pedestrian_covered_m2=walk_ground.area,
        road_covered_pct=100.0 * per_c.area / road.intersection(corr).area
            if not road.is_empty and road.intersection(corr).area else 0.0,
        sun_sheltered_m2=sun_m2,
        rain_sheltered_m2=rain_m2,
        green_on_structures_m2=green_m2,
        green_retention_m3=(green_can * min(P.GREEN_ROOF_RETENTION_L_M2, P.DESIGN_RAIN_MM * canopy_rain)
                           + green_per * min(P.GREEN_ROOF_RETENTION_L_M2, P.DESIGN_RAIN_MM * pergola_rain)) / 1000.0,
        rain_kept_off_m3=rain_m2 * P.DESIGN_RAIN_MM / 1000.0,
        walk_zone_covered_pct=100.0 * walk.intersection(built).area / walk.area
            if walk.area and not built.is_empty else 0.0,
        route_sheltered_structures_pct=route_pct(built),
        route_sheltered_all_pct=route_pct(all_cover),
    )
