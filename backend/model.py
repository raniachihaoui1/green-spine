"""Green Spine pipeline: grid -> score -> place -> species -> KPIs.

Existing canopy is the RIVM Bomenkaart 2022 (L["existing"], one disc per 10 m cell, see
backend/bomenkaart.py), or the tree points when the raster is absent. Species are matched to
the soil at the nearest BRO borehole (backend/soil.py). All numbers: backend/parameters.py.
"""
import math
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point
from shapely.ops import unary_union
from . import parameters as C
from . import soil
from . import sun
from . import feasibility


# ---------- existing canopy ----------
def existing_discs(L: dict) -> pd.DataFrame:
    """Existing canopy as discs: x, y, r (m), cover (%), in_corridor."""
    return L["existing"]


def existing_cleared(trees: pd.DataFrame, L: dict) -> np.ndarray:
    """True for each existing canopy disc that a new trunk lands in (cleared for planting)."""
    ex = existing_discs(L)
    if ex.empty:
        return np.zeros(0, dtype=bool)
    removal = L.get("canopy_removals", Point().buffer(0))
    out = shapely.covers(removal, shapely.points(ex.x, ex.y))
    if not len(trees) or not len(ex):
        return out
    d = np.hypot(ex.x.values[:, None] - trees.x.values[None, :], ex.y.values[:, None] - trees.y.values[None, :])
    return out | (d <= ex.r.values[:, None] + C.PLANTING_RADIUS).any(axis=1)


def _kept(trees, L):
    ex = existing_discs(L)
    return ex[~existing_cleared(trees, L)]


# ---------- soil boreholes ----------
_SOIL = {}


def soil_context(species) -> dict:
    """Borehole positions and soil-fit scores for the species in the plant table (cached)."""
    files = (Path(soil.DEFAULT_SOIL_CSV), Path(soil.DEFAULT_PLANT_CSV))
    key = (tuple(sorted(species)), tuple((str(p), p.stat().st_mtime_ns) for p in files))
    if key not in _SOIL:
        pos = soil.borehole_positions()
        table = soil.compatibility_table(key[0], default_root_depth=C.SOIL_DEFAULT_ROOT_DEPTH_M)
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
    rejected = []
    for name, geom in (("Building", bld), ("Carriageway", L["road"]), ("Utilities", L["utilities"]),
                       ("Water", L.get("water")), ("Underground structure", L.get("underground"))):
        if geom is not None and not geom.is_empty:
            hit = shapely.covers(geom, pts) & ~blocked
            rejected.extend(dict(x=float(a), y=float(b), reason=name) for a, b in zip(x[hit], y[hit]))
            blocked |= hit
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

    ex = _kept(pd.DataFrame(), L)
    committed = L.get("committed", pd.DataFrame())
    if len(committed):
        planned = committed[["x", "y"]].copy()
        planned["r"] = committed.size_class.map(lambda c: C.TREE_CLASSES[c]["r_mature"])
        planned["cover"] = 100.0
        ex = pd.concat([ex, planned], ignore_index=True)
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
    g.attrs["rejections"] = rejected
    return g


def mask_grid(g: pd.DataFrame, L: dict, setback_building: float = C.TREE_SETBACK_BUILDING_M,
              setback_road: float = C.TREE_SETBACK_ROAD_M, no_plant=None, protect_canopy: bool = True) -> pd.DataFrame:
    """Plantable cells: drop cells within `setback_building` m of a facade, within `setback_road` m
    of the carriageway, inside `no_plant` (e.g. building canopies) and, if `protect_canopy`,
    under protected existing canopy (RIVM cover >= CANOPY_PROTECT_COVER, plus the root buffer)."""
    blocked = (g.d_building.values < setback_building) | (g.d_road.values < setback_road)
    blocked |= g.dist_canopy.values <= C.PLANTING_RADIUS
    if no_plant is not None and not no_plant.is_empty:
        shapely.prepare(no_plant)
        blocked |= shapely.contains(no_plant, shapely.points(g.x.values, g.y.values))
    if protect_canopy:
        blocked |= g.protected.values
    result = g[~blocked].reset_index(drop=True)
    result.attrs["rejections"] = g.attrs.get("rejections", []) + [
        dict(x=float(t.x), y=float(t.y), reason="Setback, protected canopy or shelter")
        for t in g[blocked].itertuples()]
    return result


