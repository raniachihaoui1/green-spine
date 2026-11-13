# Data sources

Written by `scripts/fetch_data.py` on 2026-11-13. All layers are in EPSG:28992.

| File | Source | Licence | Content |
|---|---|---|---|
| `centreline.geojson` | DRAFT: mid-line of the Fellenoord / Dorgelolaan carriageways from OpenStreetMap | OpenStreetMap, ODbL | 909 m |
| `corridor.geojson` | Centreline widened by 30 m each side, minus the Dommel | derived | 5.45 ha |
| `buildings.geojson` | 3D BAG, layer lod12 (https://3dbag.nl) | CC BY 4.0 | 3248 building parts; `height` = roof (70th percentile) minus ground level |
| `trees_existing.geojson` | Eindhoven open data, "bomen" (https://data.eindhoven.nl/explore/dataset/bomen/) | see dataset page | 196 trees within 40 m of the corridor, 98 inside it |
| `road.geojson` | OpenStreetMap roads and cycleways (https://www.openstreetmap.org) | ODbL | 27271 m² |
| `unpaved.geojson` | OpenStreetMap grass, parks, gardens, scrub, woodland | ODbL | 13402 m² |
| `wet_zone.geojson` | Ground within 30 m of the Dommel (OpenStreetMap) | ODbL | 1015 m² |

## Assumptions in these layers

These are starting values set in `scripts/fetch_data.py`, not survey data.

- The corridor is the centreline widened by 30 m each side.
- Roads are OpenStreetMap centre lines widened by road type (3.2 m per lane where lanes are tagged). They show today's layout, not the planned narrower boulevard.
- Footpaths are not blocked; they count as paved ground that needs engineered soil.
- Tree crown radius is 0.3 x the middle of the municipal height class (for example "6-9" m gives 2.2 m), limited to 1.5 to 8 m. The dataset has no crown size.
- Building height is one value per building part (flat extrusion).
- No utilities layer: underground cables and pipes are not included.
- Soil is not measured: OpenStreetMap green areas count as open ground, everything else as paved.
