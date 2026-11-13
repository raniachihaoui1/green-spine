# CLAUDE.md: Green Spine

Read this file before changing anything in the repo. It holds the requirements, conventions and status. Add a line to the **Change log** (section 9) after every change.

Background, site facts, team and sources are in [docs/PROJECT_SCOPE.md](docs/PROJECT_SCOPE.md) and [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md). This file merges in the full dashboard specification from `GreenSpine_dashboard_prompt.md` (section 6), adapted to this repo.

---

## 1. Goal

A one-screen Streamlit + pydeck tool that generates and ranks tree-planting options for **one corridor, from Fellenoord to the Dommel** (Eindhoven). It puts trees only where the ground and climate support them, under three strategies, assigns species from the plant database, grows them over time and reports KPIs live. It also places built shelter (building canopies and a road pergola) and reports the ground it covers.

Pitch: corridors succeed above ground and fail below it, and most schemes never measure their results. Our tool checks the soil and reports metrics. *We did not place trees where they look good, we placed them where the ground can carry them.*

## 2. Conventions

- **All parameters live in [`backend/parameters.py`](backend/parameters.py).** Never hard-code a number in `app.py` or the backend. A new tunable value goes in that file with a unit and a label (`STARTING VALUE` = placeholder to confirm, `SOURCE` = named policy or rule). Sliders use those values as defaults. `backend/config.py` only re-exports `parameters.py` for older imports.
- Coordinates: RD New (EPSG:28992) internally; convert to WGS84 only for pydeck.
- Code, identifiers, UI text and comments are in **English** (the repo convention). The original prompt asked for Dutch; the repo was built in English, so English stays unless the team decides otherwise.
- Environment: `gsenv` on Python 3.13, `pip install -r requirements-lock.txt` (see README). When you add a package: add it to `requirements.txt` and refresh `requirements-lock.txt`.
- Never modify the raw inputs (3D BAG tiles, the INPUTS folder, the plant database xlsx). Write derived files to `data/` or `Processed_data/`.
- Never present invented geometry as real data. Label demo and assumed geometry "indicative" in the UI.
- Keep `app.py` thin: computation goes in `backend/`. Cache heavy steps with `st.cache_data`, keyed on the parameters.
- After each change, run `streamlit run app.py --server.headless true` and confirm that it starts without errors.
- **Existing tree data is being analysed and clipped to the scope by the team. Do not touch the tree data or its loader until they hand it over.**

## 3. Repo layout

| Path | Role |
|---|---|
| `app.py` | Streamlit dashboard: sidebar, option cards, 3D map, targets, covered ground, planting schedule |
| `backend/parameters.py` | **Every tunable parameter** |
| `backend/config.py` | Backwards-compatible alias of `parameters.py` |
| `backend/data_io.py` | Loads GeoJSON layers from `data/`; falls back to demo data |
| `backend/demo_data.py` | Synthetic corridor, buildings, road, trees (indicative only) |
| `backend/model.py` | Grid → mask (incl. tree setbacks) → score → place → species → growth → KPIs |
| `backend/cover.py` | Building canopies, road pergola, covered-ground analysis |
| `data/plants.csv` | Starter species table (20 native species) |
| `Assets_inputs/` | Raw inputs: 3D BAG tiles, INPUTS folder, sketches. Read-only |
| `docs/` | Project scope and log |

## 4. Built shelter and setbacks (added 13 Nov 2026)

All values in `backend/parameters.py`, all adjustable in the sidebar.

### 4.1 Building canopies (wind shelter)

Tall buildings push wind down to the street. A canopy at pedestrian height breaks that downdraught for people walking below. It also shelters the ground from rain and sun, and its top can carry small greenery.

