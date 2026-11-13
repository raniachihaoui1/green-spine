"""Heat stress: share of the walking route in shade at 15:00 on 21 June.

Method: backend/metrics/HEAT_STRESS.md. Parameters: backend/parameters.py, section 9.
"""
import datetime as dt
import math
import numpy as np
import shapely
from .. import parameters as P
from .. import sun
from ..model import _all_crowns, survival_share


def check_position() -> dict:
    """Sun altitude and azimuth at HEAT_CHECK_HOUR_LOCAL on the design day."""
    utc = P.HEAT_CHECK_HOUR_LOCAL - P.UTC_OFFSET_H
    month, dom = P.DESIGN_DAY
    n = dt.date(2026, month, dom).timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1 + (utc - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    ha = math.radians((utc * 60 + eqtime + 4 * P.LON) / 4 - 180)
    la = math.radians(P.LAT)
    alt = math.asin(math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha))
    az = math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(decl) * math.cos(la)) + math.pi
    return dict(utc=utc, alt=math.degrees(alt), az=math.degrees(az) % 360)


def _raised_shadow(geom, height, pos):
    """Ground shadow of a flat roof (canopy, pergola) at `height` m."""
    if geom is None or geom.is_empty:
        return None
    dx, dy = sun._shift(height, pos["alt"], pos["az"])
    return shapely.transform(geom, lambda xy: xy + np.array([dx, dy]))


def heat_stress(trees, L: dict, year: int, canopies=None, pergola=None) -> dict:
    """Share of the route (sample points every ROUTE_STEP m) in shade at the check time,
    from buildings, kept existing canopy, new trees in `year`, and the canopies and pergola."""
    R = L.get("route")
    if R is None:
        from ..model import route_base
        R = route_base(L)
    pos = check_position()
    if pos["alt"] <= 0:
        return dict(shaded_pct=100.0, pos=pos, by_buildings_pct=100.0)
    x, y = R["x"], R["y"]
    bld = sun.building_shade(x, y, L["buildings"], [pos])[0]
    tx, ty, tr = _all_crowns(trees, L, year)
    tre = sun.tree_shade(x, y, tx, ty, tr, [pos])[0]
    pts = shapely.points(x, y)
    transmission = np.ones(len(x))
    for geom, h, factor in ((canopies, P.CANOPY_HEIGHT_M, P.CANOPY_SUN_FACTOR),
                             (pergola, P.PERGOLA_HEIGHT_M, P.PERGOLA_SUN_FACTOR)):
        if not 0 <= factor <= 1:
            raise ValueError("Shelter sun factors must be between zero and one.")
        s = _raised_shadow(geom, h, pos)
        if s is not None:
            shapely.prepare(s)
            transmission *= 1 - factor * shapely.covers(s, pts)
    shaded = np.where(bld | tre, 1.0, 1 - transmission)
    base_x, base_y, base_r = _all_crowns(trees.iloc[:0], L, year)
    base_tree = sun.tree_shade(x, y, base_x, base_y, base_r, [pos])[0]
    baseline = np.where(bld | base_tree, 1.0, 1 - transmission).mean()
    return dict(shaded_pct=100.0 * shaded.mean(),
                survival_adjusted_shaded_pct=100 * (baseline + (shaded.mean() - baseline) * survival_share(trees, year)),
                by_buildings_pct=100.0 * bld.mean(), by_trees_pct=100.0 * (tre & ~bld).mean(),
                by_structures_pct=100.0 * ((1 - transmission) * ~bld * ~tre).mean(), pos=pos)
