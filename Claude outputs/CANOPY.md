# Canopy calculations

**Code:** geometry in [`backend/cover.py`](../cover.py), metric in [`covered_ground.py`](covered_ground.py), tree canopy in [`backend/model.py`](../model.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), sections 3, 5, 6 and 7 · **Shown in:** dashboard, "Covered ground" panel and the option cards

This file defines three related calculations:

1. **Building canopies:** built shelters on tall buildings, against wind, rain and sun.
2. **Road pergola:** a shelter over the middle of the carriageway.
3. **Covered ground:** how much ground 1 and 2 shelter, and the tree canopy KPI they combine with.

All geometry is in RD New (EPSG:28992), metres.

---

## 1. Building canopies

### Purpose

Tall buildings pull fast wind down their facades to street level. A horizontal canopy at pedestrian height breaks that downdraught. It also keeps rain and sun off the ground below, and its top can carry small greenery (an extensive green roof).

### Which buildings

Every building with `height > CANOPY_MIN_BUILDING_HEIGHT_M` (default **30 m**). Height comes from `buildings.geojson` (`height` property, from 3D BAG).

### Geometry, per building

For each outer facade segment of the footprint (the exterior ring, oriented anticlockwise so the outside is to the right):

1. Skip the segment if it is shorter than `CANOPY_MIN_FACADE_M` (4 m). This ignores small jogs.
2. Facade length `ℓ`, unit direction `u`, outward normal `n`.
3. Extension per end: `e = ℓ · CANOPY_EXTENSION_PCT / 100 / 2`.
4. The canopy is the rectangle from `start − u·e` to `end + u·e`, `CANOPY_WIDTH_M` deep along `n`.

```
            e            ℓ (facade)            e
        ◄───────►◄──────────────────────►◄───────►
        ┌────────────────────────────────────────┐  ▲
        │               canopy                   │  │ width
        └────────┬──────────────────────┬────────┘  ▼
                 │       building       │
```

Then, for all canopies together:

5. Union all rectangles.
6. Subtract every building footprint, so a canopy never runs into a neighbour or into its own inner corner.
7. If `CANOPY_AVOID_ROAD`, subtract the carriageway, so canopies do not overhang traffic.

Courtyards (inner rings) get no canopy. With 0 % extension the canopies stop at the corners and leave a small square gap at each outside corner; any extension above `width / ℓ` closes it.

**Check:** a 20 × 10 m building, 3 m wide, 10 % extension → long sides 22 × 3 m, short sides 11 × 3 m, four corner overlaps of 0.5 m² → 196 m². With 0 % → 2·60 + 2·30 = 180 m². Both match the code.

### Outputs

| Output | Meaning |
|---|---|
| `geom` | Union of all canopies |
| `n_buildings` | Buildings that got a canopy |
| `facade_m` | Total facade length with a canopy |

---

## 2. Road pergola

### Purpose

A strip of pergola along the middle of the carriageway, high enough for traffic (`PERGOLA_HEIGHT_M` = 5 m, above the 4.2 m clearance). It shades the asphalt, keeps rain off and carries climbers.

### Geometry, per road polygon

1. **Road width.** Estimated as the width of the rectangle with the same area `A` and perimeter `P`:
   `w = (P/2 − √((P/2)² − 4A)) / 2`. Exact for rectangles, close for long strips.
2. **Width cut.** Inset `i = w · (1 − PERGOLA_ROAD_PCT/100) / 2`; the strip is the road polygon buffered inward by `i` (mitred corners). At 30 % on a 7 m road: a 2.1 m strip centred on the axis.
3. **Length cut.** If `PERGOLA_LENGTH_PCT < 100`, keep a band centred on the middle of the road section, `PERGOLA_LENGTH_PCT` % of its length. The long axis comes from the polygon's minimum rotated rectangle, so this is approximate on curved roads.
4. Union all strips.

`PERGOLA_ROAD_PCT = 0` or `PERGOLA_LENGTH_PCT = 0` gives no pergola.

---

## 3. Covered ground

Counted **inside the corridor only**. Canopy area outside it is reported separately as `canopy_total_m2`.

