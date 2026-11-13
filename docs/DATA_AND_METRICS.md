# Green Spine: data and metrics

What the dashboard is built on, where each piece came from, how it is used, and how every number on screen is calculated. Status: 13 November 2026, real Fellenoord data with a draft corridor. File details are in [data/SOURCES.md](../data/SOURCES.md); every parameter is in [backend/parameters.py](../backend/parameters.py).

## 1. Data

| Data | Source | How we collected it | How we used it | KPIs it feeds |
|---|---|---|---|---|
| Buildings with heights | 3D BAG (lod12), CC BY 4.0 | Downloaded through the 3D BAG web service by `scripts/fetch_data.py`: 3,248 building parts within 400 m of the corridor. Height = roof (70th percentile) minus ground level. The four tiles in `data/raw/3dbag/` are stored but not read by the app | No trees inside buildings or within 5 m of a facade. Cast shadows for sun hours. Buildings over 30 m push wind down to the street, which affects the comfort and wellbeing of people walking past: they get canopies and define the facades for the wind index | Sun hours, heat stress, wind index, covered ground; indirectly all planting KPIs (fewer plantable cells) |
| Existing trees | RIVM Bomenkaart 2022, 10 m cells, % cover by trees over 2.5 m | National raster clipped by a teammate to the Fellenoord scope plus 250 m (`scripts/clip_bomenkaart.py`) | Each cell becomes a disc with the same area as its tree cover. Counts as today's trees, casts shadows, sets the distance-to-trees (gap) score. Cells with 30% tree cover or more are protected, plus a 3 m root zone | Canopy cover (baseline 9–10%), shaded route, longest gap, existing trees kept, heat stress, wind index, synergy index |
| Roads | OpenStreetMap, ODbL | Downloaded by `scripts/fetch_data.py`; centre lines widened by road type (3.2 m per tagged lane) | No trees on the carriageway or within 2 m of it. Carries the road pergola | Plantable area; covered ground |
| Green areas | OpenStreetMap (grass, parks, gardens, scrub, woodland) | Downloaded by `scripts/fetch_data.py` | Open ground scores soil 1.0; everything else counts as paving (0.35) and needs engineered soil for large trees | Trees in natural soil, engineered soil volume, synergy index (habitat, resilience) |
| The Dommel and wet ground | OpenStreetMap river line | Downloaded by `scripts/fetch_data.py`; ground within 30 m of the river marked wet | Ends the corridor at the river. Wet cells get species that tolerate wet soil | Species choice; synergy index (connection to the Dommel) |
| Corridor and walking line | Derived from OpenStreetMap | **Draft:** mid-line of the Fellenoord and Dorgelolaan carriageways down to the Dommel, 909 m long, 30 m either side (5.45 ha). The architect still has to confirm it | Corridor area is the denominator for canopy cover. The walking line is where route shade and gaps are measured | Canopy cover, shaded route, longest gap, heat stress |
| Soil boreholes | BRO (Basisregistratie Ondergrond), downloaded from DINOloket | Collected by a teammate: 6 boreholes with layer depth, texture and made ground (`data/raw/soil/`) | The team's soil algorithm compares each plant's texture and root-depth needs with every borehole profile. In the app, each tree's species must fit the soil at its nearest usable borehole (score 0.6 or more). One borehole is unusable (its record starts at 0.8 m) | Species choice and the soil-fit column in the schedule. Barely changes results: only European white elm is ruled out |
| Plant database | Team, merged from GBIF, POWO, PlantNet, PFAF and ForwardPlant | Built by the team: 1,477 plants of all types, 75 of them trees (`data/raw/plants/`) | Input to the soil algorithm: soil texture and root depth per plant | Species choice |
| Soil-compatible species | Team's soil algorithm (`backend/soil.py`) on the plant database and the DINOloket boreholes | The algorithm keeps every plant that fits at least one borehole: 680 of 1,477 (trees, shrubs, herbs and grasses), 73 of them trees (`data/processed/fellenoord_compatible_plants.csv`) | The app plants trees only. It takes its species from a list of 20 native trees (`data/processed/plants.csv`, set up when the app was first built), and the algorithm checks each tree against its nearest borehole: 19 of the 20 pass. Size class sets crown and spacing; genus and family drive the 10-20-30 rule | Largest species share, synergy index (diversity, native share) |
| Climbing plants | Team's soil algorithm on the plant database | Plants of type Vine in the soil-compatible list that reach at least 2.5 m: 8 climbers, with their shade tolerance | Green facades: sunny walls get sun-loving climbers, shady walls ivy or honeysuckle | Green facades |
| Sun position | Calculated (standard solar formulas) | 21 June at Fellenoord (51.44° N, 5.48° E), every 30 minutes with the sun above 10° | Shadows of buildings and crowns, cell by cell and along the route | Sun hours, heat score for placement, heat stress |
| Policy targets | [1] 3-30-300 rule (Konijnendijk 2023); [2] Clusterpaspoort 1A Fellenoord (Gemeente Eindhoven); [3] 10-20-30 rule (Santamour 1990) | [1] and [3] from the published papers. [2] from the cluster passport in the team Drive, as quoted in the team's dashboard brief; its KPI annex is not checked yet. Shaded route ≥ 60%, longest gap ≤ 25 m and natural soil ≥ 60% are team proposals, not policy | 30% canopy cover per neighbourhood [1]; ≥ 50% unsealed public space [2]; at most 10% of trees per species, 20% per genus, 30% per family [3] | Target lines and pass/fail |

