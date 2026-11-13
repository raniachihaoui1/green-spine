# Green Spine: project and scope

AEC NL Hackathon 2026, Eindhoven. Challenge theme: Green Spine (native planting, urban forest and biodiversity).

This is the single reference for the team: what we are building, what is in and out of scope, what exists, and what is left. It is based on the project log of 13 November 2026, 12:57 ([PROJECT_LOG.md](PROJECT_LOG.md)) and checked against the repo at 13:00 the same day. Where the repo has moved on since the log, this document follows the repo.

## 1. The project in one paragraph

Draw a line through the asphalt, and the tool plants a native urban forest along it, then shows canopy cover and habitat connection today, in 2040 and in 2060.

Fellenoord is paved and about to be rebuilt. Street-tree schemes often fail below ground, and their results are rarely measured. Our tool generates and ranks planting options for one corridor from Fellenoord to the Dommel, placing trees where the ground and climate support them, and reports the results as live KPIs.

**Pitch line:** we did not place trees where they look good, we placed them where the ground can carry them.

## 2. Scope

### In scope

| Area | What we deliver |
|---|---|
| Site | One corridor, from Fellenoord to the Dommel, in Eindhoven |
| Method | A transparent scoring rule on a 2 m grid: heat, soil and gap, each scaled 0 to 1 |
| Options | Three planting strategies: A most shade, B most connected, C lowest cost, plus custom weights |
| Trees | Three size classes (large, medium, small), species assigned from the plant database, native species |
| KPIs | Canopy cover, shaded route, longest gap, trees in natural soil |
| Also reported | Tree count, species count, largest species share (10-20-30 rule), engineered soil volume as a cost proxy |
| Time | Results at any year from 2026 to 2060, shown for 2026, 2040 and 2060 |
| Product | A Streamlit dashboard with a 3D map, option cards, targets table, species mix and a downloadable planting schedule |
| Pitch | Pitch, a before/after image and a backup video |

### Out of scope

