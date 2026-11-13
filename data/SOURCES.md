# Data

All coordinates are RD New (EPSG:28992). Folder paths are set in `backend/parameters.py` (`RAW_DIR`, `PROCESSED_DIR`).

- **`raw/`** holds files as they were received or downloaded. Never edit them; write derived files to `processed/`.
- **`processed/`** holds what the app reads. Every file there is made by a script, named below.

## raw/

| File | What it is | Source | Licence |
|---|---|---|---|
| `3dbag/9-588-304.city.json.gz` and three more tiles | 3D BAG building tiles (CityJSON) | https://3dbag.nl/en/download | CC BY 4.0 |
| `soil/fellenoord_soil_type.csv` | 6 BRO boreholes: position, soil layers (depth, texture, made ground) | BRO (Basisregistratie Ondergrond), downloaded from DINOloket, https://www.dinoloket.nl | Public |
| `plants/plant_database.csv` | Team plant database, 1,477 plants (75 trees) | Team, merged from GBIF, POWO, PlantNet, PFAF, ForwardPlant | Team |
| `sketches/*.jpeg` | Whiteboard and sketch photos from 13 November | Team | Team |

Not stored as raw files: the national RIVM Bomenkaart 2022 (too large; [Atlas Natuurlijk Kapitaal](http://www.atlasnatuurlijkkapitaal.nl)), and the OpenStreetMap, 3D BAG API and Eindhoven tree downloads, which `scripts/fetch_data.py` fetches directly.

## processed/

| File | Content | Made by |
|---|---|---|
| `corridor.geojson`, `centreline.geojson` | Draft corridor (30 m either side) and walking line, 909 m, 5.45 ha | `scripts/fetch_data.py` (OpenStreetMap) |
| `buildings.geojson` | 3,248 building parts, `height` = roof (70th percentile) minus ground | `scripts/fetch_data.py` (3D BAG API) |
| `road.geojson`, `unpaved.geojson`, `wet_zone.geojson` | Carriageway, green areas, ground within 30 m of the Dommel | `scripts/fetch_data.py` (OpenStreetMap) |
| `trees_existing.geojson` | 196 municipal trees. Kept for reference; the app uses the RIVM canopy instead | `scripts/fetch_data.py` (Eindhoven open data) |
| `bomenkaart_2022_fellenoord.npz` / `.tif`, `scope_fellenoord.geojson` | RIVM tree cover (% per 10 m cell), clipped to the scope plus 250 m | `scripts/clip_bomenkaart.py` |
| `fellenoord_compatible_plants.csv` | 680 plants whose soil needs match at least one borehole | `python -m backend.soil` |
| `plants.csv` | The 20 native species the app plants | Team, by hand |
| `plants_candidates.csv` | The 75 database trees, for the team to mark as native | `scripts/build_plants.py` |
| `fetch_report.md` | Counts and assumptions of the last download (written on the next run) | `scripts/fetch_data.py` |

## Assumptions in the downloaded layers (from the 13 November run)

These are starting values in `scripts/fetch_data.py`, not survey data.

- The corridor is the centreline widened by 30 m each side, and the line is a draft along the carriageway mid-line.
- Roads are OpenStreetMap centre lines widened by road type (3.2 m per lane where lanes are tagged). They show today's layout, not the planned narrower boulevard.
- Footpaths are not blocked; they count as paved ground that needs engineered soil.
- Building height is one value per building part (flat extrusion).
- No utilities layer: underground cables and pipes are not included.
- Soil plantability is paved versus unpaved. The boreholes inform species choice only.
