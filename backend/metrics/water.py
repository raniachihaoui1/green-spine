"""Rain kept on site: how much of a heavy storm the corridor holds instead of sending to the sewer.

Method: backend/metrics/WATER.md. Parameters: backend/parameters.py, sections 7, 8 and 12.
Uses only layers we already have (no flood or groundwater map yet).
"""
from shapely.geometry import Polygon
from .. import parameters as P
from ..model import canopy_geometry

EMPTY = Polygon()


def water_retention(trees, L: dict, year: int, green_on_structures_m2: float = 0.0) -> dict:
    """Share of the design storm (DESIGN_RAIN_MM on all public ground) kept on site by
    open ground and tree pits (infiltration), tree crowns (interception) and greenery on
    canopies and pergola (green-roof retention)."""
    corr = L["corridor"]
    bld = L.get("bld_union")
    public = corr.difference(bld) if bld is not None and not bld.is_empty else corr
    rain = P.DESIGN_RAIN_MM / 1000.0
    storm = public.area * rain
    unpaved = L["unpaved"].intersection(corr).area if not L["unpaved"].is_empty else 0.0
    pits = int((trees.soil < P.SOIL_UNPAVED).sum()) * P.ECO_TREE_PIT_M2 if len(trees) and "soil" in trees else 0.0
    soak = (unpaved + pits) * min(P.INFILTRATION_MM, P.DESIGN_RAIN_MM) / 1000.0
    crowns = canopy_geometry(trees, L, year).intersection(corr).area * min(P.CROWN_INTERCEPTION_MM, P.DESIGN_RAIN_MM) / 1000.0
    roofs = green_on_structures_m2 * P.GREEN_ROOF_RETENTION_L_M2 / 1000.0
    kept = min(soak + crowns + roofs, storm)
    return dict(kept_pct=100.0 * kept / storm if storm else 0.0, kept_m3=kept, storm_m3=storm,
                soak_m3=soak, crowns_m3=crowns, roofs_m3=roofs)
