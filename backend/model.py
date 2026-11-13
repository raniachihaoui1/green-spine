"""Green Spine pipeline: grid -> score -> place -> species -> KPIs.

Existing canopy is the RIVM Bomenkaart 2022 (L["existing"], one disc per 10 m cell, see
backend/bomenkaart.py), or the tree points when the raster is absent. Species are matched to
the soil at the nearest BRO borehole (backend/soil.py). All numbers: backend/parameters.py.
"""
import math
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point
from shapely.ops import unary_union
from . import parameters as C
from . import soil
from . import sun


# ---------- existing canopy ----------
def existing_discs(L: dict) -> pd.DataFrame:
    """Existing canopy as discs: x, y, r (m), cover (%), in_corridor."""
    return L["existing"]


def existing_cleared(trees: pd.DataFrame, L: dict) -> np.ndarray:
    """True for each existing canopy disc that a new trunk lands in (cleared for planting)."""
    ex = existing_discs(L)
    out = np.zeros(len(ex), bool)
    if not len(trees) or not len(ex):
        return out
    d = np.hypot(ex.x.values[:, None] - trees.x.values[None, :], ex.y.values[:, None] - trees.y.values[None, :])
    return (d <= ex.r.values[:, None] + C.PLANTING_RADIUS).any(axis=1)


def _kept(trees, L):
    ex = existing_discs(L)
    return ex[~existing_cleared(trees, L)]


# ---------- soil boreholes ----------
_SOIL = {}


def soil_context(species) -> dict:
    """Borehole positions and soil-fit scores for the species in the plant table (cached)."""
    key = tuple(sorted(species))
    if key not in _SOIL:
        pos = soil.borehole_positions()
        table = soil.compatibility_table(key, default_root_depth=C.SOIL_DEFAULT_ROOT_DEPTH_M)
        usable = {b: xy for b, xy in pos.items()
                  if any(s is not None and s >= C.SOIL_MIN_COMPATIBILITY for s in table.get(b, {}).values())}
        _SOIL[key] = dict(positions=pos, usable=usable, table=table)
    return _SOIL[key]


def _nearest_borehole(x, y, usable: dict):
    if not usable:
        return np.array([""] * len(x)), np.full(len(x), np.nan)
    ids = list(usable)
    bx = np.array([usable[b][0] for b in ids])
    by = np.array([usable[b][1] for b in ids])
    d = np.hypot(np.asarray(x)[:, None] - bx[None, :], np.asarray(y)[:, None] - by[None, :])
    j = d.argmin(axis=1)
    return np.array(ids)[j], d[np.arange(len(x)), j]


