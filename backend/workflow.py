"""Cached application workflow. Every result is keyed by its inputs and reference."""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import shapely
import streamlit as st
from shapely.geometry import Polygon

from . import facades, parameters as P
from .cover import building_canopies, road_pergola
from .data_io import load_layers
from .model import base_grid, mask_grid, run_option, route_base
from .scenarios import load_masterplan, situation_metrics


@dataclass(frozen=True)
class Proposal:
    weights: tuple[float, float, float]
    budget: int = P.TREE_BUDGET_DEFAULT
    engineering: bool = P.ALLOW_ENGINEERED_SOIL
    diversity: bool = P.ENFORCE_10_20_30
    canopies: bool = P.CANOPY_ENABLED
    pergola: bool = P.PERGOLA_ENABLED
    canopy_width: float = P.CANOPY_WIDTH_M
    pergola_width: float = P.PERGOLA_ROAD_PCT


@st.cache_data(show_spinner="Loading source layers")
def references(fingerprint):
    existing = load_layers()
    existing["route"] = route_base(existing)
    return existing, load_masterplan(existing)


@st.cache_data(show_spinner="Checking ground, sunlight and boreholes")
def site(fingerprint, reference):
    L = references(fingerprint)[reference]
    if L is None:
        raise ValueError("No masterplan geometry supplied. Masterplan assessment is unavailable.")
    plants = pd.read_csv(Path(P.PROCESSED_DIR) / "plants.csv")
    grid = base_grid(L, tuple(plants.species))
    bands = facades.facade_sun(facades.street_facades(L), L)
    return L, plants, grid, bands


@st.cache_data(show_spinner=False)
def structures(fingerprint, reference, settings):
    L = site(fingerprint, reference)[0]
    can = building_canopies(L, width=settings.canopy_width)["geom"] if settings.canopies else Polygon()
    per = road_pergola(L["road"], settings.pergola_width) if settings.pergola else Polygon()
    return (shapely.union_all([L.get("canopies", Polygon()), can]),
            shapely.union_all([L.get("pergola", Polygon()), per]))


@st.cache_data(show_spinner="Testing planting options")
def planting(fingerprint, reference, settings):
    L, plants, grid, _ = site(fingerprint, reference)
    can, _ = structures(fingerprint, reference, settings)
    eligible = mask_grid(grid, L, no_plant=can if P.TREE_AVOID_CANOPIES else None)
    weights = dict(zip(("heat", "soil", "gap"), settings.weights))
    return run_option(L, eligible, plants, weights, settings.budget, settings.diversity, settings.engineering)


@st.cache_data(show_spinner=False)
def walls(fingerprint, reference, year, share, settings=None):
    L, _, _, bands = site(fingerprint, reference)
    roots = None
    if settings is not None:
        trees = planting(fingerprint, reference, settings).trees
        if len(trees):
            roots = shapely.union_all(shapely.from_wkt(trees.root_zone_wkt.to_numpy()))
    return facades.green_facades(bands, L, year, share, roots)


@st.cache_data(show_spinner="Measuring the proposal")
def results(fingerprint, reference, settings, year, facade_share):
    L = site(fingerprint, reference)[0]
    trees = planting(fingerprint, reference, settings).trees
    can, per = structures(fingerprint, reference, settings)
    G = walls(fingerprint, reference, year, facade_share, settings)
    return situation_metrics(L, trees, year, can, per, G["area_m2"])


@st.cache_data(show_spinner=False)
def baseline(fingerprint, reference, year):
    L = references(fingerprint)[reference]
    if L is None:
        return None
    return situation_metrics(L, pd.DataFrame(), year)


@st.cache_data(show_spinner=False)
def growth(fingerprint, reference, settings):
    from .model import canopy_accounting, survival_share
    L = site(fingerprint, reference)[0]
    trees = planting(fingerprint, reference, settings).trees
    rows = []
    for year in range(P.BASE_YEAR, P.YEAR_MAX + 1, P.YEAR_STEP):
        base = canopy_accounting(trees.iloc[:0], L, year)["total_m2"]
        total = canopy_accounting(trees, L, year)["total_m2"]
        rows.append(dict(Year=year, **{
            "Canopy potential (%)": 100 * total / L["corridor"].area,
            "Survival-adjusted estimate (%)": 100 * (base + (total - base) * survival_share(trees, year)) / L["corridor"].area,
            "Reference (%)": 100 * base / L["corridor"].area}))
    return pd.DataFrame(rows).set_index("Year")
