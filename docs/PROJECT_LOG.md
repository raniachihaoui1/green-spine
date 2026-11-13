# Green Spine: project log

AEC NL Hackathon 2026, Eindhoven. Challenge theme: Green Spine (native planting, urban forest and biodiversity).
Log written Friday 13 November 2026 at 12:57. It summarises the working session with Claude from 06:50 onward.

## 1. Where we are right now

| Item | Status |
|---|---|
| Concept, KPIs, algorithm | Agreed |
| Team split and timeline | On the Miro board |
| Backend and dashboard | First version runs on demo data (`streamlit run app.py`) |
| Real data in the app | Not yet: layers still need converting into `data/` |
| Corridor outline and centreline | Not drawn yet. This blocks the real-data run |
| Tree class numbers | Placeholders in `backend/config.py`, to be confirmed |
| Pitch and before/after image | Not started |
| Git | App files are in the local repo folder but not committed or pushed |

**Next three actions**

1. Architect draws `corridor.geojson` and `centreline.geojson` (EPSG:28992).
2. Convert the four 3D BAG tiles and the Eindhoven tree dataset into the files `backend/data_io.py` expects.
3. Engineer replaces the placeholder tree class values and confirms the targets.

## 2. The idea

**One sentence:** draw a line through the asphalt, and the tool plants a native urban forest along it, then shows canopy cover and habitat connection today, in 2040 and in 2060.

- **Why:** Fellenoord is paved and about to be rebuilt. Street-tree schemes often fail below ground, and their results are rarely measured.
- **What:** a tool that generates and ranks planting options for one corridor from Fellenoord to the Dommel, placing trees where the ground and climate support them.
- **How:** score every plantable 2 m cell, place trees under three strategies, assign species from the plant database, report the KPIs live.

**Pitch line:** we did not place trees where they look good, we placed them where the ground can carry them.

## 3. How we got here

| Time | Step |
|---|---|
| 06:50 | Team method and brainstorm plan for the hackathon; five seed ideas |
| 06:54 | Event shortened to one day; plan compressed, scope cut to one street and one metric |
| 08:10 | Fellenoord site facts researched; first slide deck built |
| 08:48 | Theme chosen: Green Spine. Concept and three metrics defined |
| 09:02 | Concept saved as a Claude Doc; site analysis added, then a slide version in Rania's portfolio style |
| 09:28 | GitHub repo requested; created by hand because the session could not create repos |
| 09:30 | Roles discussed for architect, structural engineer and AI student |
| 09:49 | Use of soil and greenery data worked out (overlay into four action classes) |
| 10:50 | Brainstorm board reviewed; why/what/how, reference projects, KPIs, data sources, algorithm and six-hour scope defined |
| 11:03 | Workflow diagram, methodology and team split added to the Miro board |
| 11:10 | Detailed step-by-step of the pipeline and the exact output |
| 11:42 | Data preparation method |
| 12:04 | Realistic plan, data availability, parameters, metrics, how options are generated |
| 12:09 | Drive folder read (on the IAAC account); contents inventoried |
| 12:12 | Data plan added to the Miro board |
| 12:14 | Backend and Streamlit dashboard built and tested on demo data |

## 4. Site facts used

Figures come from public search extracts gathered on 13 November 2026. Check the originals before quoting them to the jury.

- Fellenoord lies north of Eindhoven Centraal and is the core of Internationale Knoop XL (55 ha station area).
- 6,000 to 7,000 homes are planned where a few hundred people live today; 30% targeted for social rent.
- The KCAP plan downgrades the Fellenoord road from urban motorway to city boulevard, cutting traffic space to a 40 m minimum. That freed width is the planting area.
- The Dommel valley is designated as an ecological and recreational link; no new buildings on its banks.
- About 120,000 daily bus and train users, 180,000 forecast for 2040.
- The development vision sets "maximum green" as a principle and names a green wedge along Dorgelolaan and the railway.

## 5. Lessons from reference projects

| Reference | What worked | What did not |
|---|---|---|
| Medellín, Corredores Verdes | About 2°C of cooling from 30 corridors, per city data | Maintenance was underfunded |
| Barcelona, Green Axis | Before/after study found better greenery, safety and pedestrian conditions | Likely gentrification |
| Toronto, Bloor Street | Soil cells gave engineered rooting space | Tree deaths from several causes, de-icing salt most notable |
| Milwaukee street trees | Monitored from 1979 to 2005 | Narrower planting strips meant more deaths |
| Eindhoven, Vestdijk | Grey car street turned into a greener boulevard | No published figures found |