| Parameter | Default | Meaning |
|---|---|---|
| `CANOPY_MIN_BUILDING_HEIGHT_M` | 30 m | Canopies only on buildings taller than this |
| `CANOPY_WIDTH_M` | 3 m | Depth of the canopy, out from the facade |
| `CANOPY_EXTENSION_PCT` | 10 % | Extra canopy length past the building corners, as % of the facade length, split evenly over both ends |
| `CANOPY_HEIGHT_M` | 4.5 m | Height above the street (3D view) |
| `CANOPY_MIN_FACADE_M` | 4 m | Shorter facade segments get no canopy |
| `CANOPY_AVOID_ROAD` | on | Cut canopies back where they would overhang the carriageway |
| `CANOPY_GREEN_FRACTION` | 0.8 | Share of the canopy top with small greenery |
| `CANOPY_SUN_FACTOR`, `CANOPY_RAIN_FACTOR` | 1.0 | Share of sun / rain kept off the ground below |

Geometry: every outer facade of a qualifying footprint gets a rectangle `width` deep, lengthened by the extension; the union is cut back by all building footprints (and the road, if set). This is a geometric proxy, not a wind simulation. Size real canopies with a wind study.

### 4.2 Road pergola

| Parameter | Default | Meaning |
|---|---|---|
| `PERGOLA_ROAD_PCT` | 30 % | Pergola width as % of the carriageway width, centred on the road axis |
| `PERGOLA_LENGTH_PCT` | 100 % | Share of each road section's length covered, centred on its middle |
| `PERGOLA_HEIGHT_M` | 5.0 m | Underside height (keeps the 4.2 m traffic clearance) |
| `PERGOLA_GREEN_FRACTION` | 0.6 | Share of the top with climbers / small greenery |
| `PERGOLA_SUN_FACTOR`, `PERGOLA_RAIN_FACTOR` | 1.0 | Share of sun / rain kept off |

Geometry: per road polygon, width is estimated as the equivalent-rectangle width; the strip is an inward buffer of `width × (1 − pct)/2`. The length cut uses the polygon's minimum rotated rectangle, so it is approximate on curved roads.

### 4.3 Tree setbacks

| Parameter | Default | Meaning |
|---|---|---|
| `TREE_SETBACK_BUILDING_M` | 5 m | No new trunk within this distance of a facade |
| `TREE_SETBACK_ROAD_M` | 2 m | No new trunk within this distance of the carriageway |
| `TREE_AVOID_CANOPIES` | on | No new trunk under a building canopy |

Applied as hard exclusions in `model.build_grid`. Later: per size class (3 / 5 / 7 m), see 6.4.

### 4.4 Covered-ground analysis (`cover.covered_ground`)

Counted inside the corridor:

- covered ground (union of canopies and pergola) in m² and as % of public ground (corridor minus buildings)
- canopy area, number of buildings with canopies, facade length; pergola area and % of carriageway covered
- pedestrian ground under canopies (canopy outside the carriageway)
- ground sheltered from sun and from rain (area × sun / rain factor)
- small greenery on structures (area × green fraction) and the rain it holds (`GREEN_ROOF_RETENTION_L_M2`, default 25 L/m²)
- rain kept off the ground per design storm (`DESIGN_RAIN_MM`, default 70 mm in 2 h)
- sheltered route: % of the centreline under structures alone, and with tree crowns for the selected year

## 5. Current state of the app

- Runs on demo data until `corridor.geojson` and `centreline.geojson` are in `data/` (see 7).
- Strategies: A Most shade, B Most connected, C Lowest cost, plus custom weights (heat, soil, gap).
- KPIs live: canopy cover, shaded route, longest gap, trees in natural soil; plus tree count, species count, largest species share, engineered soil volume, and the covered-ground panel.
- Exports: planting schedule CSV, KPI JSON.

## 6. Full specification (merged from `GreenSpine_dashboard_prompt.md`)

The target design. Values marked **[ASSUMPTION]** are suggested defaults; each one becomes a parameter in `parameters.py`. The status column shows what exists in this repo.

### 6.1 Screen layout

| Part | Requirement | Status |
|---|---|---|
| Left sidebar (INPUT) | Data-layer toggles, parameter sliders, strategy choice A/B/C | Sliders and strategy done; layer toggles to do |
| Centre (3D LAYOUT) | pydeck view with existing/masterplan masses, corridor outline, 2 m suitability grid (toggle), trees as extruded crowns coloured by species/size class, canopies and pergola. Below the map: YEAR slider (0, 5, 10, 25, 50) and OPTION slider stepping through ranked layouts | Map done; grid toggle, option slider to do; year slider is in the sidebar |
| Right column (OUTPUT) | Option cards A, B, C with the KPIs, pass/fail badge per policy norm, before/after toggle | Cards and targets table done; before/after to do |
| Transparency expander | Data sources, assumptions, limitations, how each KPI is calculated | Basic "Assumptions" expander; to extend |