def build_grid(L: dict, setback_building: float = C.TREE_SETBACK_BUILDING_M,
               setback_road: float = C.TREE_SETBACK_ROAD_M, no_plant=None, species=(), protect_canopy=True) -> pd.DataFrame:
    """Base grid plus setbacks in one call (kept for older code)."""
    return mask_grid(base_grid(L, species), L, setback_building, setback_road, no_plant, protect_canopy)


# ---------- 2+3. score and place ----------
@dataclass
class PlantingResult:
    trees: pd.DataFrame
    rejections: list[dict]
    requested: int


def place_trees(grid: pd.DataFrame, L: dict, w: dict, budget: int, plants: pd.DataFrame,
                enforce=C.ENFORCE_10_20_30, allow_engineering=C.ALLOW_ENGINEERED_SOIL) -> PlantingResult:
    rejections = grid.attrs.get("rejections", [])
    grid = grid.copy(deep=False)
    grid.attrs.clear()
    if any(not math.isfinite(v) or v < 0 for v in w.values()) or sum(w.values()) <= 0:
        raise ValueError("Strategy weights must be non-negative and at least one must be positive.")
    wh, ws, wg = (w[k] / sum(w.values()) for k in ("heat", "soil", "gap"))
    x, y = grid.x.values, grid.y.values
    soil_v, heat = grid.soil.values, grid.heat.values
    dist = grid.dist_canopy.values.copy()
    free = np.ones(len(grid), bool)

    classes = sorted(C.TREE_CLASSES, key=lambda k: -C.TREE_CLASSES[k]["r_mature"])
    S = soil_context(plants.species)
    caps = diversity_caps(budget)
    counts = {k: {} for k in caps}
    pools = {(b, m, cls): _species_candidates(plants, S["table"].get(b, {}), cls, m)
             for b, m in grid[["borehole", "moisture"]].drop_duplicates().itertuples(index=False, name=None)
             for cls in classes}
    groups = {(b, m): np.flatnonzero((grid.borehole.values == b) & (grid.moisture.values == m))
              for b, m, _ in pools}
    available = feasibility.rootable_ground(L)
    reserved = []
    rejection = np.full(len(grid), "Not selected within tree budget", dtype=object)
    placed = []
    while len(placed) < budget and free.any():
        for (b, m), indices in groups.items():
            if not free[indices].any():
                continue
            candidates = [r for cls in classes for r in pools[b, m, cls]]
            if enforce:
                candidates = [r for r in candidates if all(counts[k].get(getattr(r, k), 0) < caps[k] for k in caps)]
            if not candidates:
                rejected = indices[free[indices]]
                rejection[rejected] = "No soil- and moisture-compatible species within diversity limits"
                free[rejected] = False
        if not free.any():
            break
        score = wh * heat + ws * soil_v + wg * np.clip(dist / C.GAP_CAP, 0, 1)
        score[~free] = -1
        i = int(score.argmax())
        if score[i] < C.MIN_SCORE:
            rejection[free] = "Below strategy score threshold"
            break
        cell = grid.iloc[i]
        chosen = None
        reason = "No soil- and moisture-compatible species within diversity limits"
        for cls in classes:
            rows = pools[cell.borehole, cell.moisture, cls]
            if enforce:
                rows = [r for r in rows if all(counts[k].get(getattr(r, k), 0) < caps[k] for k in caps)]
            if not rows:
                continue
            sp = C.TREE_CLASSES[cls]["spacing"]
            if any(math.hypot(x[i] - t["x"], y[i] - t["y"]) <
                   (sp + C.TREE_CLASSES[t["size_class"]]["spacing"]) / 2 for t in placed):
                reason = "Tree spacing"
                continue
            root, failure = feasibility.rooting_space(x[i], y[i], cls, bool(cell.paved), L, available, allow_engineering, reserved)
            if root is None:
                reason = failure
                continue
            fit = S["table"][cell.borehole]
            species = min(rows, key=lambda r: (counts["species"].get(r.species, 0),
                                               counts["genus"].get(r.genus, 0), -fit[r.species]))
            chosen = (cls, species, root, fit[species.species])
            break
        free[i] = False
        if chosen is None:
            rejection[i] = reason
            continue
        cls, species, root, fit = chosen
        c = C.TREE_CLASSES[cls]
        placed.append(dict(x=x[i], y=y[i], size_class=cls, score=round(float(score[i]), 3),
                           soil=float(soil_v[i]), moisture=cell.moisture, paved=bool(cell.paved),
                           borehole=cell.borehole, borehole_dist_m=float(cell.borehole_dist_m),
                           soil_fit=float(fit), species=species.species, common_name=species.common_name,
                           genus=species.genus, family=species.family, resized=False,
                           soil_confidence="nearby proxy" if cell.borehole_dist_m <= C.SOIL_CONFIDENCE_REACH_M else "distant proxy",
                           species_traits="Drought, salt, flood and shade tolerances not fully verified",
                           order=len(placed) + 1, **root))
        for key in counts:
            value = getattr(species, key)
            counts[key][value] = counts[key].get(value, 0) + 1
        reserved.append(shapely.from_wkt(root["root_zone_wkt"]))
        rejection[i] = ""
        d = np.hypot(x - x[i], y - y[i])
        close = free & (d < (c["spacing"] + min(v["spacing"] for v in C.TREE_CLASSES.values())) / 2)
        free[close] = False
        rejection[close] = "Tree spacing"
        dist = np.minimum(dist, np.clip(d - c["r_mature"], 0, None))
    columns = ["x", "y", "size_class", "species", "common_name", "genus", "family", "engineered",
               "paved", "soil", "soil_fit", "borehole", "resized", "order", "soil_m3", "phase"]
    result = pd.DataFrame(placed) if placed else pd.DataFrame(columns=columns)
    decisions = rejections + [
        dict(x=float(a), y=float(b), reason=str(r)) for a, b, r in zip(x, y, rejection) if r]
    return PlantingResult(result, decisions, budget)