| Item | Why |
|---|---|
| Wind protection | Needs airflow simulation |
| Water modelling | Dropped to fit the day |
| Language-model layer (turning a planner's written goal into weights and explaining the trade-off) | Optional idea, not built |
| More than one corridor, or the whole station area | Scope was cut when the event was shortened to one day |
| Measured soil, heat, utilities, traffic and pedestrian-flow data | Not available in time; replaced by the stated fallbacks below |

### Assumptions we are working with

| Missing data | Fallback used |
|---|---|
| Soil | Unpaved ground is good; paved ground needs engineered soil |
| Heat map | Paved ground far from canopy is hot |
| Utilities | An assumed utilities strip is removed from the plantable area |
| Traffic, pedestrian flow | Stated assumptions |
| Crown growth | Linear from planting size to mature size |
| Pitch time | Assumed to be 17:00 |

### Done means

1. The app runs on real Fellenoord data, not the demo corridor.
2. Tree class values and targets are confirmed by the engineer.
3. The three options are checked by hand on one block.
4. The pitch, the before/after image and the backup video are ready.

## 3. Status

| Item | Status |
|---|---|
| Concept, KPIs, algorithm | Agreed |
| Team split and timeline | On the Miro board |
| Backend and dashboard | First version runs on demo data |
| Environment | `gsenv` on Python 3.13, with setup scripts and pinned versions (see [README](../README.md)) |
| Git | App and environment setup are committed and pushed to `main`; branch `test_1` is at the same commit. The log said "not committed"; that is out of date |
| Real data in the app | Not yet: `data/` holds only `plants.csv` |
| Corridor outline and centreline | Not drawn yet. **This blocks the real-data run** |
| Tree class numbers | Placeholders in `backend/config.py`, to be confirmed |
| Pitch and before/after image | Not started |

### Next three actions

1. Architect draws `corridor.geojson` and `centreline.geojson` (EPSG:28992).
2. Convert the four 3D BAG tiles and the Eindhoven tree dataset into the files `backend/data_io.py` expects.
3. Engineer replaces the placeholder tree class values and confirms the targets.

## 4. KPIs and targets

| KPI | Calculation | Target | Basis |
|---|---|---|---|
| Canopy cover | Merged crown area ÷ corridor area | 30% or more | 3-30-300 rule |
| Shaded route | Centreline length under crowns ÷ total length | 60% or more | Team proposal |
| Longest gap | Longest uncovered stretch of centreline | 25 m or less | Team proposal |
| Trees in natural soil | Trees whose cell meets their soil need ÷ all trees | 60% or more | Team proposal |

Only the canopy target comes from a published rule. The cluster passport 1A KPI annex may hold official targets and has not been read.

## 5. Algorithm

1. **Inputs:** 3D mass, surfaces, greenery, soil, climate proxy, plant database.
2. **Grid:** 2 m cells inside the corridor.
3. **Mask:** remove buildings, carriageway and the assumed utilities strip.
4. **Score:** `score = w_heat × heat + w_soil × soil + w_gap × gap`. Cells scoring below 0.15 are not planted.
5. **Place:** take the best free cell, pick the largest tree class the soil allows, block neighbours within spacing, update distances, repeat until the tree budget is used.
6. **Species:** filter by size class and soil moisture, then balance toward the 10-20-30 mix (at most 10% one species, 20% one genus, 30% one family).
7. **Evaluate:** KPIs at any year from 2026 to 2060.
8. **Options:** three weight profiles.

| Option | Heat | Soil | Gap |
|---|---|---|---|
| A Most shade | 0.60 | 0.10 | 0.30 |
| B Most connected | 0.20 | 0.15 | 0.65 |
| C Lowest cost | 0.20 | 0.60 | 0.20 |

Tree classes in `backend/config.py`. **All are starting values, not sourced standards:**

| Class | Mature crown radius | Spacing | Soil need (0 to 1) | Crown growth per year | Rooting volume if engineered |
|---|---|---|---|---|---|
| Large | 7.0 m | 12 m | 0.80 | 0.25 m | 30 m³ |
| Medium | 4.5 m | 8 m | 0.50 | 0.20 m | 15 m³ |
| Small | 2.5 m | 5 m | 0.30 | 0.12 m | 6 m³ |

Other starting values: crown radius at planting 1.0 m; plantability 1.0 for open ground and 0.35 under paving.

## 6. The app

Set up and run (full steps in the [README](../README.md)):

```powershell
.\setup_gsenv.ps1
.\gsenv\Scripts\Activate.ps1
streamlit run app.py
```

- Sidebar: option A, B, C or custom weights; tree budget; year.
- Option cards with the four KPIs, best fit marked.
- 3D map: buildings, corridor, trees growing by year. Green can be planted now; magenta needs engineered soil.
- Targets table, species mix chart, planting schedule with CSV and JSON downloads.

Demo results from the log: synthetic corridor, 90 trees, year 2040. **These are not Fellenoord numbers.**

| Option | Canopy | Shaded route | Longest gap | Natural soil | Engineered soil |
|---|---|---|---|---|---|
| A Most shade | 20% | 45% | 49 m | 0% | 2,700 m³ |
| B Most connected | 21% | 54% | 30 m | 10% | 2,430 m³ |
| C Lowest cost | 12% | 37% | 69 m | 100% | 0 m³ |

### Switching to real data

Put these files in `data/`, all in EPSG:28992. Without `corridor.geojson` and `centreline.geojson` the app falls back to the demo corridor.

| File | Content | Required |
|---|---|---|
| `corridor.geojson` | One polygon | Yes |
| `centreline.geojson` | One line | Yes |
| `buildings.geojson` | Polygons, property `height` in metres | Yes |
| `road.geojson` | Carriageway polygons (blocked) | Yes |
| `unpaved.geojson` | Open-ground polygons | Yes |
| `trees_existing.geojson` | Points, property `crown_radius` in metres | Yes |
| `utilities.geojson`, `wet_zone.geojson` | Polygons | Optional |

## 7. Data

**In the Drive (GREENSPINE / INPUTS, IAAC account).** Only the file list has been read, not the file contents.

- `INPROGRESS_merged_plant_database_modified_by_hand.xlsx`
- Four 3D BAG tiles: `9-588-304`, `9-588-308`, `9-592-304`, `9-592-308`
- Cluster passports 1A (with KPI annex), 1B, 2, 9B, 9C
- Ontwikkelvisie Fellenoord (annex and public version), Dutch Mountains preliminary urban plan
- Fellenoord BV annual reports 2024 and 2025, Mooi NL advice, two event reports

**To fetch**

- Existing trees: https://data.eindhoven.nl/explore/dataset/bomen/
- Other public green: Eindhoven open data, "Openbaar groen"
- Surfaces: OpenStreetMap

**To make**

- Corridor polygon and walking centreline
- Tree class table and soil lookup
- The scored grid (made by the app)

**In the repo now:** `data/plants.csv`, a starter table of 20 species.

## 8. Team and schedule

| Work package | Owner | Hands over |
|---|---|---|
| A. Data and scoring | AI student | Scored grid |
| B. Placement model | Architect | Tree points per option |
| C. Ground and KPIs | Structural engineer | KPI formulas and tree class table |
| D. UI and pitch | Fourth member, or shared from 15:00 | Pitch draft, started early |

Owners were assigned by discipline, not by name. The original handover times (12:00, 12:30, 14:00) were set at 11:00 and have slipped; the team needs to reset them.

| Time | Milestone |
|---|---|
| 13:00–14:00 | Corridor drawn; real layers converted; app running on real data |
| 14:00–15:00 | Tree classes and plant database in; three options checked by hand on one block |
| 15:00–16:00 | Layout polish; before/after image; feature freeze at 16:00 |
| 16:00–17:00 | Pitch rehearsal and backup video |

## 9. Open issues

- The dashboard passed an automated run but has not been checked visually.
- The 10% species rule is not met (largest share 18%) because each size class has only six or seven species in the starter table. The full plant database should fix it.
- Tree class sizes, growth rates and rooting volumes are placeholders.
- Shade, gap and natural-soil targets are proposals, not sourced standards.
- Collaborators have to be invited to the GitHub repo by hand (Settings, Collaborators).
- Claude's GitHub connection cannot see the repo, so pushes are done locally.

## 10. Background

### Site facts

Figures come from public search extracts gathered on 13 November 2026. **Check the originals before quoting them to the jury.**

- Fellenoord lies north of Eindhoven Centraal and is the core of Internationale Knoop XL (55 ha station area).
- 6,000 to 7,000 homes are planned where a few hundred people live today; 30% targeted for social rent.
- The KCAP plan downgrades the Fellenoord road from urban motorway to city boulevard, cutting traffic space to a 40 m minimum. That freed width is the planting area.
- The Dommel valley is designated as an ecological and recreational link; no new buildings on its banks.
- About 120,000 daily bus and train users, 180,000 forecast for 2040.
- The development vision sets "maximum green" as a principle and names a green wedge along Dorgelolaan and the railway.

### Lessons from reference projects

| Reference | What worked | What did not |
|---|---|---|
| Medellín, Corredores Verdes | About 2°C of cooling from 30 corridors, per city data | Maintenance was underfunded |
| Barcelona, Green Axis | Before/after study found better greenery, safety and pedestrian conditions | Likely gentrification |
| Toronto, Bloor Street | Soil cells gave engineered rooting space | Tree deaths from several causes, de-icing salt most notable |
| Milwaukee street trees | Monitored from 1979 to 2005 | Narrower planting strips meant more deaths |
| Eindhoven, Vestdijk | Grey car street turned into a greener boulevard | No published figures found |

Takeaway: corridors succeed above ground and fail below it, and benefits are rarely evaluated. A tool that checks soil and reports metrics addresses both.

### How we got here

| Time | Step |
|---|---|
| 06:50 | Team method and brainstorm plan; five seed ideas |
| 06:54 | Event shortened to one day; plan compressed, scope cut |
| 08:10 | Fellenoord site facts researched; first slide deck built |
| 08:48 | Theme chosen: Green Spine. Concept and metrics defined |
| 09:02 | Concept saved as a Claude Doc; site analysis and slide version added |
| 09:28 | GitHub repo created by hand |
| 09:30 | Roles discussed for architect, structural engineer and AI student |
| 09:49 | Use of soil and greenery data worked out |
| 10:50 | Why/what/how, reference projects, KPIs, data sources, algorithm and six-hour scope defined |
| 11:03 | Workflow diagram, methodology and team split added to the Miro board |
| 11:42 | Data preparation method |
| 12:04 | Realistic plan, data availability, parameters, metrics, option generation |
| 12:09 | Drive folder inventoried |
| 12:14 | Backend and Streamlit dashboard built and tested on demo data |
| 12:40 | `gsenv` environment, setup scripts and README instructions added and pushed |

## 11. Where everything is

| Output | Where |
|---|---|
| App | `app.py`, `backend/`, `data/plants.csv` in this repo |
| GitHub repo | https://github.com/raniachihaoui1/green-spine |
| Miro board: brainstorm, team split, methodology, workflow diagram, data plan | https://miro.com/app/board/uXjVEOFK7kA=/ |
| Concept and site analysis doc | https://claude.ai/artifact/95i9cysbhWaVxz4aFJRePU |
| Fellenoord site facts deck (9 slides) | `Fellenoord_site_facts.pptx`, sent in chat |
| Green Spine site analysis deck (7 slides) | `Green_Spine_site_analysis.pptx`, sent in chat |
| Project log | [PROJECT_LOG.md](PROJECT_LOG.md) |

## 12. Sources

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
