# Rain kept on site

**Code:** [`water.py`](water.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), sections 7, 8 and 12 · **Shown in:** dashboard, Results

## What it measures

The share of a heavy storm, 70 mm in 2 hours (`DESIGN_RAIN_MM`, Klimaateffectatlas scenario), that the corridor keeps instead of sending it to the sewer or the street.

## Calculation

Rain falling on all public ground (corridor minus buildings) = public area × 70 mm.

Kept on site:

| Part | Formula | Parameter |
|---|---|---|
| Soaks in | (open ground + one 9 m² tree pit per tree planted in paving) × 50 mm | `INFILTRATION_MM`, `ECO_TREE_PIT_M2` |
| Held by crowns | crown area in the corridor (kept existing trees + new trees in the chosen year) × 1.5 mm | `CROWN_INTERCEPTION_MM` |
| Held by green roofs | greenery on wind canopies and pergola × 25 L/m² | `GREEN_ROOF_RETENTION_L_M2` |

Rain kept = the sum, capped at the storm volume, as % of the storm. "vs today" uses no new trees and no built shelter.

## Limits

- Fixed soak-in and interception values (starting values), not a flood or groundwater model. Ground height, flood depth and groundwater are not in the data yet.
- Paving is assumed to send all its rain away. Gutters, sewers and permeable paving are not modelled.
- Next step: ground height from AHN (low spots), the Klimaateffectatlas flood map and groundwater depth from BRO, as a fourth "Sponge" strategy.
