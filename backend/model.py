"""Green Spine pipeline: grid -> score -> place -> species -> KPIs."""
import math
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point
from shapely.ops import unary_union
from . import parameters as C


# ---------- 1. grid ----------
def build_grid(L: dict, setback_building: float = C.TREE_SETBACK_BUILDING_M,
               setback_road: float = C.TREE_SETBACK_ROAD_M, no_plant=None) -> pd.DataFrame:
    """2 m grid of plantable cells inside the corridor.

    A cell is blocked inside a building, the carriageway or the utilities strip, within
    `setback_building` m of a facade, within `setback_road` m of the carriageway, and
    inside `no_plant` (e.g. the building canopies) when given.
    """
    minx, miny, maxx, maxy = L["corridor"].bounds
    xs = np.arange(minx + C.CELL / 2, maxx, C.CELL)
    ys = np.arange(miny + C.CELL / 2, maxy, C.CELL)
    X, Y = np.meshgrid(xs, ys)
    x, y = X.ravel(), Y.ravel()
    pts = shapely.points(x, y)
    inside = shapely.contains(L["corridor"], pts)
    x, y, pts = x[inside], y[inside], pts[inside]

    blocked = np.zeros(len(x), bool)
    bld = unary_union([b for b, _ in L["buildings"]]) if L["buildings"] else None
    for geom in (bld, L["road"], L["utilities"], no_plant):
        if geom is not None and not geom.is_empty:
            blocked |= shapely.contains(geom, pts)
    # setbacks from facades and carriageway edges
    if bld is not None and not bld.is_empty and setback_building > 0:
        blocked |= shapely.dwithin(bld, pts, setback_building)
    if not L["road"].is_empty and setback_road > 0:
        blocked |= shapely.dwithin(L["road"], pts, setback_road)
    paved = np.ones(len(x), bool)
    if not L["unpaved"].is_empty:
        paved = ~shapely.contains(L["unpaved"], pts)
    wet = np.zeros(len(x), bool)
    if not L["wet_zone"].is_empty:
        wet = shapely.contains(L["wet_zone"], pts)

    g = pd.DataFrame(dict(x=x, y=y, blocked=blocked, paved=paved, wet=wet))
    g["soil"] = np.where(g.paved, C.SOIL_PAVED, C.SOIL_UNPAVED)
    g["moisture"] = np.where(g.wet, "wet", np.where(g.paved, "dry", "moist"))
    g["dist_canopy"] = _dist_to_existing(g, L["existing_trees"])
    exposure = np.where(g.paved, 1.0, 0.5)
    g["heat"] = exposure * (0.4 + 0.6 * np.clip(g.dist_canopy / C.GAP_CAP, 0, 1))
    g["heat"] = g.heat / max(g.heat.max(), 1e-9)
    return g[~g.blocked].reset_index(drop=True)


def _dist_to_existing(g, trees):
    d = np.full(len(g), C.GAP_CAP * 4.0)
    for pt, r in trees:
        d = np.minimum(d, np.hypot(g.x.values - pt.x, g.y.values - pt.y) - r)
    return np.clip(d, 0, None)


# ---------- 2+3. score and place ----------
def place_trees(grid: pd.DataFrame, L: dict, w: dict, budget: int) -> pd.DataFrame:
    tot = max(w["heat"] + w["soil"] + w["gap"], 1e-9)
    wh, ws, wg = w["heat"] / tot, w["soil"] / tot, w["gap"] / tot
    tolerance = (1 - ws) ** 2 * 0.7   # low soil weight = willing to engineer the ground

    x, y = grid.x.values, grid.y.values
    soil, heat = grid.soil.values, grid.heat.values
    dist = grid.dist_canopy.values.copy()
    free = np.ones(len(grid), bool)
    ex = [(p.x, p.y, r) for p, r in L["existing_trees"]]
    for px, py, r in ex:
        free &= np.hypot(x - px, y - py) > r + 2.0

    classes = sorted(C.TREE_CLASSES.items(), key=lambda kv: -kv[1]["r_mature"])
    min_sp = min(c["spacing"] for _, c in classes)
    placed = []
    while len(placed) < budget and free.any():
        score = wh * heat + ws * soil + wg * np.clip(dist / C.GAP_CAP, 0, 1)
        score[~free] = -1
        i = int(score.argmax())
        if score[i] < C.MIN_SCORE:
            break
        cls = next((n for n, c in classes if c["soil_need"] <= soil[i] + tolerance), None)
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
                           soil=float(soil[i]), moisture=grid.moisture.values[i],
                           engineered=bool(c["soil_need"] > soil[i]),
                           soil_m3=c["soil_m3"], order=len(placed) + 1))
        d = np.hypot(x - x[i], y - y[i])
        free &= d > (c["spacing"] + min_sp) / 2
        dist = np.minimum(dist, np.clip(d - c["r_mature"], 0, None))
    return pd.DataFrame(placed)