### 6.2 Modules

The prompt proposed `corridor.py`, `grid.py`, `lagen.py` (layers), `scoring.py`, `plaatsing.py` (placement), `soorten.py` (species), `groei.py` (growth), `kpi.py`. This repo currently combines grid, scoring, placement, species, growth and KPIs in `backend/model.py`, layers in `backend/data_io.py`, and shelter in `backend/cover.py`. Split `model.py` along those lines when it grows. Cache grid, scoring and shadow, keyed on input file mtimes and parameters.

### 6.3 Input data (all RD)

| File | Content | Status |
|---|---|---|
| 3D BAG tiles | Buildings | In `Assets_inputs/` (4 tiles); to convert to `buildings.geojson` with `height` |
| `masterplan.geojson` | Masterplan masses (placeholders) | Missing |
| Plant database xlsx | `INPUTS/INPROGRESS_merged_plant_database_modified_by_hand.xlsx`, second sheet | In `Assets_inputs/INPUTS…`; app still uses `data/plants.csv` |
| `corridor.geojson` + `centreline.geojson` | Corridor polygon and walking line (optionally the Dommeldal/EVZ outline) | Missing; **blocks the real-data run**. If missing, use the indicative corridor and label it |
| `bomenkaart_2022.tif` | RIVM "Bomen in Nederland" 2022, 10 m raster, % cover by trees > 2.5 m. Check CRS on load. The existing canopy to respect. Optional siblings: shrubs, low vegetation | Missing |
| `bomen_bestaand.geojson` / `trees_existing.geojson` | Individual trees (Eindhoven open data): point, species, crown Ø | **Being prepared by the team. Do not touch** |
| `bgt_vlakken.geojson` | BGT surfaces: road, green, water, building | Missing (app uses `road.geojson`, `unpaved.geojson`) |
| `kabels_leidingen.geojson` / `utilities.geojson` | Utility zones. Fallback: 1.5 m strip along both kerbs of every road [ASSUMPTION] | Missing; demo strip used |
| `ondergronds.geojson` | Underground garages/basements (cluster 1A has one) | Missing |
| `hitte.tif`, `wateroverlast.tif` | Klimaateffectatlas: PET heat, flood depth at 70 mm/2 h | Missing |
| `grondwater.geojson` or one GHG value | Fallback: GHG 0.8 m below surface [ASSUMPTION] | Missing |

For each missing file: use the fallback and show a yellow "missing – assumption used" chip in the sidebar.

### 6.4 Hard exclusions (cell cannot hold a trunk)

- Inside a building footprint (BAG or masterplan, per scenario). **Done (BAG/demo).**
- Within the facade distance: one setback parameter now (**done**); per size class small 3 m, medium 5 m, large 7 m [ASSUMPTION] to do.
- Within the road setback (**done**); carriageway, tram/bus lanes and fire-access route keep 4 m wide and 4.2 m high clear [ASSUMPTION].
- Under a building canopy (**done**, toggle).
- Utility strips (**done**) and existing water surfaces (to do).
- Above an underground structure, unless "soil layer on deck" ≥ 1.2 m; then only small trees.
- Existing canopy: resample bomenkaart to 2 m (nearest neighbour). Cells with cover ≥ "existing canopy threshold" (default 30 % [ASSUMPTION]) get no new trunk, plus a 3 m root-zone buffer. Canopy inside a masterplan footprint or demolition area is flagged "lost to masterplan" (orange) and counts as a loss. Toggle "keep existing greenery" defaults ON; OFF frees those cells but books the lost canopy against the option.

### 6.5 Suitability score

`S = w_soil·soil + w_sun·sun + w_heat·heat + w_people·people + w_link·link + w_water·water`, weights as sliders, each factor 0..1. The repo currently uses heat, soil and gap.

