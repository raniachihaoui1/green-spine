# Green Spine – prompt for building the dashboard

Paste the block below into Claude Code, started from the `Greenspine` folder. It builds on the existing Streamlit dashboard
(`dashboard/app.py`, `bag3d.py`, `masterplan.py`) and follows its `CLAUDE.md`. Values marked **[ASSUMPTION]** are
suggested defaults. Every one of them is a slider or a config value, so the team can change it without touching code.

---

```text
ROLE
You are extending the Green Spine dashboard (Streamlit + pydeck) in Greenspine/dashboard. Read dashboard/CLAUDE.md first
and follow it: identifiers/UI/comments in Dutch, RD (EPSG:28992) internally, `uv add` for dependencies, never modify the
3D BAG tiles or the INPUTS zip, never present invented geometry as real data (label it "indicatief"). Add a line to the
Wijzigingslog after every change.

GOAL
A one-screen tool that generates and ranks tree-planting options for ONE corridor, running from the Fellenoord to the
Dommel. It puts trees only where the ground and climate support them, under three strategies, assigns species from our
plant database, grows them over time and reports four KPIs live. The pitch: corridors succeed above ground and fail
below it, and most schemes never measure their results. Our tool checks the soil and reports metrics.

SCREEN LAYOUT (from our sketch)
- Left sidebar = INPUT: data-layer toggles, parameter sliders (see PARAMETERS), strategy choice A/B/C.
- Centre = 3D LAYOUT: pydeck view with existing/masterplan masses (already built), corridor outline, 2 m suitability
  grid (toggle), trees as extruded crowns (ColumnLayer or SimpleMeshLayer spheres) coloured by species/size class.
  Below the map: a YEAR SLIDER (0, 5, 10, 25, 50) and an OPTION SLIDER that steps through the ranked layouts.
- Right column = OUTPUT: three option cards (A, B, C) with the four KPIs, a pass/fail badge per policy norm, and a
  "before/after" toggle (current situation vs. chosen option).
- Expander "Transparantie": data sources, assumptions, limitations, and how each KPI is calculated.

NEW MODULES (keep app.py thin)
- corridor.py   corridor polyline + buffer → mask (polygon). Read from data/corridor.geojson. If missing, build an
                indicative corridor along the Fellenoord to the Dommel and label it "indicatief".
- grid.py       2 m grid of cell centroids inside the mask (GeoDataFrame or numpy arrays), with a cell id.
- lagen.py      loaders for each input layer with an explicit fallback. If a file is missing, return a neutral layer and
                register the missing source in a list that is shown in the Transparantie panel.
- scoring.py    per cell: hard exclusions (boolean) + a weighted suitability score in [0,1].
- plaatsing.py  greedy placement per strategy with spacing and a soil-volume check (see PLACEMENT).
- soorten.py    species filter + assignment from the plant database (see SPECIES).
- groei.py      crown growth over time.
- kpi.py        the four KPIs + policy checks, computed for a given layout and year.
Cache the heavy steps (grid, scoring, shadow) with st.cache_data, keyed on the input file mtimes and the parameters.

INPUT DATA (read from Greenspine/dashboard/data/; all in RD)
Have:      3D BAG tiles (buildings), masterplan.geojson (placeholders), plant database xlsx in INPUTS.
Expected:  corridor.geojson            corridor centre line (and optionally the Dommeldal/EVZ outline)
           bomenkaart_2022.tif         RIVM "Bomen in Nederland" 2022, clipped to the study area: 10 x 10 m raster,
                                       value = % of the cell covered by trees > 2.5 m (0–100). Check the CRS on load
                                       (expected RD) and reproject if needed. This is the EXISTING CANOPY to respect.
                                       Optional siblings in the same format: struiken (shrubs), lage vegetatie (low).
           bomen_bestaand.geojson      optional individual trees (Eindhoven bomen open data): point, species, crown Ø.
                                       If present it refines the raster; if absent, the raster alone is enough.
           bgt_vlakken.geojson         BGT surfaces: wegdeel (paved), begroeidterreindeel (green), waterdeel, pand
           kabels_leidingen.geojson    utility zones (if unavailable: assume a 1.5 m strip along both kerbs of every
                                       wegdeel [ASSUMPTION])
           ondergronds.geojson         underground garages/basements (cluster 1A has a garage under the surface)
           hitte.tif / wateroverlast.tif   Klimaateffectatlas rasters (PET heat, flood depth at 70 mm/2 h)
           grondwater.geojson or a single GHG value   [ASSUMPTION fallback: GHG 0.8 m below surface, low-lying area]
For each missing file: use the fallback, show a yellow "ontbreekt – aanname gebruikt" chip in the sidebar.

HARD EXCLUSIONS (cell cannot hold a trunk)
- Inside a building footprint (BAG or masterplan scenario, depending on the selected scenario).
- Within the facade distance for the tree's size class: small 3 m, medium 5 m, large 7 m [ASSUMPTION].
- Carriageway, tram/bus lanes and the fire-access route: keep 4 m wide and 4.2 m high clear [ASSUMPTION].
- Utility strips and existing water surfaces.
- Above an underground structure, unless the slider "grondlaag op dek (m)" is ≥ 1.2 m. If it is, allow only small trees.
- Existing canopy (RESPECT): resample bomenkaart_2022 to the 2 m grid (nearest neighbour; each 2 m cell inherits
  its 10 m parent's %). Cells with cover ≥ slider "drempel bestaand kronendak" (default 30 % [ASSUMPTION]) are
  existing canopy: no new trunk there, plus a 3 m buffer to protect the root zone. Exception: canopy inside a
  masterplan building footprint or sloop area is flagged "vervalt door masterplan" (shown in orange) and counts as
  a loss in the KPIs. The miro's step 2 ("remove existing greenery") is a toggle "bestaand groen behouden" that
  defaults to ON; switching it OFF frees those cells but books the lost canopy against the option.

SUITABILITY SCORE (weights are sidebar sliders; normalise every factor to 0..1)
  S = w_bodem·bodem + w_zon·zon + w_hitte·hitte + w_mensen·mensen + w_verbinding·verbinding + w_water·water
- bodem:      available rooting soil. 1 for unpaved, 0.6 for paved but open to unsealing, 0 above structures.
- zon:        sun hours on 21 June. Compute with a 2 m height raster (numpy) from the 3D masses, shadow-cast at hourly
              sun positions (pvlib or a simple solar formula). More sun = better growth; tie to species shade tolerance.
- hitte:      heat need (PET raster, or the share of paved surface within 25 m as a proxy). Hotter = higher priority.
- mensen:     pedestrian benefit. Proxy: distance to the station/entrances + footpaths/cycle paths in BGT, higher near
              routes. Replace with real flow data if we get it.
- verbinding: closeness to existing canopy (bomenkaart cells ≥ threshold) or the Dommel (1 at 0 m, 0 at ≥ 100 m
              [ASSUMPTION]). New trees that bridge gaps between existing canopy patches score highest.
- water:      low-lying / flood-prone cells score higher for water-tolerant species and for infiltration value.

PLACEMENT (plaatsing.py)
Greedy: sort the cells by strategy score, place a tree, block the cells inside its spacing radius, repeat.
Size classes [ASSUMPTION, editable table]:
  class   mature height   crown Ø   spacing   min. soil volume   min. rooting depth
  small   6–12 m          4–6 m     6 m       15 m³              1.0 m
  medium  12–18 m         6–10 m    9 m       30 m³              1.2 m
  large   > 18 m          10–15 m   12 m      50 m³              1.2 m
Soil volume available to a tree = (unsealed or soil-cell area within its crown radius) × usable depth, where usable
depth = min(slider "doorwortelbare diepte", GHG − 0.3 m). If the volume is below the class minimum, try the next smaller
class. If no class fits, do not place a tree. Log every rejected cell with its reason. This drives the "below ground"
story in the pitch.
Strategies:
  A "Maximaal kronendak"  sort by S, always try the largest class first.
  B "Koelte eerst"        sort by hitte + mensen. Guarantee a cool spot (≥ 200 m², ≥ 50 % shade) within 300 m of
                          every corridor point (policy KPI 2.d.4 / clusterpaspoort 1A).
  C "Ecologische drager"  sort by verbinding + water. Fill gaps so no canopy gap along the corridor is > 30 m
                          [ASSUMPTION]. Favour native species and mixed layers (tree + shrub + herb).
Rank layouts with a weighted total of the normalised KPIs. The option slider steps through A, B, C and the 2 best
variants of each (random seeds / weight jitter), so the user sees up to 9 layouts.

SPECIES (soorten.py)
Source: INPUTS/INPROGRESS_merged_plant_database_modified_by_hand.xlsx, second sheet. The workbook contains formulas;
read with openpyxl data_only=True. If the cached values are empty, ask the team to re-save it in Excel as values or
CSV. Only rows with plant_type == "Tree" (≈59) are candidate trees; shrubs/herbs feed the understorey of strategy C.
Columns to use: species, height_m_summary / "Height, Mature (meters)", fp_spread (text like "4.5 m to 8 m": parse to
a number of metres and take the upper value), soil_type_summary (L/M/H), moisture_req_summary (D/M/We/Wa),
shade_tolerance_summary (F/S/N), "Drought Tolerance", "Salinity Tolerance", "Root Depth, Minimum (meters)",
"Anaerobic Tolerance", "Fire Tolerance", "Foliage Porosity Summer", growth_rate_summary (F/M/S), "Nursery Stock
Product", occurrence_count (local GBIF records = proxy for local fit).
Filter per placed tree: size class matches crown/height; shade tolerance matches the cell's sun hours; moisture/
anaerobic tolerance if the cell is flood-prone or the GHG is shallow; drought tolerance if the cell is paved/hot;
salinity tolerance within 5 m of a road (road salt). A missing value counts as "unknown". Allow unknowns but lower the
species' score and show the count in Transparantie.
Diversity rule: max 10 % per species, 20 % per genus, 30 % per family (Santamour) across the corridor.

GROWTH (groei.py)
crown_Ø(t) = Ø_plant + (Ø_max − Ø_plant) · (1 − e^(−k·t)), Ø_plant = 1.5 m; k = 0.12 / 0.08 / 0.05 for growth rate
F / M / S [ASSUMPTION]. Height scales the same way. Add a survival slider (default 85 % after 10 years if the soil rule
is met, 50 % if it was relaxed [ASSUMPTION]) applied as an expected-value multiplier on canopy KPIs.

FOUR KPIs (kpi.py) – show the value for the selected year, the delta vs. the current situation and a target line
1. Kronendak & groen/grijs-ratio (greenery / cement ratio)
   canopy % = (existing canopy kept + union of new crown discs) ∩ corridor / corridor area (target 30 %, "3-30-300"
   rule). Baseline "huidige situatie" = area-weighted mean of bomenkaart_2022 over the corridor. Show net change:
   + new canopy − canopy lost to the masterplan;
   unsealed % of public ground (policy: ≥ 50 % unsealed public space, clusterpaspoort 1A).
2. Hittestress (heat stress)
   % of footpath length shaded at 15:00 on 21 June; max distance to a cool spot (policy 2.d.4: ≤ 300 m).
3. Synergie-index (synergy / biodiversity)
   0.4 · connectivity (1 − largest canopy gap / 100 m) + 0.3 · Shannon diversity of species (normalised)
   + 0.3 · share of native species / species with wildlife value. Also show "aansluiting op Dommel-EVZ: ja/nee".
4. Bodemgezondheid & infrastructuur (soil & infrastructure impact)
   % of trees that meet the soil-volume rule; total soil volume required (m³); number of trees on or near utility
   strips (should be 0); count of rejected cells and why.
Secondary (small text under the cards): wind protection (number of trees within 30 m of masses > 70 m, weighted by
foliage porosity), fire-tolerance share, water storage proxy (unsealed m² × 60 mm vs. paved m², policy 2.d.3).
Policy check card "Groenopgave": required green = 8 m² per new dwelling + 10 % of non-residential BVO (KPI 2.d.1/2.d.2).
Derive it from the masterplan masses (BVO = footprint × floors, floors = height / 3.2 m; dwellings = residential
BVO / 75 m² [ASSUMPTION]) and compare it with the green m² delivered by the selected option.

WORK ORDER (feature freeze 16:00)
1. corridor + grid + exclusions visible on the map, with fallbacks for every missing layer.
2. scoring + strategy A placement end to end, with KPI 1 and 4.
3. strategies B and C, species assignment, KPI 2 and 3, growth slider.
4. option cards, ranking/option slider, before/after toggle, Transparantie panel.
5. Export: a PNG screenshot of before/after + a CSV of placed trees (id, x, y, class, species, soil volume, reason).
After each step, run the app headless (streamlit run … --server.headless true) and confirm that it starts without
errors before moving on.

ACCEPTANCE
- Changing any slider updates the map and KPIs within ~2 s (cache the heavy parts).
- Every number on screen can be traced through Transparantie to a source or an [ASSUMPTION].
- With all optional data files absent, the app still runs on fallbacks and clearly says so.
```