# ---------- 1. grid ----------
def base_grid(L: dict, species=()) -> pd.DataFrame:
    """Every 2 m cell inside the corridor and outside buildings, the carriageway and utilities,
    with soil, sun hours, heat, distance to canopy, canopy protection and nearest borehole.
    Independent of the sidebar setbacks, so it is computed once."""
    minx, miny, maxx, maxy = L["corridor"].bounds
    xs = np.arange(minx + C.CELL / 2, maxx, C.CELL)
    ys = np.arange(miny + C.CELL / 2, maxy, C.CELL)
    X, Y = np.meshgrid(xs, ys)
    x, y = X.ravel(), Y.ravel()
    pts = shapely.points(x, y)
    inside = shapely.contains(L["corridor"], pts)
    x, y, pts = x[inside], y[inside], pts[inside]

    blocked = np.zeros(len(x), bool)
    bld = L["bld_union"] if L.get("bld_union") is not None else (unary_union([b for b, _ in L["buildings"]]) if L["buildings"] else None)
    for geom in (bld, L["road"], L["utilities"]):
        if geom is not None and not geom.is_empty:
            blocked |= shapely.contains(geom, pts)
    x, y, pts = x[~blocked], y[~blocked], pts[~blocked]

    paved = np.ones(len(x), bool)
    if not L["unpaved"].is_empty:
        paved = ~shapely.contains(L["unpaved"], pts)
    wet = np.zeros(len(x), bool)
    if not L["wet_zone"].is_empty:
        wet = shapely.contains(L["wet_zone"], pts)

    g = pd.DataFrame(dict(x=x, y=y, paved=paved, wet=wet))
    # distances for the setback sliders, computed once so moving a slider is only a comparison
    g["d_building"] = shapely.distance(bld, pts) if bld is not None and not bld.is_empty else np.inf
    g["d_road"] = shapely.distance(L["road"], pts) if not L["road"].is_empty else np.inf
    g["soil"] = np.where(g.paved, C.SOIL_PAVED, C.SOIL_UNPAVED)
    g["moisture"] = np.where(g.wet, "wet", np.where(g.paved, "dry", "moist"))

    ex = existing_discs(L)
    if len(ex):
        d = np.hypot(g.x.values[:, None] - ex.x.values[None, :], g.y.values[:, None] - ex.y.values[None, :])
        g["dist_canopy"] = np.clip((d - ex.r.values[None, :]).min(axis=1), 0, None)
        g["canopy_cover"] = np.where(d <= ex.r.values[None, :], ex.cover.values[None, :], 0).max(axis=1)
        prot = ex.cover.values >= C.CANOPY_PROTECT_COVER
        g["protected"] = (d[:, prot] <= ex.r.values[prot][None, :] + C.CANOPY_ROOT_BUFFER_M).any(axis=1) if prot.any() else False
    else:
        g["dist_canopy"], g["canopy_cover"], g["protected"] = C.GAP_CAP * 4.0, 0.0, False

    # Heat = direct-sun hours on the design day (buildings and existing canopy cast shadows),
    # weighted by surface: paving heats up fully, open ground half as much.
    pos = sun.sun_positions()
    shaded = sun.building_shade(g.x, g.y, L["buildings"], pos) | sun.tree_shade(g.x, g.y, ex.x, ex.y, ex.r, pos)
    g["sun_hours"] = sun.hours(shaded)
    g["heat"] = np.where(g.paved, 1.0, 0.5) * g.sun_hours
    g["heat"] = g.heat / max(g.heat.max(), 1e-9)

    S = soil_context(species)
    g["borehole"], g["borehole_dist_m"] = _nearest_borehole(g.x.values, g.y.values, S["usable"])
    return g


def mask_grid(g: pd.DataFrame, L: dict, setback_building: float = C.TREE_SETBACK_BUILDING_M,
              setback_road: float = C.TREE_SETBACK_ROAD_M, no_plant=None, protect_canopy: bool = True) -> pd.DataFrame:
    """Plantable cells: drop cells within `setback_building` m of a facade, within `setback_road` m
    of the carriageway, inside `no_plant` (e.g. building canopies) and, if `protect_canopy`,
    under protected existing canopy (RIVM cover >= CANOPY_PROTECT_COVER, plus the root buffer)."""
    blocked = (g.d_building.values < setback_building) | (g.d_road.values < setback_road)
    if no_plant is not None and not no_plant.is_empty:
        shapely.prepare(no_plant)
        blocked |= shapely.contains(no_plant, shapely.points(g.x.values, g.y.values))
    if protect_canopy:
        blocked |= g.protected.values
    return g[~blocked].reset_index(drop=True)


def build_grid(L: dict, setback_building: float = C.TREE_SETBACK_BUILDING_M,
               setback_road: float = C.TREE_SETBACK_ROAD_M, no_plant=None, species=(), protect_canopy=True) -> pd.DataFrame:
    """Base grid plus setbacks in one call (kept for older code)."""
    return mask_grid(base_grid(L, species), L, setback_building, setback_road, no_plant, protect_canopy)