Takeaway: corridors succeed above ground and fail below it, and benefits are rarely evaluated. A tool that checks soil and reports metrics addresses both.

## 6. KPIs and targets

| KPI | Calculation | Target |
|---|---|---|
| Canopy cover | Merged crown area ÷ corridor area | 30% (3-30-300 rule) |
| Shaded route | Centreline length under crowns ÷ total length | 60% (team proposal) |
| Longest gap | Longest uncovered stretch of centreline | 25 m or less (team proposal) |
| Trees in natural soil | Trees whose cell meets their soil need ÷ all trees | 60% (team proposal) |

Also reported: tree count, species count, largest species share (10-20-30 rule), engineered soil volume as a cost proxy.

Dropped: wind protection (needs airflow simulation), water modelling.

## 7. Algorithm

1. **Inputs:** 3D mass, surfaces, greenery, soil, climate proxy, plant database.
2. **Grid:** 2 m cells inside the corridor.
3. **Mask:** remove buildings, carriageway and an assumed utilities strip.
4. **Score:** `score = w_heat × heat + w_soil × soil + w_gap × gap`, each value scaled 0 to 1.
5. **Place:** take the best free cell, pick the largest tree class the soil allows, block neighbours within spacing, update distances, repeat until the tree budget is used.
6. **Species:** filter by size class and soil moisture, then balance toward the 10-20-30 mix.
7. **Evaluate:** KPIs at any year from 2026 to 2060, crowns growing linearly to mature size.
8. **Options:** three weight profiles. A favours heat (most shade), B favours gaps (most connected), C favours good soil (lowest cost).

The generator is a transparent scoring rule. An optional language-model layer could turn a planner's written goal into weights and explain the trade-off; it is not built.

## 8. Data status

**In the Drive (GREENSPINE / INPUTS, IAAC account)**

- `INPROGRESS_merged_plant_database_modified_by_hand.xlsx`
- Four 3D BAG tiles: `9-588-304`, `9-588-308`, `9-592-304`, `9-592-308`
- Cluster passports 1A (with KPI annex), 1B, 2, 9B, 9C
- Ontwikkelvisie Fellenoord (annex and public version), Dutch Mountains preliminary urban plan
- Fellenoord BV annual reports 2024 and 2025, Mooi NL advice, two event reports

Only the file list has been read, not the file contents.

**To fetch**

- Existing trees: https://data.eindhoven.nl/explore/dataset/bomen/
- Other public green: Eindhoven open data, "Openbaar groen"
- Surfaces: OpenStreetMap

**To make**

- Corridor polygon and walking centreline
- Tree class table and soil lookup
- The scored grid (made by the app)

**Missing, with fallbacks**

- Soil: not in the Drive. Fallback: unpaved is good, paved needs engineered soil.
- Heat map: national map has limited download options. Fallback: paved ground far from canopy is hot.
- Utilities, traffic, pedestrian flow: not openly available. Fallback: stated assumptions.

## 9. Team split

| Work package | Owner | Hands over |
|---|---|---|
| A. Data and scoring | AI student | Scored grid by 12:30 |
| B. Placement model | Architect | Tree points per option by 14:00 |
| C. Ground and KPIs | Structural engineer | KPI formulas and tree class table by 12:00 |
| D. UI and pitch | Fourth member, or shared from 15:00 | Pitch draft started early |

Owners were assigned by discipline, not by name. The handover times were set at 11:00 and have slipped; reset them.

## 10. What exists

| Output | Where |
|---|---|
| Fellenoord site facts deck (9 slides) | `Fellenoord_site_facts.pptx`, sent in chat |
| Green Spine site analysis deck (7 slides, Roboto and magenta) | `Green_Spine_site_analysis.pptx`, sent in chat |
| Concept and site analysis doc | https://claude.ai/artifact/95i9cysbhWaVxz4aFJRePU |
| Miro board: brainstorm, team split, methodology, workflow diagram, data plan | https://miro.com/app/board/uXjVEOFK7kA=/ |
| GitHub repo | https://github.com/raniachihaoui1/green-spine |
| App | `app.py`, `backend/`, `data/plants.csv` in this repo |

## 11. The app

Run with:

```
pip install -r requirements.txt
streamlit run app.py
```

- Sidebar: option A, B, C or custom weights; tree budget; year.
- Option cards with the four KPIs, best fit marked.
- 3D map: buildings, corridor, trees growing by year. Green can be planted now; magenta needs engineered soil.
- Targets table, species mix chart, planting schedule with CSV and JSON downloads.

