"""Direct-sun hours from sun positions and shadow geometry.

Simplifications: clear sky, one design day, flat ground, buildings as extruded
footprints, tree crowns as discs. Direct sun only (no diffuse or reflected light).
Coordinates are EPSG:28992; grid north is treated as true north (the difference
at Eindhoven is far below one degree).
"""
import datetime as dt
import numpy as np
import shapely
from . import config as C


def sun_positions(day=None, lat=None, lon=None, step_h=None, min_alt=None):
    """Sun (altitude, azimuth) in degrees for every time step of the design day
    with the sun above min_alt. Azimuth is clockwise from north. Times are UTC hours."""
    month, dom = day or C.DESIGN_DAY
    lat = C.LAT if lat is None else lat
    lon = C.LON if lon is None else lon
    step_h = C.SUN_STEP_H if step_h is None else step_h
    min_alt = C.MIN_SUN_ALTITUDE if min_alt is None else min_alt

    n = dt.date(2026, month, dom).timetuple().tm_yday
    utc = np.arange(step_h / 2, 24, step_h)
    g = 2 * np.pi / 365 * (n - 1 + (utc - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                       - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))          # minutes
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    solar_time = utc * 60 + eqtime + 4 * lon                                           # minutes
    ha = np.radians(solar_time / 4 - 180)
    la = np.radians(lat)
    alt = np.arcsin(np.sin(la) * np.sin(decl) + np.cos(la) * np.cos(decl) * np.cos(ha))
    az = np.arctan2(np.sin(ha), np.cos(ha) * np.sin(la) - np.tan(decl) * np.cos(la)) + np.pi
    alt, az = np.degrees(alt), np.degrees(az) % 360
    keep = alt >= min_alt
    return [dict(utc=float(t), alt=float(a), az=float(z)) for t, a, z in zip(utc[keep], alt[keep], az[keep])]


def _shift(height, alt, az):
    """Ground offset (dx, dy) of the shadow of a point at this height."""
    length = height / np.tan(np.radians(alt))
    return -np.sin(np.radians(az)) * length, -np.cos(np.radians(az)) * length


def building_shadow(footprint, height, alt, az):
    """Ground shadow of an extruded footprint: the footprint swept away from the sun."""
    dx, dy = _shift(height, alt, az)
    parts = [footprint]
    polys = list(footprint.geoms) if hasattr(footprint, "geoms") else [footprint]
    for p in polys:
        xy = np.asarray(p.exterior.coords)
        seg = np.stack([xy[:-1], xy[1:], xy[1:] + (dx, dy), xy[:-1] + (dx, dy)], axis=1)   # one quad per wall
        parts.extend(shapely.convex_hull(shapely.multipoints(seg)))
    return shapely.union_all(parts)


def _walls(buildings):
    """All exterior wall segments of the buildings as one array, with the building height per wall."""
    a, b, h = [], [], []
    for geom, height in buildings:
        for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            xy = np.asarray(p.exterior.coords)[:, :2]
            a.append(xy[:-1]); b.append(xy[1:]); h.append(np.full(len(xy) - 1, height))
    return np.concatenate(a), np.concatenate(b), np.concatenate(h)


def building_shade(xs, ys, buildings, positions=None):
    """Boolean matrix [time step, point]: True where a building shades the point.
    A point is shaded when it lies in the swept shadow of any wall (or under a footprint)."""
    positions = positions or sun_positions()
    pts = shapely.points(np.asarray(xs, float), np.asarray(ys, float))
    out = np.zeros((len(positions), len(pts)), bool)
    if not buildings or len(pts) == 0:
        return out
    minx, miny, maxx, maxy = shapely.total_bounds(pts)
    area = shapely.box(minx, miny, maxx, maxy)
    reach = 1 / np.tan(np.radians(min(p["alt"] for p in positions)))
    near = [(b, h) for b, h in buildings if h > 0 and b.distance(area) <= h * reach]
    if not near:
        return out
    a, b, h = _walls(near)
    feet = np.array([g for g, _ in near], dtype=object)
    for i, p in enumerate(positions):
        dx, dy = _shift(h, p["alt"], p["az"])
        d = np.stack([dx, dy], axis=1)
        quads = shapely.convex_hull(shapely.multipoints(np.stack([a, b, b + d, a + d], axis=1)))
        tree = shapely.STRtree(np.concatenate([quads, feet]))
        hit, _ = tree.query(pts, predicate="within")
        out[i, np.unique(hit)] = True
    return out


def tree_shade(xs, ys, tx, ty, tr, positions=None):
    """Boolean matrix [time step, point]: True where a tree crown shades the point.
    A crown is a disc of radius r spanning heights CROWN_BASE*r to CROWN_TOP*r, so its
    shadow is every point within r of the line between the two shifted disc centres."""
    positions = positions or sun_positions()
    px, py = np.asarray(xs, float), np.asarray(ys, float)
    cx, cy, r = np.asarray(tx, float), np.asarray(ty, float), np.asarray(tr, float)
    out = np.zeros((len(positions), len(px)), bool)
    if len(cx) == 0 or len(px) == 0:
        return out
    r2 = (r * r)[None, :]
    for i, p in enumerate(positions):
        sx, sy = _shift(C.CROWN_BASE * r, p["alt"], p["az"])                  # centre of the lower disc's shadow
        dx, dy = _shift((C.CROWN_TOP - C.CROWN_BASE) * r, p["alt"], p["az"])  # from there to the upper disc's
        dd = np.maximum(dx * dx + dy * dy, 1e-12)
        for s in range(0, len(px), 4000):                       # chunks keep memory small
            wx = px[s:s + 4000, None] - (cx + sx)[None, :]
            wy = py[s:s + 4000, None] - (cy + sy)[None, :]
            f = np.clip((wx * dx + wy * dy) / dd, 0, 1)
            wx -= f * dx
            wy -= f * dy
            out[i, s:s + 4000] = (wx * wx + wy * wy <= r2).any(axis=1)
    return out


def hours(shaded):
    """Direct-sun hours per point from a [time step, point] shade matrix."""
    return (~shaded).sum(axis=0) * C.SUN_STEP_H
