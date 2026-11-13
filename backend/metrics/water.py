"""Conserved, indicative storm balance on public ground; not certified storage capacity."""
import shapely
from shapely.geometry import Polygon

from .. import parameters as P
from ..feasibility import unsealed_ground
from ..model import canopy_geometry


def water_retention(trees, L, year, *, canopies=None, pergola=None):
    empty = Polygon()
    public = L["corridor"].difference(L.get("bld_union") or empty).difference(L.get("water", empty))
    can = (canopies if canopies is not None else empty).intersection(public)
    per = (pergola if pergola is not None else empty).intersection(public)
    can = can.difference(per)  # higher pergola takes precedence in the overlap
    roofs = shapely.union_all([can, per])
    open_ground = unsealed_ground(trees, L).intersection(public)
    infiltrating = open_ground.difference(L.get("underground", empty))
    crowns = canopy_geometry(trees, L, year).intersection(public).difference(roofs)
    rain = P.DESIGN_RAIN_MM
    interception = min(rain, P.CROWN_INTERCEPTION_MM)
    crown_m3 = crowns.area * interception / 1000
    soil_m3 = (
        infiltrating.difference(roofs).difference(crowns).area * min(rain, P.INFILTRATION_MM)
        + infiltrating.intersection(crowns).area * min(rain - interception, P.INFILTRATION_MM)
    ) / 1000
    roof_m3 = 0.0
    for geom, green, blocking in ((can, P.CANOPY_GREEN_FRACTION, P.CANOPY_RAIN_FACTOR),
                                  (per, P.PERGOLA_GREEN_FRACTION, P.PERGOLA_RAIN_FACTOR)):
        if not 0 <= green <= 1 or not 0 <= blocking <= 1:
            raise ValueError("Roof green and rain fractions must be between zero and one.")
        roof_m3 += geom.area * green * min(rain * blocking, P.GREEN_ROOF_RETENTION_L_M2) / 1000
        soil_m3 += geom.intersection(infiltrating).area * min(rain * (1 - blocking), P.INFILTRATION_MM) / 1000
    storm = public.area * rain / 1000
    kept = soil_m3 + crown_m3 + roof_m3
    return dict(kept_pct=100 * kept / storm if storm else 0.0, kept_m3=kept,
                storm_m3=storm, runoff_m3=max(0.0, storm - kept),
                soak_m3=soil_m3, crowns_m3=crown_m3, roofs_m3=roof_m3,
                unsealed_m2=open_ground.area,
                unsealed_pct=100 * open_ground.area / public.area if public.area else 0.0,
                public_m2=public.area,
                method="Indicative local rainfall only; no runoff routing or verified storage capacity")
