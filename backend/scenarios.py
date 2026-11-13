"""The three global views of the dashboard and one comparable set of metrics for each.

  Existing situation   today's buildings, roads and kept canopy; no new trees, no built shelter
  Masterplan           existing situation + wind canopies on tall buildings + green pergola over the road
                       (indicative geometry from backend/cover.py, no masterplan file yet)
  Planting scenario    masterplan + the trees of strategy A, B or C

`situation_metrics` returns the same keys for every view, so the dashboard can chart them side by side.
"""
import pandas as pd
from shapely.geometry import Polygon
from . import parameters as P
from .metrics import covered_ground, ecosystem_score, heat_stress, wind_index, water_retention
from .model import canopy_geometry, kpis

EMPTY = Polygon()

# Metrics in the performance chart: key -> (label, unit, target or None, higher is better).
# All are on a 0-100 scale, so they share one axis. Targets come from parameters.py.
CHART_METRICS = {
    "canopy_pct": ("Tree cover", "%", P.TARGETS["canopy_pct"][1], True),
    "shade_pct": ("Shaded walk (crowns)", "%", P.TARGETS["shade_pct"][1], True),
    "shade_3pm_pct": ("Shade at 3 pm (all)", "%", None, True),
    "rain_kept_pct": ("Rain kept on site", "%", None, True),
    "wind_pct": ("Wind shelter", "%", None, True),
    "nature_score": ("Nature score", "/100", None, True),
}


def situation_metrics(L: dict, plants: pd.DataFrame, trees: pd.DataFrame, year: int,
                      canopies=None, pergola=None) -> dict:
    """Flat dict of headline metrics for one situation. `trees` may be empty (existing, masterplan)."""
    canopies = EMPTY if canopies is None else canopies
    pergola = EMPTY if pergola is None else pergola
    K = kpis(trees, L, year)
    crowns = canopy_geometry(trees, L, year)
    cover = covered_ground(L, canopies, pergola, crowns)
    heat = heat_stress(trees, L, year, canopies, pergola)
    wind = wind_index(trees, L, year, canopies, crowns)
    water = water_retention(trees, L, year, cover["green_on_structures_m2"])
    eco = ecosystem_score(trees, L, plants, year, K)
    return dict(
        **K,
        shade_3pm_pct=heat["shaded_pct"],
        rain_kept_pct=water["kept_pct"],
        wind_pct=wind["with_canopies_pct"] if wind["with_canopies_pct"] is not None else 0.0,
        nature_score=eco["score"],
        covered_m2=cover["covered_m2"],
        green_on_structures_m2=cover["green_on_structures_m2"],
    )


def performance_table(rows: dict) -> pd.DataFrame:
    """Long table (situation, metric, value, target) for the chart, from {situation: metrics}."""
    out = []
    for name, m in rows.items():
        for key, (label, unit, target, _) in CHART_METRICS.items():
            out.append(dict(situation=name, metric=label, unit=unit, value=float(m[key]), target=target))
    return pd.DataFrame(out)