# ---------- 2+3. score and place ----------
def place_trees(grid: pd.DataFrame, L: dict, w: dict, budget: int) -> pd.DataFrame:
    tot = max(w["heat"] + w["soil"] + w["gap"], 1e-9)
    wh, ws, wg = w["heat"] / tot, w["soil"] / tot, w["gap"] / tot
    tolerance = (1 - ws) ** 2 * 0.7   # low soil weight = willing to engineer the ground

    x, y = grid.x.values, grid.y.values
    soil_v, heat = grid.soil.values, grid.heat.values
    dist = grid.dist_canopy.values.copy()
    free = np.ones(len(grid), bool)

    classes = sorted(C.TREE_CLASSES.items(), key=lambda kv: -kv[1]["r_mature"])
    min_sp = min(c["spacing"] for _, c in classes)
    placed = []
    while len(placed) < budget and free.any():
        score = wh * heat + ws * soil_v + wg * np.clip(dist / C.GAP_CAP, 0, 1)
        score[~free] = -1
        i = int(score.argmax())
        if score[i] < C.MIN_SCORE:
            break
        cls = next((n for n, c in classes if c["soil_need"] <= soil_v[i] + tolerance), None)
        ok = cls is not None
        if ok:
            sp = C.TREE_CLASSES[cls]["spacing"]
            for t in placed:
                if math.hypot(x[i] - t["x"], y[i] - t["y"]) < (sp + C.TREE_CLASSES[t["size_class"]]["spacing"]) / 2:
                    ok = False
                    break
        if not ok:
            free[i] = False
            continue
        c = C.TREE_CLASSES[cls]
        placed.append(dict(x=x[i], y=y[i], size_class=cls, score=round(float(score[i]), 3),
                           soil=float(soil_v[i]), moisture=grid.moisture.values[i],
                           engineered=bool(c["soil_need"] > soil_v[i]),
                           soil_m3=c["soil_m3"], borehole=grid.borehole.values[i],
                           borehole_dist_m=round(float(grid.borehole_dist_m.values[i]), 0),
                           order=len(placed) + 1))
        d = np.hypot(x - x[i], y - y[i])
        free &= d > (c["spacing"] + min_sp) / 2
        dist = np.minimum(dist, np.clip(d - c["r_mature"], 0, None))
    return pd.DataFrame(placed)


# ---------- 4. species ----------
def diversity_caps(n: int) -> dict:
    """Santamour's 10-20-30 rule as the most trees allowed per species, genus and family in a
    planting of n trees. Rounded down, so the share never exceeds 10 / 20 / 30 % (min. 1 tree)."""
    return {k: max(1, math.floor(f * n + 1e-9)) for k, f in
            (("species", C.MAX_SPECIES), ("genus", C.MAX_GENUS), ("family", C.MAX_FAMILY))}