---

## Data still missing (for the team)

| Need | Status | Quickest source |
|---|---|---|
| Existing trees and green | **Covered at canopy level** by RIVM bomenkaart 2022 (10 m, % cover). No species, height or individual trees | Eindhoven open data "Bomen" (trees + species), BGT via PDOK (paved vs. green vs. water), AHN DSM−DTM for canopy height |
| Planned greenery and corridor route | **Qualitative only.** Norms are in clusterpaspoort 1A, but there is no geometry; `masterplan.geojson` is placeholders | Georeference the "raamwerk openbare ruimte" map from the Ontwikkelvisie in QGIS and digitise the corridor + Dommeldal EVZ (~30 min) |
| Soil and groundwater | Missing | BRO bodemkaart + groundwater levels (GHG); Fellenoord is one of the lowest areas in Eindhoven |
| Underground structures and utilities | Missing (KLIC is not public) | Garages from the clusterpaspoorten; otherwise the strip assumption |
| Heat, flooding | Missing | Klimaateffectatlas (PET heat map, flood depth) |
| Traffic and people flow | Missing | Gemeente/NDW intensities; otherwise a proxy based on distance to the station and footpaths |
| Plant database | Present, but thin for trees: 59 trees out of 1,477 rows; drought tolerance known for 29, salinity for 21, root depth for 32; spread is free text; formula cells | Add columns for street-tree size class, native yes/no and wildlife value; save as values |
| Animal / water databases (miro) | Not in the folder | Drop them for today, or use GBIF occurrences only |
