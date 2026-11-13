"""Green facades: climbing plants on the street-facing walls along the corridor.

1. Street facades: outer walls (>= FACADE_MIN_LENGTH_M) of buildings within FACADE_REACH_M of the
   corridor, facing the corridor.
2. Sun per wall: direct-sun hours on 21 June at the middle of each floor band, counting only the
   moments the sun is in front of the wall and not hidden by other buildings (backend/sun.py).
3. Greening: the sunniest walls first (they heat up most), until FACADE_GREEN_SHARE_PCT of the
   street-facade length is green, up to FACADE_MAX_HEIGHT_M or the building height.
4. Climber: from the team's soil-compatible plant list, plant type Vine, at least
   CLIMBER_MIN_HEIGHT_M tall, tolerant of the wall's sun class (database shade columns).
   The green height is capped by the climber's own mature height.
Method and limits: backend/metrics/GREEN_FACADES.md.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient

from . import parameters as P
from . import sun

SHADE_COL = {"full sun": "Shade: No shade (N)", "part shade": "Shade: Semi (S)", "full shade": "Shade: Full (F)"}


def _max_height(text):
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(text))]
    if not nums:
        return None
    return max(nums) / 100.0 if "cm" in str(text) and "m " not in str(text).replace("cm", "") else max(nums)


def climbers() -> pd.DataFrame:
    """Climbing plants from the soil-compatible list: species, max height (m), shade tolerance."""
    c = pd.read_csv(Path(P.PROCESSED_DIR) / "fellenoord_compatible_plants.csv", encoding="utf-8-sig")
    v = c[c.plant_type.astype(str).str.contains("Vine", case=False)].copy()
    v["height_m"] = v["Plant Height"].map(_max_height)
    v = v[v.height_m >= P.CLIMBER_MIN_HEIGHT_M]
    for cls, col in SHADE_COL.items():
        v[cls] = v[col].astype(str).str.upper().eq("TRUE")
    return v[["species", "plant_type", "height_m"] + list(SHADE_COL)].reset_index(drop=True)


def street_facades(L: dict) -> pd.DataFrame:
    """One row per street-facing wall segment: line, building height, outward normal."""
    corr = L["corridor"]
    reach = corr.buffer(P.FACADE_REACH_M)
    rows = []
    for bi, (b, h) in enumerate(L["buildings"]):
        if h < P.FACADE_BAND_M or not b.intersects(reach):
            continue
        for poly in (b.geoms if hasattr(b, "geoms") else [b]):
            ring = np.asarray(orient(poly, 1.0).exterior.coords)[:, :2]       # anticlockwise: outside on the right
            for a, c in zip(ring[:-1], ring[1:]):
                d = c - a
                length = float(np.hypot(*d))
                if length < P.FACADE_MIN_LENGTH_M:
                    continue
                n = np.array([d[1], -d[0]]) / length                          # outward normal
                mid = (a + c) / 2
                probe = shapely.Point(*(mid + n * 0.5))
                if not reach.contains(probe):
                    continue
                near = shapely.ops.nearest_points(corr, probe)[0]
                to_corr = np.array([near.x - mid[0], near.y - mid[1]])
                if np.hypot(*to_corr) > 0.5 and float(n @ to_corr) <= 0:        # wall turns its back on the corridor
                    continue
                rows.append(dict(building=bi, height=h, x0=a[0], y0=a[1], x1=c[0], y1=c[1],
                                 nx=n[0], ny=n[1], length=length, mx=mid[0] + n[0] * 0.5, my=mid[1] + n[1] * 0.5))
    return pd.DataFrame(rows)


def facade_sun(F: pd.DataFrame, L: dict) -> pd.DataFrame:
    """Sun hours per wall and floor band. Returns one row per (wall, band)."""
    if F.empty:
        return pd.DataFrame()
    pos = sun.sun_positions()
    tops = np.arange(P.FACADE_BAND_M, P.FACADE_MAX_HEIGHT_M + 1e-9, P.FACADE_BAND_M)
    out = []
    for top in tops:
        z = top - P.FACADE_BAND_M / 2
        sel = F[F.height >= top - 1e-9]
        if sel.empty:
            continue
        blds = [(b, h - z) for b, h in L["buildings"] if h > z]
        shaded = sun.building_shade(sel.mx.values, sel.my.values, blds, pos)
        az = np.radians([p["az"] for p in pos])
        sx, sy = np.sin(az), np.cos(az)                                       # direction towards the sun
        facing = (sel.nx.values[None, :] * sx[:, None] + sel.ny.values[None, :] * sy[:, None]) > 0
        hours = ((~shaded) & facing).sum(axis=0) * P.SUN_STEP_H
        out.append(sel.assign(band_top=top, band_bottom=top - P.FACADE_BAND_M, sun_hours=hours))
    return pd.concat(out, ignore_index=True)


def sun_class(h):
    return "full sun" if h >= P.FACADE_SUN_FULL_H else ("part shade" if h >= P.FACADE_SUN_PART_H else "full shade")


def green_facades(FB: pd.DataFrame, share_pct: float = P.FACADE_GREEN_SHARE_PCT) -> dict:
    """Pick walls to green (sunniest first) and a climber per wall.
    FB: output of facade_sun. Returns the greened bands and the totals."""
    V = climbers()
    if FB.empty or share_pct <= 0 or V.empty:
        return dict(bands=FB.iloc[0:0] if not FB.empty else FB, area_m2=0.0, share_pct=0.0, walls=0,
                    buildings=0, street_m=float(FB.drop_duplicates(["x0", "y0", "x1", "y1"]).length.sum()) if not FB.empty else 0.0,
                    species=[])
    walls = FB.groupby(["x0", "y0", "x1", "y1"], as_index=False).agg(
        length=("length", "first"), building=("building", "first"), height=("height", "first"), sun=("sun_hours", "mean"))
    walls = walls.sort_values("sun", ascending=False)
    total = walls.length.sum()
    walls["cum"] = walls.length.cumsum()
    chosen = walls[walls.cum - walls.length < total * share_pct / 100.0].copy()
    use = {}
    picks = []
    for w in chosen.itertuples():
        cls = sun_class(w.sun)
        ok = V[V[cls]]
        if ok.empty:
            continue
        need = min(w.height, P.FACADE_MAX_HEIGHT_M, P.CLIMBER_PREFERRED_HEIGHT_M)  # climbers reaching this come first,
        r = min(ok.itertuples(), key=lambda r: (r.height_m < need, use.get(r.species, 0), -r.height_m))  # then spread species
        use[r.species] = use.get(r.species, 0) + 1
        picks.append(dict(x0=w.x0, y0=w.y0, x1=w.x1, y1=w.y1, climber=r.species, climber_height=r.height_m, sun_class=cls))
    if not picks:
        return dict(bands=FB.iloc[0:0], area_m2=0.0, share_pct=0.0, walls=0, buildings=0, street_m=float(total), species=[])
    pk = pd.DataFrame(picks)
    B = FB.merge(pk, on=["x0", "y0", "x1", "y1"])
    B = B[B.band_bottom < B.climber_height].copy()
    B["green_h"] = np.minimum(B.band_top, B.climber_height) - B.band_bottom
    area = float((B.length * B.green_h).sum())
    greened = B.drop_duplicates(["x0", "y0", "x1", "y1"])
    return dict(bands=B, area_m2=area, share_pct=100.0 * greened.length.sum() / total if total else 0.0,
                walls=len(greened), buildings=int(greened.building.nunique()), street_m=float(total),
                species=sorted(pk.climber.value_counts().items(), key=lambda kv: -kv[1]))


def strip(row, depth=0.4):
    """Thin footprint just outside the wall, for the 3D view."""
    a = np.array([row.x0, row.y0]); c = np.array([row.x1, row.y1]); n = np.array([row.nx, row.ny])
    return Polygon([a, c, c + n * depth, a + n * depth])