# ---------- 4. species ----------
def diversity_caps(n: int) -> dict:
    """Santamour's 10-20-30 rule as the most trees allowed per species, genus and family in a
    planting of n trees. Small populations cannot claim a false pass."""
    return {k: math.floor(f * n + 1e-9) for k, f in
            (("species", C.MAX_SPECIES), ("genus", C.MAX_GENUS), ("family", C.MAX_FAMILY))}

def _species_candidates(plants, fit, cls, moisture):
    return [r for r in plants[plants.size_class == cls].itertuples()
            if fit.get(r.species) is not None and fit[r.species] >= C.SOIL_MIN_COMPATIBILITY
            and moisture in str(r.soil_moisture).split(";")]


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
def crown_radius(size_class, year, planting_year=C.BASE_YEAR):
    c = pd.Series(size_class).map(lambda s: C.TREE_CLASSES[s])
    ages = np.maximum(0, year - np.broadcast_to(np.asarray(planting_year), (len(c),)))
    return np.array([C.PLANTING_RADIUS + (k["r_mature"] - C.PLANTING_RADIUS) * (1 - math.exp(-k["growth"] * age))
                     for k, age in zip(c, ages)])


def survival_share(trees, year):
    if trees.empty:
        return 1.0
    age = np.clip((year - C.BASE_YEAR) / C.SURVIVAL_HORIZON_YEARS, 0, 1)
    mature = np.where(trees.engineered, C.SURVIVAL_ENGINEERED_SOIL, C.SURVIVAL_NATURAL_SOIL)
    weights = crown_radius(trees.size_class, year) ** 2
    return float(np.average(1 - age * (1 - mature), weights=weights))


def new_crowns(trees, L, year):
    geoms = []
    for planting in (L.get("committed", pd.DataFrame()), trees):
        if len(planting):
            dates = planting.get("planting_year", pd.Series(C.BASE_YEAR, index=planting.index))
            active = planting[dates <= year]
            rr = crown_radius(active.size_class, year, dates[dates <= year])
            geoms.extend(shapely.buffer(shapely.points(active.x, active.y), rr, quad_segs=12))
    return shapely.union_all(geoms)


def canopy_geometry(trees: pd.DataFrame, L: dict, year: int):
    """Existing canopy that is kept, plus the new crowns at their size in `year`."""
    ex = _kept(trees, L)
    geoms = list(shapely.buffer(shapely.points(ex.x.values, ex.y.values), ex.r.values, quad_segs=12)) if len(ex) else []
    geoms.append(new_crowns(trees, L, year))
    return unary_union(geoms) if geoms else Point(0, 0).buffer(0)


