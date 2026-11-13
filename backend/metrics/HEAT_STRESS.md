# Heat stress

**Code:** [`heat.py`](heat.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), section 9 · **Shown in:** dashboard, Outputs panel

## What it measures

The share of the assessment route in shade at **15:00 on 21 June**. This is solar geometry on the summer solstice, not necessarily the hottest day. The time follows the dashboard prompt, not a verified municipal cool-place calculation.

## Calculation

1. Sun position at 15:00 CEST (13:00 UTC) on 21 June at Fellenoord: about 58° high, from the south-west (217°). Same solar formulas as [`backend/sun.py`](../sun.py).
2. Sample points every 2 m along the walking line (`ROUTE_STEP`).
3. A point is in shade when it lies in the ground shadow of:
   - a building (each wall swept away from the sun by `height ÷ tan(sun height)`);
   - a tree crown: the kept existing canopy (RIVM discs) and the new trees at their size in the chosen year, as discs between 0.6 and 1.8 radii above the ground;
   - a building canopy at 4.5 m or the road pergola at 5 m, as a flat roof shifted by its height.
4. Buildings and trees fully block direct sun in this simplified model. Structures use their configurable sun-blocking factors; overlapping structures multiply transmission rather than double-count shade. Zero-factor shelter adds no shade.
5. Compare against the selected reference, including any committed shelter and trees. A second estimate scales the additional tree benefit by the assumed survival share. It is not a stochastic mortality model.

The result also splits the shade into buildings, trees and structures.

## Limits

- One moment on one clear day. It says where the sun falls, not how hot it gets. Air temperature, wind and reflected heat are not modelled.
- Cluster 1A's cool-place definition is 200 m2 with at least 50% vegetation shade, within 300 m walking. This needs accessible polygons and a walking network; the route-shade metric does not establish compliance.
- Cross-route shade deltas are suppressed if the imported reference changes the route.
- Partial raster-cell canopy removals use fractional area for canopy accounting but indicative whole-cell symbols for shadows. That discrepancy needs a surveyed canopy model before detailed design.
- The walking line is a draft along the carriageway mid-line.