| Output | Formula |
|---|---|
| `canopy_m2` | area(canopies ∩ corridor) |
| `pergola_m2` | area(pergola ∩ corridor) |
| `covered_m2` | area((canopies ∪ pergola) ∩ corridor) |
| `covered_public_pct` | `covered_m2` ÷ public ground (corridor minus buildings) |
| `pedestrian_covered_m2` | area(canopies ∩ corridor − carriageway) |
| `road_covered_pct` | `pergola_m2` ÷ area(carriageway ∩ corridor) |
| `sun_sheltered_m2` | `canopy_m2 · CANOPY_SUN_FACTOR + pergola_m2 · PERGOLA_SUN_FACTOR` |
| `rain_sheltered_m2` | `canopy_m2 · CANOPY_RAIN_FACTOR + pergola_m2 · PERGOLA_RAIN_FACTOR` |
| `green_on_structures_m2` | `canopy_m2 · CANOPY_GREEN_FRACTION + pergola_m2 · PERGOLA_GREEN_FRACTION` |
| `green_retention_m3` | `green_on_structures_m2 · GREEN_ROOF_RETENTION_L_M2 / 1000` |
| `rain_kept_off_m3` | `rain_sheltered_m2 · DESIGN_RAIN_MM / 1000` |
| `walk_zone_covered_pct` | Share of the walking zone (centreline ± `WALK_ZONE_HALF_WIDTH_M`) under canopies or pergola |
| `route_sheltered_structures_pct` | Share of the centreline within `SHADE_REACH_M` (2 m) of a canopy or the pergola |
| `route_sheltered_all_pct` | Same, with the tree crowns of the selected year added |

The sun and rain factors are 1.0 by default (a closed roof). Lower them for an open pergola with climbers only.

### Tree canopy cover (KPI, for reference)

The "Canopy" KPI on the option cards is **tree** canopy only: `area(∪ crown discs ∩ corridor) ÷ corridor area`, crowns of existing and new trees at the selected year, target 30 % (3-30-300). Built canopies are **not** counted in it. They appear in the covered-ground panel and in the combined sheltered-route figure, so the tree KPI stays comparable with the 3-30-300 rule.

---

## 4. Parameters

| Parameter | Default | Label |
|---|---|---|
| `CANOPY_ENABLED` | True | |
| `CANOPY_MIN_BUILDING_HEIGHT_M` | 30 m | Starting value |
| `CANOPY_WIDTH_M` | 3 m | Starting value |
| `CANOPY_EXTENSION_PCT` | 10 % | Starting value |
| `CANOPY_HEIGHT_M`, `CANOPY_THICKNESS_M` | 4.5 m, 0.4 m | 3D view only |
| `CANOPY_MIN_FACADE_M` | 4 m | Starting value |
| `CANOPY_AVOID_ROAD` | True | |
| `CANOPY_GREEN_FRACTION` | 0.8 | Starting value |
| `CANOPY_SUN_FACTOR`, `CANOPY_RAIN_FACTOR` | 1.0, 1.0 | Closed roof |
| `PERGOLA_ROAD_PCT` | 30 % | Starting value |
| `PERGOLA_LENGTH_PCT` | 100 % | Starting value |
| `PERGOLA_HEIGHT_M` | 5 m | Above 4.2 m clearance |
| `PERGOLA_GREEN_FRACTION` | 0.6 | Starting value |
| `PERGOLA_SUN_FACTOR`, `PERGOLA_RAIN_FACTOR` | 1.0, 1.0 | Closed roof |
| `GREEN_ROOF_RETENTION_L_M2` | 25 L/m² | Starting value |
| `DESIGN_RAIN_MM` | 70 mm | Klimaateffectatlas scenario (70 mm in 2 h) |
| `WALK_ZONE_HALF_WIDTH_M` | 4 m | |
| `SHADE_REACH_M` | 2 m | |
| `TREE_AVOID_CANOPIES` | True | No new trunks under a canopy |

## 5. Limits

- **Not a wind model.** The canopies show where a wind problem is likely and how much ground a standard shelter covers. Size real canopies with a wind study (CFD or wind tunnel, NEN 8100), which Dutch municipalities commonly ask for buildings over about 30 m.
- Every outer facade gets a canopy, including facades that face away from the public space or the wind. Filtering by orientation or by distance to the corridor is a possible next step.
- Shelter is counted as plan area. Low sun angles and driving rain reach under canopies; the sun and rain factors are a simple correction.
- The road width and length cuts are approximate on curved or irregular road polygons.
- On demo data the buildings sit just outside the corridor, so most canopy area falls outside it and the canopies do not reach the walking route.
