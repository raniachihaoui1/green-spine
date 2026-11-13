"""Separate measured design indicators from source-specific policy requirements."""
from .. import parameters as P


def policy_checks(metrics):
    return [
        {"Check": "Canopy ambition", "Requirement": f"{P.TARGETS['canopy_pct'][1]:g}%",
         "Result": f"{metrics['canopy_pct']:.1f}%", "Status": "Team corridor target; not full 3-30-300 compliance"},
        {"Check": "Unsealed public ground", "Requirement": f"{P.POLICY_UNSEALED_PCT:g}% within cluster 1A",
         "Result": f"{metrics['unsealed_pct']:.1f}% of this corridor",
         "Status": "Not assessed: corridor is not a supplied policy/ownership boundary"},
        {"Check": "Water storage", "Requirement": f"{P.POLICY_STORAGE_MM:g} mm per m2 public paving; "
         f"{P.POLICY_DESIGNED_STORAGE_MM:g} mm in designed facilities (1A)",
         "Result": "Not assessed", "Status": "Need policy boundary and verified storage inventory; storm proxy is not capacity"},
        {"Check": "Reachable cool place", "Requirement": f"{P.POLICY_COOL_AREA_M2:g} m2; "
         f"{P.POLICY_COOL_SHADE_PCT:g}% vegetation shade; within {P.POLICY_COOL_DISTANCE_M:g} m walking (1A)",
         "Result": "Not assessed", "Status": "Need accessible-space polygons and walking network; built shelter does not qualify"},
        {"Check": "Additional development greenery", "Requirement": f"{P.POLICY_GREEN_DWELLING_M2:g} m2/dwelling + "
         f"{P.POLICY_GREEN_GFA_SHARE:.0%} non-residential GFA (1A)",
         "Result": "Not assessed", "Status": "Need programme, compensation ledger and official quality weights"},
        {"Check": "Connected ecological corridor", "Requirement": "Context-specific ecological continuity",
         "Result": "Not assessed", "Status": "Canopy gaps are a proxy; touching the Dommel is not functional connectivity"},
    ]
