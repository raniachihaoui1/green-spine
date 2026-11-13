# Wind index

**Code:** [`wind.py`](wind.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), section 9 · **Shown in:** dashboard, Outputs panel

## What it measures

Tall buildings pull fast wind down to street level. Trees and canopies close to their facades break that downdraught for people walking past. The wind index is the share of tall-building facade along the corridor that has shelter next to it.

**It is a geometric proxy, not a wind simulation.**

## Calculation

1. Tall facades: the outer walls of buildings taller than `WIND_TALL_BUILDING_M` (30 m), within `WIND_CORRIDOR_REACH_M` (30 m) of the corridor. On the current data: 6 buildings.
2. Wind index (trees) = facade length with a tree crown (kept existing canopy plus new trees at the chosen year) within `WIND_SHELTER_REACH_M` (10 m), ÷ total tall facade length.
3. With canopies = the same, counting the building canopies as shelter too.

The canopies are drawn along every outer facade of every tall building (see [`CANOPY.md`](CANOPY.md)), so "with canopies" is 100% whenever they are switched on. That is why the trees are reported on their own as the main number.

## Limits

- No wind direction, building shape effects or foliage porosity (the plant table has no porosity data).
- Facades facing away from the corridor count the same as facades facing it.
- Size real shelter with a wind study (NEN 8100), as Dutch municipalities ask for buildings over about 30 m.