# ---------- 4. species ----------
def assign_species(trees: pd.DataFrame, plants: pd.DataFrame) -> pd.DataFrame:
    if trees.empty:
        return trees.assign(species="", common_name="", genus="", family="")
    n = len(trees)
    caps = dict(species=max(1, math.ceil(C.MAX_SPECIES * n)), genus=max(1, math.ceil(C.MAX_GENUS * n)),
                family=max(1, math.ceil(C.MAX_FAMILY * n)))
    cnt = dict(species={}, genus={}, family={})
    plants = plants.copy()
    plants["_m"] = plants.soil_moisture.str.split(";")
    out = []
    for t in trees.itertuples():
        same = plants[plants.size_class == t.size_class]
        if same.empty:
            same = plants
        fit = same[same._m.apply(lambda m: t.moisture in m)]
        def within(r):
            return all(cnt[k].get(getattr(r, k), 0) < caps[k] for k in caps)
        fit_rows, same_rows = list(fit.itertuples()), list(same.itertuples())
        okrows = ([r for r in fit_rows if within(r)] or [r for r in same_rows if within(r)]
                  or fit_rows or same_rows)
        r = min(okrows, key=lambda r: (cnt["species"].get(r.species, 0), cnt["genus"].get(r.genus, 0)))
        for k in caps:
            cnt[k][getattr(r, k)] = cnt[k].get(getattr(r, k), 0) + 1
        out.append((r.species, r.common_name, r.genus, r.family))
    return trees.assign(**dict(zip(["species", "common_name", "genus", "family"], map(list, zip(*out)))))


# ---------- 5. growth and KPIs ----------
def crown_radius(size_class, year):
    c = pd.Series(size_class).map(lambda s: C.TREE_CLASSES[s])
    r = [min(k["r_mature"], C.PLANTING_RADIUS + k["growth"] * max(0, year - C.BASE_YEAR)) for k in c]
    return np.array(r)


def canopy_geometry(trees: pd.DataFrame, L: dict, year: int):
    geoms = [p.buffer(r, 12) for p, r in L["existing_trees"]]
    if len(trees):
        rr = crown_radius(trees.size_class, year)
        geoms += [Point(a, b).buffer(r, 12) for a, b, r in zip(trees.x, trees.y, rr)]
    return unary_union(geoms) if geoms else Point(0, 0).buffer(0)


def kpis(trees: pd.DataFrame, L: dict, year: int) -> dict:
    canopy = canopy_geometry(trees, L, year)
    line = L["centreline"]
    covered = line.intersection(canopy.buffer(C.SHADE_REACH_M))    # crown close to the path still shades it
    rest = line.difference(canopy.buffer(C.SHADE_REACH_M))
    parts = list(rest.geoms) if hasattr(rest, "geoms") else ([rest] if not rest.is_empty else [])
    n = len(trees)
    eng = trees[trees.engineered] if n else trees
    return dict(
        canopy_pct=100 * canopy.intersection(L["corridor"]).area / L["corridor"].area,
        shade_pct=100 * covered.length / line.length,
        longest_gap_m=max((p.length for p in parts), default=0.0),
        natural_soil_pct=100 * (1 - len(eng) / n) if n else 0.0,
        trees=n,
        species=int(trees.species.nunique()) if n and "species" in trees else 0,
        max_species_share_pct=float(100 * trees.species.value_counts(normalize=True).max()) if n and "species" in trees else 0.0,
        engineered_soil_m3=float(eng.soil_m3.sum()) if n else 0.0,
    )


def targets_met(k: dict) -> int:
    met = 0
    for key, (op, val) in C.TARGETS.items():
        met += (k[key] >= val) if op == ">=" else (k[key] <= val)
    return int(met)


def run_option(L: dict, grid: pd.DataFrame, plants: pd.DataFrame, weights: dict, budget: int) -> pd.DataFrame:
    trees = place_trees(grid, L, weights, budget)
    trees = assign_species(trees, plants)
    if len(trees):
        trees["phase"] = np.where(trees.engineered, "Later: engineered soil", "Plant now")
    return trees