def _all_crowns(trees, L, year):
    ex = _kept(trees, L)
    tx, ty, tr = list(ex.x), list(ex.y), list(ex.r)
    if len(trees):
        tx, ty = tx + list(trees.x), ty + list(trees.y)
        tr = tr + list(crown_radius(trees.size_class, year))
    committed = L.get("committed", pd.DataFrame())
    if len(committed):
        active = committed[committed.planting_year <= year]
        tx += list(active.x)
        ty += list(active.y)
        tr += list(crown_radius(active.size_class, year, active.planting_year))
    return tx, ty, tr


def canopy_accounting(trees, L, year):
    """Raster fractional coverage plus new union on its uncovered fraction; no mixed baselines."""
    corr = L["corridor"]
    new = new_crowns(trees, L, year).intersection(corr)
    removal = L.get("canopy_removals", Point().buffer(0))
    R = L.get("raster")
    if R is not None:
        from .bomenkaart import weighted_cells
        cells, fraction = L["canopy_cells"] if "canopy_cells" in L else weighted_cells(R, corr)
        baseline = float(np.dot(shapely.area(cells), fraction))
        retained = shapely.difference(cells, removal)
        kept = float(np.dot(shapely.area(retained), fraction))
        overlap = float(np.dot(shapely.area(shapely.intersection(retained, new)), fraction))
    else:
        ex = existing_discs(L)
        old = (shapely.union_all(shapely.buffer(shapely.points(ex.x, ex.y), ex.r, quad_segs=12)).intersection(corr)
               if len(ex) else Point().buffer(0))
        baseline, kept = old.area, old.difference(removal).area
        overlap = old.difference(removal).intersection(new).area
    return dict(baseline_m2=baseline, kept_m2=kept, lost_m2=baseline - kept,
                new_m2=new.area - overlap, total_m2=kept + new.area - overlap)


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
    accounting = canopy_accounting(trees, L, year)
    baseline = canopy_accounting(trees.iloc[:0], L, year)["total_m2"] if n else accounting["total_m2"]
    return dict(
        canopy_pct=100 * accounting["total_m2"] / L["corridor"].area,
        survival_adjusted_canopy_pct=100 * (baseline + (accounting["total_m2"] - baseline) * survival_share(trees, year)) / L["corridor"].area,
        shade_pct=100 * covered.length / line.length,
        longest_gap_m=max((p.length for p in parts), default=0.0),
        natural_soil_pct=100 * float((~trees.paved.astype(bool)).mean()) if n else 0.0,
        route_sun_hours=route_sun_hours(trees, L, year),
        existing_kept_pct=100 * accounting["kept_m2"] / accounting["baseline_m2"] if accounting["baseline_m2"] else 100.0,
        existing_cleared_m2=accounting["lost_m2"],
        additional_canopy_m2=accounting["total_m2"] - baseline,
        trees=n,
        species=int(trees.species.nunique()) if n and "species" in trees else 0,
        max_species_share_pct=float(100 * trees.species.value_counts(normalize=True).max()) if n and "species" in trees else 0.0,
        max_genus_share_pct=float(100 * trees.genus.value_counts(normalize=True).max()) if n and "genus" in trees else 0.0,
        max_family_share_pct=float(100 * trees.family.value_counts(normalize=True).max()) if n and "family" in trees else 0.0,
        engineered_soil_m3=float(eng.soil_m3.sum()) if n else 0.0,
        rooting_volume_required_m3=float(trees.soil_m3.sum()) if n else 0.0,
        verified_trees=0,
    )


def targets_met(k: dict) -> int:
    met = 0
    for key, (op, val) in C.TARGETS.items():
        met += (k[key] >= val) if op == ">=" else (k[key] <= val)
    return int(met)


def run_option(L: dict, grid: pd.DataFrame, plants: pd.DataFrame, weights: dict, budget: int,
               enforce: bool = C.ENFORCE_10_20_30, allow_engineering=C.ALLOW_ENGINEERED_SOIL) -> PlantingResult:
    result = place_trees(grid, L, weights, budget, plants, enforce, allow_engineering)
    while enforce and len(result.trees) and not diversity_check(result.trees)["ok"]:
        result = place_trees(grid, L, weights, len(result.trees), plants, enforce, allow_engineering)
    trees = result.trees
    if len(trees):
        trees["phase"] = np.where(trees.engineered, "Conditional: engineered soil", "Conditional: open-ground survey")
    result.requested = budget
    return result
