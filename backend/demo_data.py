"""Synthetic stand-in data so the app runs before the real layers are ready.
Geometry is invented; only the rough location (Fellenoord, Eindhoven) is real."""
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity

_to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)


def make_demo(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    lonlat = [(5.4760, 51.4447), (5.4788, 51.4443), (5.4815, 51.4437), (5.4842, 51.4433)]
    pts = [_to_rd.transform(lon, lat) for lon, lat in lonlat]
    centreline = LineString(pts)
    corridor = centreline.buffer(20, cap_style="flat")

    road = centreline.parallel_offset(7, "left").buffer(3.5, cap_style="flat")
    utilities = centreline.parallel_offset(15, "right").buffer(1.2, cap_style="flat")

    buildings = []
    for d in np.arange(20, centreline.length - 20, 46):
        p = centreline.interpolate(d)
        q = centreline.interpolate(d + 1)
        ang = np.degrees(np.arctan2(q.y - p.y, q.x - p.x))
        for side in (-1, 1):
            if rng.random() < 0.15:
                continue
            w, h = rng.uniform(26, 38), rng.uniform(14, 22)
            off = 20 + h / 2 + rng.uniform(1, 5)
            nx, ny = -(q.y - p.y), (q.x - p.x)
            cx, cy = p.x + side * nx * off, p.y + side * ny * off
            b = affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), ang, origin=(cx, cy))
            buildings.append((b, float(rng.choice([12, 18, 24, 36, 48, 70]))))

    unpaved = []
    for _ in range(9):
        p = centreline.interpolate(rng.uniform(10, centreline.length - 10))
        unpaved.append(Point(p.x + rng.uniform(-14, 14), p.y + rng.uniform(-14, 14)).buffer(rng.uniform(6, 13)))
    unpaved = unary_union(unpaved).intersection(corridor).difference(road)

    trees = []
    for _ in range(11):
        p = centreline.interpolate(rng.uniform(5, centreline.length - 5))
        pt = Point(p.x + rng.uniform(-16, 16), p.y + rng.uniform(-16, 16))
        if corridor.contains(pt) and not road.contains(pt):
            trees.append((pt, float(rng.uniform(2.5, 5.0))))

    wet = Point(pts[-1]).buffer(90)   # near the Dommel end
    return dict(corridor=corridor, centreline=centreline, buildings=buildings, road=road,
                utilities=utilities, unpaved=unpaved, existing_trees=trees, wet_zone=wet, demo=True)