### References

1. Konijnendijk, C. (2023). Evidence-based guidelines for greener, healthier, more resilient neighbourhoods: introducing the 3–30–300 rule. *Journal of Forestry Research* 34, 821–830.
2. Gemeente Eindhoven. Clusterpaspoort 1A, Fellenoord. In the team Drive, GREENSPINE / INPUTS.
3. Santamour, F.S. (1990). Trees for urban planting: diversity, uniformity, and common sense. *Proceedings of the 7th Conference of the Metropolitan Tree Improvement Alliance (METRIA)* 7, 57–65.

## 2. Metrics

Only the four KPIs in the bar under the map have targets. They decide the "best fit" option: most targets met, then most canopy. The other outputs are reported, not ranked.

| Metric | How it is calculated | Target | How it affects the result |
|---|---|---|---|
| **Canopy cover** (KPI) | Kept existing canopy plus new crowns at the chosen year, inside the corridor, ÷ corridor area. Crowns grow linearly from 1 m radius to the mature size of their class | 30% or more (3-30-300) | Grows with the year and the tree budget. Large trees in open spots raise it most. Ranking tiebreak |
| **Shaded route** (KPI) | Length of walking line within 2 m of a crown, in plan, ÷ total length | 60% or more (team proposal) | Rises when trees are placed along the line. Option A (heat weight) and C push it up |
| **Longest gap** (KPI) | Longest stretch of walking line with no crown within 2 m | 25 m or less (team proposal) | Driven by the gap weight: option B fills gaps first. Also feeds the synergy index |
| **Trees in natural soil** (KPI) | Trees whose cell meets their class's soil need without engineered soil ÷ all new trees | 60% or more (team proposal) | Driven by the soil weight: option C keeps trees on open ground. Also feeds the synergy index |
| Engineered soil | Sum of rooting volume (6, 15 or 30 m³ by class) for trees planted in paving | None | Cost proxy. The trade-off against shade and gaps |
| 10-20-30 rule (Santamour 1990) | Largest share of one species, one genus and one family among the new trees. Each tree gets the least-used species that fits its soil and moisture and stays within the limits; if its size class has no such species left, it changes class (smaller first, larger only where spacing allows) | ≤ 10% species, ≤ 20% genus, ≤ 30% family [3] | Met for every option and budget tested (20–200 trees). Price: about two thirds of the 90 trees become medium or small, so canopy cover in 2040 drops 1–4 points (A 19 → 16%). The synergy index rises 7–15 points because its diversity part is no longer halved |
| Synergy index | Team's ecosystem score, 0–100 = average of four parts. Habitat: canopy vs 30%, crown over open ground, unsealed share vs 50%. Diversity: Shannon, native share, wildlife (assumed 0.5), halved if 10-20-30 is broken. Connectivity: 1 − longest gap ÷ 100 m, plus reaching the Dommel. Resilience: natural-soil share and expected survival (85% / 70%) | None | Combines the KPIs into one picture: 17 today; 57 (A), 59 (B), 70 (C) in 2040. Resilience separates the options most |
| Heat stress | Share of the walking line in shade at 15:00 on 21 June (sun 58° high, from the south-west), from buildings, canopy, new trees, canopies and pergola | None | Rises from 33% today to 43–49% in 2040, depending on the option |
| Wind index | Share of the facade of the 6 buildings over 30 m along the corridor with a tree crown within 10 m. Shown separately with the building canopies, which line every tall facade by design (always 100%). A geometric proxy, not a wind simulation | None | Low: 12% today, 12–15% in 2040, because the setbacks keep new trees away from facades |
| Existing trees kept | Existing tree cover in the corridor not cleared by a new trunk ÷ all existing tree cover | None | 100% with protection on. Switching protection off frees space but books the cleared canopy |
| Sun hours (per cell) | Half-hour steps on 21 June in which no building or crown shadow covers the cell | None | Feeds the heat score that places trees: sunny paving is planted first under option A. Map layer |
| Covered ground | Area under building canopies and the road pergola inside the corridor, with the rain kept off and the greenery on top | None | Separate panel. Not counted in tree canopy cover, so canopy stays comparable with 3-30-300 |
| Green facades | Street-facing walls of buildings within 15 m of the corridor, sunniest first, up to the chosen share; climbers matched to each wall's sun on 21 June, green up to 12 m or the climber's height | None | 50% of street facade gives about 3,500 m² of climbers on 10 buildings. Not yet counted in the other metrics |
| Rain kept on site | Share of a 70 mm storm on public ground held by open ground and tree pits (50 mm), crowns (1.5 mm) and green roofs on canopies and pergola (25 mm) | None | 18% today, about 23% in 2040 with option A. A rough estimate: no flood or groundwater data yet |

## 3. Limits

- The corridor is a draft and roads are today's layout, not the planned narrower boulevard.
- Tree sizes, growth, rooting volumes, setbacks and three of the four targets are starting values.
- Soil plantability is paved versus open ground. The boreholes only inform species choice, and none lie in the middle 400 m of the route.
- Not modelled: air temperature, wind flow, water, utilities, people flow, foliage porosity.
- All results are provisional until the corridor and tree classes are confirmed.