- soil: 1 unpaved, 0.6 paved but open to unsealing, 0 above structures (repo: 1.0 / 0.35).
- sun: sun hours on 21 June from a 2 m height raster of the 3D masses, hourly sun positions. Tie to species shade tolerance.
- heat: PET raster, or share of paved surface within 25 m as proxy.
- people: distance to station/entrances + footpaths/cycle paths; replace with flow data if available.
- link: closeness to existing canopy or the Dommel (1 at 0 m, 0 at ≥ 100 m [ASSUMPTION]); gap-bridging scores highest.
- water: low-lying / flood-prone cells score higher for water-tolerant species.

### 6.6 Placement

Greedy: sort cells by strategy score, place a tree, block cells within spacing, repeat.

| Class | Mature height | Crown Ø | Spacing | Min. soil volume | Min. rooting depth |
|---|---|---|---|---|---|
| small | 6–12 m | 4–6 m | 6 m | 15 m³ | 1.0 m |
| medium | 12–18 m | 6–10 m | 9 m | 30 m³ | 1.2 m |
| large | > 18 m | 10–15 m | 12 m | 50 m³ | 1.2 m |

[ASSUMPTION, editable.] The repo still uses its own starting values in `TREE_CLASSES`; reconcile with the engineer.

Soil volume per tree = (unsealed area within crown radius) × usable depth, usable depth = min("rooting depth" slider, GHG − 0.3 m). Below the class minimum → try the next smaller class; none fits → no tree. Log every rejected cell with its reason.

Strategies (prompt version):
- A "Maximum canopy": sort by S, largest class first.
- B "Cool first": sort by heat + people. A cool spot (≥ 200 m², ≥ 50 % shade) within 300 m of every corridor point (policy 2.d.4 / cluster passport 1A).
- C "Ecological carrier": sort by link + water. No canopy gap > 30 m [ASSUMPTION]; native species and mixed layers.

Rank layouts by a weighted total of normalised KPIs. The option slider steps through A, B, C and the 2 best variants of each (seeds / weight jitter): up to 9 layouts.

### 6.7 Species

Source: plant database xlsx, second sheet; read with openpyxl `data_only=True` (formula cells; if cached values are empty, ask the team to re-save as values or CSV). Rows with `plant_type == "Tree"` (≈59) are candidate trees; shrubs/herbs feed strategy C's understorey. Columns: species, height_m_summary / "Height, Mature (meters)", fp_spread (parse "4.5 m to 8 m", take the upper value), soil_type_summary, moisture_req_summary, shade_tolerance_summary, "Drought Tolerance", "Salinity Tolerance", "Root Depth, Minimum (meters)", "Anaerobic Tolerance", "Fire Tolerance", "Foliage Porosity Summer", growth_rate_summary, "Nursery Stock Product", occurrence_count.

Filter per tree: size class; shade tolerance vs. sun hours; moisture/anaerobic tolerance if flood-prone or shallow GHG; drought tolerance if paved/hot; salinity tolerance within 5 m of a road. Missing values count as unknown: allowed, lower score, count shown in Transparency. Diversity: max 10 % species, 20 % genus, 30 % family (**done**).

### 6.8 Growth

`crown_Ø(t) = Ø_plant + (Ø_max − Ø_plant)·(1 − e^(−k·t))`, Ø_plant = 1.5 m, k = 0.12 / 0.08 / 0.05 for fast / medium / slow [ASSUMPTION]; height scales the same. Survival slider: 85 % after 10 years if the soil rule is met, 50 % if relaxed [ASSUMPTION], as an expected-value multiplier on canopy KPIs. (Repo: linear growth per class.)

### 6.9 KPIs

Show the value for the selected year, the delta vs. today, and a target line.

1. **Canopy and green/grey ratio:** canopy % = (existing canopy kept + new crowns) ∩ corridor / corridor area, target 30 % (3-30-300). Baseline = area-weighted bomenkaart mean. Net change = new − lost to masterplan. Unsealed % of public ground (≥ 50 %, cluster passport 1A).
2. **Heat stress:** % of footpath length shaded at 15:00 on 21 June; max distance to a cool spot (≤ 300 m, policy 2.d.4). Canopies and pergola count as shade (see 4.4).
3. **Synergy index:** 0.4·connectivity (1 − largest canopy gap/100 m) + 0.3·Shannon diversity (normalised) + 0.3·share native / wildlife value. Also "connects to Dommel EVZ: yes/no".
4. **Soil and infrastructure:** % trees meeting the soil-volume rule; total soil volume required; trees on/near utility strips (should be 0); rejected cells and why.