def assign_species(trees: pd.DataFrame, plants: pd.DataFrame, enforce: bool = C.ENFORCE_10_20_30) -> pd.DataFrame:
    """Pick a species per tree, in planting-priority order.

    A species qualifies when it is soil-compatible at the tree's borehole (score >=
    SOIL_MIN_COMPATIBILITY), suits the cell's moisture and keeps the planting within
    Santamour's 10-20-30 rule (at most 10 % per species, 20 % per genus, 30 % per family).
    Among qualifying species: least-used species first, then genus, then the best soil fit.

    With `enforce` on, when the tree's size class has no qualifying species left, the tree
    changes class: first to a smaller class (smaller crown, so spacing always holds), then to a
    larger class if its neighbours leave enough room for the larger spacing. Moisture is relaxed
    only after every class is tried. The rule is broken only if nothing else fits.
    With `enforce` off, the tree keeps its class and the rule may be broken (the old behaviour).
    """
    if trees.empty:
        return trees.assign(species="", common_name="", genus="", family="", soil_fit=np.nan, resized=False)
    S = soil_context(plants.species)
    caps = diversity_caps(len(trees))
    cnt = dict(species={}, genus={}, family={})
    plants = plants.copy()
    plants["moist_list"] = plants.soil_moisture.str.split(";")
    order = [n for n, _ in sorted(C.TREE_CLASSES.items(), key=lambda kv: -kv[1]["r_mature"])]
    trees = trees.copy()
    tx, ty = trees.x.values, trees.y.values
    cls_now = list(trees.size_class)                      # updated as trees change class

    def room_for(i, cls):
        """True if tree i can take class `cls` without breaking the spacing to any other tree."""
        sp = C.TREE_CLASSES[cls]["spacing"]
        d = np.hypot(tx - tx[i], ty - ty[i])
        need = (sp + np.array([C.TREE_CLASSES[c]["spacing"] for c in cls_now])) / 2
        d[i] = np.inf
        return bool((d >= need).all())

    out = []
    for i, t in enumerate(trees.itertuples()):
        fit_at = S["table"].get(t.borehole, {})

        def score(r):
            s = fit_at.get(r.species)
            return s if s is not None else -1.0

        def within(r):
            return all(cnt[k].get(getattr(r, k), 0) < caps[k] for k in caps)

        def rows_of(cls):
            same = plants[plants.size_class == cls]
            return [r for r in same.itertuples() if score(r) >= C.SOIL_MIN_COMPATIBILITY] or list(same.itertuples())

        k0 = order.index(t.size_class)
        classes = (order[k0:] + [c for c in reversed(order[:k0]) if room_for(i, c)]) if enforce else [t.size_class]
        pick, cls_used = None, t.size_class
        for moist in (True, False):                       # moisture is relaxed last
            for cls in classes:
                ok = [r for r in rows_of(cls) if within(r) and (not moist or t.moisture in r.moist_list)]
                if ok:
                    pick, cls_used = ok, cls
                    break
            if pick:
                break
        if pick is None:                                  # rule cannot be kept: least-used species of its class
            pick = rows_of(t.size_class) or list(plants.itertuples())
        r = min(pick, key=lambda r: (cnt["species"].get(r.species, 0), cnt["genus"].get(r.genus, 0), -score(r)))
        for k in caps:
            cnt[k][getattr(r, k)] = cnt[k].get(getattr(r, k), 0) + 1
        cls_now[i] = cls_used
        out.append((r.species, r.common_name, r.genus, r.family, score(r) if score(r) >= 0 else np.nan,
                    cls_used, cls_used != t.size_class))
    cols = ["species", "common_name", "genus", "family", "soil_fit", "size_class", "resized"]
    trees = trees.assign(**dict(zip(cols, map(list, zip(*out)))))
    c = trees.size_class.map(C.TREE_CLASSES)
    trees["engineered"] = [cl["soil_need"] > s for cl, s in zip(c, trees.soil)]
    trees["soil_m3"] = [cl["soil_m3"] for cl in c]
    return trees


def diversity_check(trees: pd.DataFrame) -> dict:
    """Largest share per species, genus and family (%) and whether the 10-20-30 rule holds."""
    if trees.empty:
        return dict(species_pct=0.0, genus_pct=0.0, family_pct=0.0, ok=False, resized=0)
    sh = {k: float(100 * trees[k].value_counts(normalize=True).max()) for k in ("species", "genus", "family")}
    caps = diversity_caps(len(trees))
    ok = all(trees[k].value_counts().max() <= caps[k] for k in caps)
    return dict(species_pct=sh["species"], genus_pct=sh["genus"], family_pct=sh["family"], ok=bool(ok),
                resized=int(trees.get("resized", pd.Series(dtype=bool)).sum()))


# ---------- 5. growth and KPIs ----------
def crown_radius(size_class, year):
    c = pd.Series(size_class).map(lambda s: C.TREE_CLASSES[s])
    r = [min(k["r_mature"], C.PLANTING_RADIUS + k["growth"] * max(0, year - C.BASE_YEAR)) for k in c]
    return np.array(r)


def canopy_geometry(trees: pd.DataFrame, L: dict, year: int):
    """Existing canopy that is kept, plus the new crowns at their size in `year`."""
    ex = _kept(trees, L)
    geoms = list(shapely.buffer(shapely.points(ex.x.values, ex.y.values), ex.r.values, 12)) if len(ex) else []
    if len(trees):
        rr = crown_radius(trees.size_class, year)
        geoms += [Point(a, b).buffer(r, 12) for a, b, r in zip(trees.x, trees.y, rr)]
    return unary_union(geoms) if geoms else Point(0, 0).buffer(0)