Demo results on the synthetic corridor, 90 trees, year 2040 (not Fellenoord numbers):

| Option | Canopy | Shaded route | Longest gap | Natural soil | Engineered soil |
|---|---|---|---|---|---|
| A Most shade | 20% | 45% | 49 m | 0% | 2,700 m³ |
| B Most connected | 21% | 54% | 30 m | 10% | 2,430 m³ |
| C Lowest cost | 12% | 37% | 69 m | 100% | 0 m³ |

To switch to real data, put these files in `data/`, all in EPSG:28992: `corridor.geojson`, `centreline.geojson`, `buildings.geojson` (property `height`), `road.geojson`, `unpaved.geojson`, `trees_existing.geojson` (property `crown_radius`). Optional: `utilities.geojson`, `wet_zone.geojson`.

## 12. Open issues

- The dashboard passed an automated run but has not been checked visually.
- The 10% species rule is not met (largest share 18%) because each size class has only six or seven species in the starter table. The full plant database should fix it.
- Tree class sizes, growth rates and rooting volumes are placeholders.
- Shade and gap targets are proposals, not sourced standards. The cluster passport 1A KPI annex may hold official targets and has not been read.
- Collaborators have to be invited to the GitHub repo by hand (Settings, Collaborators).
- Claude's GitHub connection cannot see the repo, so pushes are done locally.
- Pitch time is assumed to be 17:00.

## 13. Remaining schedule

| Time | Milestone |
|---|---|
| 13:00–14:00 | Corridor drawn; real layers converted; app running on real data |
| 14:00–15:00 | Tree classes and plant database in; three options checked by hand on one block |
| 15:00–16:00 | Layout polish; before/after image; feature freeze at 16:00 |
| 16:00–17:00 | Pitch rehearsal and backup video |

## 14. Sources

- Ontwikkelvisie & ontwikkelkader Fellenoord: https://commissiemer.nl/projectdocumenten/00007572.pdf
- KCAP station area plan: https://urbandesignlab.in/transformation-of-eindhoven-station-eindhoven-kcap
- ProRail MIRT summary 2023: https://www.prorail.nl/siteassets/homepage/mini-projectwebsites/ovknoop-ehv/ov-knoop-eindhoven-multimodale-knoop-eindhoven-samenvatting-mirt-voorbereidingsfase--11-maart-2023.pdf
- AM, Lightyards: https://www.am.nl/en/?p=174527
- Eindhoven News, social housing: https://eindhovennews.com/?p=69371
- Medellín green corridors: https://www.jagonews24.com/en/feature/news/70676
- Barcelona Green Axis evaluation: https://www.citedrive.com/en/discovery/quasi-experimental-evaluation-of-public-space-quality-of-barcelonas-superblocks-green-axis/
- Toronto soil cells: https://www.thenatureofcities.com/?p=27868
- Milwaukee street tree survival: https://dx.doi.org/10.1016/j.ufug.2013.05.006
- UNaLab, Vestdijk: https://unalab.eu/en/vestdijk
- Eindhoven open data, Bomen: https://data.overheid.nl/dataset/22477-bomen
- 3D BAG: https://3dbag.nl/en/download

## 14:10 Existing trees from the RIVM Bomenkaart 2022

- Clipped the national RIVM Bomenkaart 2022 (10 m cells, % cover by trees > 2.5 m, AHN4 + infrared photo 2022) to the Fellenoord scope (Kennedyplein to the Dommel) plus 250 m margin: 2.2 × 1.7 km, 220 × 170 cells, mean tree cover 12%. Tool: `tools/clip_bomenkaart.py` (needs rasterio; rerun with `--corridor data/corridor.geojson` once the corridor is drawn).
- New files in `data/`: `bomenkaart_2022_fellenoord.npz` (read by the app, numpy only), `bomenkaart_2022_fellenoord.tif` (QGIS), `scope_fellenoord.geojson`.
- The app now uses this map as the existing canopy, also on the demo corridor. Each 10 m cell is one disc with the same covered area. No species or heights.
- New KPI **Existing canopy kept (behoud)**: canopy area inside the corridor that stays ÷ canopy today. Target ≥ 90% (team proposal). Losses split into "lost to the plan" (under a building or carriageway) and "cleared for planting".
- Sidebar: "Keep existing trees" toggle and "Protect canopy from (% cover)" slider (default 30%). Protected cells block new trunks within crown radius + 3 m.
- Demo corridor result: 661 m² canopy inside the corridor today (2.9% cover); 73% kept with protection on, 48–73% with it off. Not Fellenoord numbers until the real corridor is in.
