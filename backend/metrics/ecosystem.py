"""Ecosystem score: one 0-100 KPI from four parts (habitat, diversity, connectivity, resilience).

Method, sources and limits: backend/metrics/ECOSYSTEM_SCORE.md.
All weights and targets: backend/parameters.py, section 8.
"""
import math
import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from shapely.ops import unary_union
from .. import parameters as P
from ..model import canopy_geometry, kpis
from ..feasibility import unsealed_ground

EMPTY = Polygon()


def _clip01(v):
    return float(min(max(v, 0.0), 1.0))


def _wmean(values: dict, weights: dict) -> float:
    tot = sum(weights.values()) or 1.0
    return sum(values[k] * w for k, w in weights.items()) / tot


def _shannon(labels) -> float:
    p = pd.Series(labels).value_counts(normalize=True).values
    return float(-(p * np.log(p)).sum())


def _rule_10_20_30(trees) -> bool:
    if trees.empty:
        return False
    for col, cap in (("species", P.MAX_SPECIES), ("genus", P.MAX_GENUS), ("family", P.MAX_FAMILY)):
        if col in trees and trees[col].value_counts(normalize=True).max() > cap + 1e-9:
            return False
    return True


def ecosystem_score(trees: pd.DataFrame, L: dict, plants: pd.DataFrame, year: int, K: dict | None = None) -> dict:
    """Ecosystem score for one planting option in one year.

    trees:  placed trees (columns species, genus, family, engineered, x, y, size_class)
    L:      layers from data_io.load_layers
    plants: plant table (columns species, native; optional wildlife)
    K:      the option's KPIs from model.kpis (computed here if not given)
    Returns the total (0-100), the four parts (0-1) and every indicator behind them.
    """
    K = K or kpis(trees, L, year)
    n = len(trees)
    corr = L["corridor"]
    crowns = canopy_geometry(trees, L, year).intersection(corr)
    bld = L["bld_union"] if L.get("bld_union") is not None else (unary_union([b for b, _ in L["buildings"]]) if L["buildings"] else EMPTY)
    public = corr.difference(bld) if not bld.is_empty else corr
    unpaved = L["unpaved"].intersection(corr) if not L["unpaved"].is_empty else EMPTY

    # ---- 1. Habitat --------------------------------------------------------
    canopy_pct = K["canopy_pct"]
    layered = crowns.intersection(unpaved).area / crowns.area if crowns.area and not unpaved.is_empty else 0.0
    unsealed_m2 = unsealed_ground(trees, L).area
    unsealed_pct = 100.0 * unsealed_m2 / public.area if public.area else 0.0
    hab_ind = dict(canopy=_clip01(canopy_pct / P.ECO_CANOPY_TARGET_PCT),
                   layered=_clip01(layered),
                   unsealed=_clip01(unsealed_pct / P.ECO_UNSEALED_TARGET_PCT))
    habitat = _wmean(hab_ind, P.ECO_HABITAT_W)

    # ---- 2. Diversity ------------------------------------------------------
    if n:
        info = plants.drop_duplicates("species").set_index("species")
        n_avail = info.index.nunique()
        h = _shannon(trees.species)
        h_max = math.log(min(n, n_avail)) if min(n, n_avail) > 1 else 1.0
        native = trees.species.map(info["native"].astype(str).str.lower().eq("yes")).fillna(False).mean()
        if "wildlife" in info:
            wildlife = trees.species.map(info["wildlife"].astype(str).str.lower().eq("yes")).fillna(False).mean()
            wildlife_src = "plant table"
        else:
            wildlife, wildlife_src = P.ECO_WILDLIFE_SHARE_DEFAULT, "assumption"
        div_ind = dict(shannon=_clip01(h / h_max), native=float(native), wildlife=float(wildlife))
        rule_ok = _rule_10_20_30(trees)
        diversity = _wmean(div_ind, P.ECO_DIVERSITY_W)
        if not rule_ok:
            diversity *= 0.0 if P.ECO_DIVERSITY_RULE_STRICT else 0.5
    else:
        div_ind, rule_ok, diversity, h, wildlife_src = dict(shannon=0.0, native=0.0, wildlife=0.0), False, 0.0, 0.0, "-"

    # ---- 3. Connectivity ---------------------------------------------------
    dommel = L.get("dommel")
    if dommel is None or dommel.is_empty:
        dommel = L.get("wet_zone", EMPTY)   # proxy until a Dommel valley / EVZ outline is in data/
    connects = bool(not dommel.is_empty and crowns.intersects(dommel))
    con_ind = dict(gap=_clip01(1.0 - K["longest_gap_m"] / P.ECO_GAP_ZERO_M), dommel=float(connects))
    connectivity = _wmean(con_ind, P.ECO_CONNECTIVITY_W)

    # ---- 4. Resilience -----------------------------------------------------
    if n:
        natural = float((~trees.paved.astype(bool)).mean())
        survival = float(np.where(trees.engineered, P.SURVIVAL_ENGINEERED_SOIL, P.SURVIVAL_NATURAL_SOIL).mean())
    else:
        natural = survival = 0.0
    res_ind = dict(natural_soil=natural, survival=survival)
    resilience = _wmean(res_ind, P.ECO_RESILIENCE_W)

    # ---- Total -------------------------------------------------------------
    parts = dict(habitat=habitat, diversity=diversity, connectivity=connectivity, resilience=resilience)
    w = P.ECO_WEIGHTS
    if P.ECO_AGGREGATION == "geometric":
        tot_w = sum(w.values()) or 1.0
        total = math.prod(max(parts[k], 1e-6) ** (w[k] / tot_w) for k in w)
    else:
        total = _wmean(parts, w)

    return dict(
        score=100.0 * total if n else None,
        status="Exploratory new-planting index; not comparable to unsurveyed existing ecology",
        parts=parts,
        indicators=dict(
            canopy_pct=canopy_pct, layered_share=layered, unsealed_pct=unsealed_pct,
            shannon=h, shannon_scaled=div_ind["shannon"], native_share=div_ind["native"],
            wildlife_share=div_ind["wildlife"], wildlife_source=wildlife_src, rule_10_20_30=rule_ok,
            longest_gap_m=K["longest_gap_m"], connects_dommel=connects,
            natural_soil_share=natural, expected_survival=survival,
        ),
    )