def _all_crowns(trees, L, year):
    ex = _kept(trees, L)
    tx, ty, tr = list(ex.x), list(ex.y), list(ex.r)
    if len(trees):
        tx, ty = tx + list(trees.x), ty + list(trees.y)
        tr = tr + list(crown_radius(trees.size_class, year))
    return tx, ty, tr


def route_base(L: dict) -> dict:
    """Sample points along the walking route and the building shade on them.
    Independent of the planting option, so compute once and keep it in L["route"]."""
    line = L["centreline"]
    d = np.arange(C.ROUTE_STEP / 2, line.length, C.ROUTE_STEP)
    pts = shapely.line_interpolate_point(line, d)
    x, y = shapely.get_x(pts), shapely.get_y(pts)
    pos = sun.sun_positions()
    return dict(x=x, y=y, pos=pos, bld=sun.building_shade(x, y, L["buildings"], pos))


def route_sun_hours(trees: pd.DataFrame, L: dict, year: int) -> float:
    """Average direct-sun hours along the route on the design day, with buildings, the kept
    existing canopy and the planted trees at their size in this year."""
    R = L.get("route") or route_base(L)
    tx, ty, tr = _all_crowns(trees, L, year)
    shaded = R["bld"] | sun.tree_shade(R["x"], R["y"], tx, ty, tr, R["pos"])
    return float(sun.hours(shaded).mean())


def kpis(trees: pd.DataFrame, L: dict, year: int) -> dict:
    canopy = canopy_geometry(trees, L, year)
    line = L["centreline"]
    covered = line.intersection(canopy.buffer(C.SHADE_REACH_M))    # crown close to the path still shades it
    rest = line.difference(canopy.buffer(C.SHADE_REACH_M))
    parts = list(rest.geoms) if hasattr(rest, "geoms") else ([rest] if not rest.is_empty else [])
    n = len(trees)
    eng = trees[trees.engineered] if n else trees
    ex = existing_discs(L)
    inside = ex[ex.in_corridor.astype(bool)] if len(ex) else ex
    area = np.pi * inside.r ** 2 if len(inside) else pd.Series(dtype=float)
    cleared = existing_cleared(trees, L)[ex.in_corridor.astype(bool).values] if len(ex) else np.array([], bool)
    return dict(
        canopy_pct=100 * canopy.intersection(L["corridor"]).area / L["corridor"].area,
        shade_pct=100 * covered.length / line.length,
        longest_gap_m=max((p.length for p in parts), default=0.0),
        natural_soil_pct=100 * (1 - len(eng) / n) if n else 0.0,
        route_sun_hours=route_sun_hours(trees, L, year),
        existing_kept_pct=100 * (1 - float(area[cleared].sum()) / float(area.sum())) if len(area) and area.sum() else 100.0,
        existing_cleared_m2=float(area[cleared].sum()) if len(area) else 0.0,
        trees=n,
        species=int(trees.species.nunique()) if n and "species" in trees else 0,
        max_species_share_pct=float(100 * trees.species.value_counts(normalize=True).max()) if n and "species" in trees else 0.0,
        max_genus_share_pct=float(100 * trees.genus.value_counts(normalize=True).max()) if n and "genus" in trees else 0.0,
        max_family_share_pct=float(100 * trees.family.value_counts(normalize=True).max()) if n and "family" in trees else 0.0,
        engineered_soil_m3=float(eng.soil_m3.sum()) if n else 0.0,
    )


def targets_met(k: dict) -> int:
    met = 0
    for key, (op, val) in C.TARGETS.items():
        met += (k[key] >= val) if op == ">=" else (k[key] <= val)
    return int(met)


def run_option(L: dict, grid: pd.DataFrame, plants: pd.DataFrame, weights: dict, budget: int,
               enforce: bool = C.ENFORCE_10_20_30) -> pd.DataFrame:
    trees = place_trees(grid, L, weights, budget)
    trees = assign_species(trees, plants, enforce)
    if len(trees):
        trees["phase"] = np.where(trees.engineered, "Later: engineered soil", "Plant now")
    return trees
