# Heat stress

**Code:** [`heat.py`](heat.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), section 9 · **Shown in:** dashboard, Outputs panel

## What it measures

The share of the walking route in shade at **15:00 on 21 June**, the hottest part of the longest day. More shade means less heat stress for people walking the corridor. The time follows the dashboard prompt (KPI 2, "% of footpath length shaded at 15:00 on 21 June").

## Calculation

1. Sun position at 15:00 CEST (13:00 UTC) on 21 June at Fellenoord: about 58° high, from the south-west (217°). Same solar formulas as [`backend/sun.py`](../sun.py).
2. Sample points every 2 m along the walking line (`ROUTE_STEP`).
3. A point is in shade when it lies in the ground shadow of:
   - a building (each wall swept away from the sun by `height ÷ tan(sun height)`);
   - a tree crown: the kept existing canopy (RIVM discs) and the new trees at their size in the chosen year, as discs between 0.6 and 1.8 radii above the ground;
   - a building canopy at 4.5 m or the road pergola at 5 m, as a flat roof shifted by its height.
4. Heat stress output = shaded points ÷ all points × 100. "vs today" is the same calculation with no new trees and no canopies or pergola.

The result also splits the shade into buildings, trees and structures.

## Limits

- One moment on one clear day. It says where the sun falls, not how hot it gets. Air temperature, wind and reflected heat are not modelled.
- No target is set: the prompt's companion KPI (cool spot within 300 m) needs a cool-spot definition that is not agreed yet.
- The walking line is a draft along the carriageway mid-line.