Secondary: wind protection (trees within 30 m of masses > 70 m weighted by foliage porosity, plus the building canopies), fire-tolerance share, water storage proxy (unsealed m² × 60 mm vs. paved m², policy 2.d.3; plus rain held by greenery on structures).

Policy card "Green requirement": 8 m² per new dwelling + 10 % of non-residential GFA (KPI 2.d.1/2.d.2). GFA = footprint × floors, floors = height / 3.2 m; dwellings = residential GFA / 75 m² [ASSUMPTION]. Compare with the green m² of the selected option (trees, unsealed ground and greenery on canopies/pergola).

### 6.10 Work order

1. Corridor + grid + exclusions on the map, with fallbacks for every missing layer.
2. Scoring + strategy A end to end, with KPI 1 and 4.
3. Strategies B and C, species, KPI 2 and 3, growth slider.
4. Option cards, ranking/option slider, before/after toggle, Transparency panel.
5. Export: PNG before/after + CSV of placed trees (id, x, y, class, species, soil volume, reason).

### 6.11 Acceptance

- Any slider change updates the map and KPIs within ~2 s.
- Every number on screen traces through the Transparency panel to a source or an [ASSUMPTION].
- With all optional data files absent, the app still runs on fallbacks and says so.

## 7. Switching to real data

Put these in `data/` (EPSG:28992). Without `corridor.geojson` and `centreline.geojson` the app uses the demo corridor.

| File | Content | Required |
|---|---|---|
| `corridor.geojson` | One polygon | Yes |
| `centreline.geojson` | One line | Yes |
| `buildings.geojson` | Polygons, property `height` (m); drives the canopies | Yes |
| `road.geojson` | Carriageway polygons; drives the pergola and road setback | Yes |
| `unpaved.geojson` | Open-ground polygons | Yes |
| `trees_existing.geojson` | Points, `crown_radius` (m). Being prepared by the team | Yes |
| `utilities.geojson`, `wet_zone.geojson` | Polygons | Optional |

## 8. Data still missing

| Need | Status | Quickest source |
|---|---|---|
| Existing trees and green | Covered at canopy level by RIVM bomenkaart 2022; individual trees being prepared by the team | Eindhoven open data "Bomen", BGT via PDOK, AHN DSM−DTM |
| Corridor route and planned green | Qualitative only (cluster passport 1A norms, no geometry) | Georeference the Ontwikkelvisie "raamwerk openbare ruimte" map in QGIS and digitise (~30 min) |
| Soil and groundwater | Missing | BRO soil map + GHG; Fellenoord is one of the lowest areas in Eindhoven |
| Underground structures and utilities | Missing (KLIC not public) | Garages from cluster passports; otherwise the strip assumption |
| Heat, flooding | Missing | Klimaateffectatlas |
| Traffic and people flow | Missing | Municipality/NDW; otherwise station/footpath proxy |
| Wind | No simulation; canopies are a geometric proxy | Wind study for buildings > 30 m |
| Plant database | Thin for trees (59 of 1,477 rows; drought 29, salinity 21, root depth 32; spread is text; formula cells) | Add street-tree size class, native yes/no, wildlife value; save as values |

## 9. Change log

| Date | Change |
|---|---|
| 13 Nov 2026 | Added `backend/parameters.py` as the single parameter file; `config.py` now re-exports it. |
| 13 Nov 2026 | Added building canopies on buildings above a height threshold (width and corner extension parameters), road pergola (% of road width and length), tree setbacks from buildings and roads, and the covered-ground analysis (`backend/cover.py`, new dashboard panel and sidebar sections). |
| 13 Nov 2026 | Created this CLAUDE.md, merging `GreenSpine_dashboard_prompt.md`. |
