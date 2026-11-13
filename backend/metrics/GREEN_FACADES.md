# Green facades

**Code:** [`backend/facades.py`](../facades.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), section 12 · **Shown in:** dashboard, Results ("Green facades" and the Facades tab), map layer "Green facades"

## What it does

Puts climbing plants on the street-facing walls along the corridor: the vertical part of the green spine.

## Calculation

1. **Street walls.** Outer walls of at least 4 m (`FACADE_MIN_LENGTH_M`) of buildings within 15 m of the corridor (`FACADE_REACH_M`), facing the corridor. On the current data: 51 walls on 14 buildings, 669 m.
2. **Sun per wall.** For each floor band (3 m, up to 12 m), direct-sun hours on 21 June at the middle of the band, 0.5 m in front of the wall. A moment counts when the sun is in front of the wall and no building taller than the band shades the point (same shadow method as [`backend/sun.py`](../sun.py)).
3. **Which walls.** The sunniest walls first (they heat up most and gain most from greening), until the chosen share of the street-facade length is green (slider, default 50%).
4. **Which climber.** From the team's soil-compatible list (`fellenoord_compatible_plants.csv`): plant type Vine, at least 2.5 m tall. The wall's sun class decides which climbers are allowed, using the database shade columns:
   - **full sun** (6 h or more): Shade: No shade = TRUE;
   - **part shade** (3–6 h): Shade: Semi = TRUE;
   - **full shade** (under 3 h): Shade: Full = TRUE (ivy, honeysuckle).

   Climbers that reach two floors (6 m) come first; among those, species are spread over the walls.
5. **Green area** = wall length × green height, where the green height stops at 12 m, at the building height, or at the climber's mature height, whichever is lowest.

## Results (current data, 50%)

24 walls on 10 buildings, about 3,500 m², with ivy, honeysuckle, hop and grapevine.

## Limits

- Grapevine (*Vitis vinifera*) is not native. Hop, honeysuckle and ivy are. Mark climbers as native in the plant table to filter them.
- Sun is measured at one point per wall and band. Windows, balconies and wall material are not known.
- Facade greening does not yet feed the other metrics (nature score, heat stress, rain). Its cooling of the wall and the street is not modelled.
