# Supplying the masterplan reference

Green Spine does not redesign the urban framework. It proposes additional planting
inside supplied buildings, roads and the common assessment corridor.

Without `data/processed/masterplan/scenario.json`, the masterplan view and masterplan
deltas are **unavailable**. Existing-condition exploration still works. Generated
building canopies and pergolas are optional proposals, off by default.

## Reference package

Keep received GIS/CAD files unchanged in `data/raw/masterplan/`. Export derived
GeoJSONs into `data/processed/masterplan/` and record their source in
[SOURCES.md](../data/SOURCES.md). CAD/PDF conversion and georeferencing must happen
before import. The app does not infer geometry from a PDF.

Every layer is a GeoJSON **FeatureCollection in EPSG:28992 metres**, not longitude
and latitude. Required layers may be explicitly empty, except the route. An empty
file asserts that the supplied reference contains no such features; do not use it
to conceal an unresolved part of the plan.

| Required layer key | Geometry | Properties / meaning |
|---|---|---|
| `buildings` | Polygon / MultiPolygon | Full reference massing, including retained buildings; positive `height` in m |
| `road` | Polygon / MultiPolygon | Full reference carriageway |
| `centreline` | One LineString | Continuous assessment route, entirely inside the existing corridor |
| `unpaved` | Polygon / MultiPolygon | Full reference open ground; not a rooting-depth certification |
| `water` | Polygon / MultiPolygon | Actual water surface; not the indicative wet-ground buffer |
| `canopy_removals` | Polygon / MultiPolygon | Explicitly documented canopy-removal areas, never inferred from today's roads |
| `committed_trees` | Point | `species`, `size_class` (`small`, `medium`, `large`), integer `planting_year`; optional Boolean `engineered` |

Optional polygon layers: `utilities`, `underground`, `soil_zones`, `canopies`,
`pergola`. Missing optional layers are **unknown**, not surveyed clear.
Supplied underground structures are conservatively excluded: planting on decks
needs a separate engineered design, which this version cannot certify.

Each `soil_zones` feature needs `usable_depth_m` (non-negative, after groundwater
and other limitations) and `source`. Overlapping depth zones are rejected where
used. Outside these zones, the labelled assumed depth is used. Root volume remains
conditional on compaction, access, groundwater and utility investigations.

`canopies` and `pergola` mean **committed** shelter footprints, not automatically
generated ones. Heights and interception factors currently use the explicit model
parameters; unusual structures need those assumptions reviewed.

Example manifest structure (replace all filenames, dates and sources with your
actual evidence; this is documentation, not a supplied reference):

```json
{
  "name": "Fellenoord reference",
  "date": "2026-11-13",
  "source": "Document title, revision and drawing identifiers",
  "status": "documented",
  "crs": "EPSG:28992",
  "layers": {
    "buildings": {"file": "buildings.geojson", "source": "Drawing / GIS layer"},
    "road": {"file": "road.geojson", "source": "Drawing / GIS layer"},
    "centreline": {"file": "centreline.geojson", "source": "Route drawing"},
    "unpaved": {"file": "unpaved.geojson", "source": "Landscape drawing"},
    "water": {"file": "water.geojson", "source": "Water drawing"},
    "canopy_removals": {"file": "canopy_removals.geojson", "source": "Removal schedule"},
    "committed_trees": {"file": "committed_trees.geojson", "source": "Planting schedule"}
  }
}
```

Use `status: "indicative"` for a reconstructed or assumed reference.
`documented` means traceable to supplied documents, **not municipally approved or
verified compliant**. Files must be inside the reference directory. Invalid
geometry, invalid heights, wrong coordinate ranges and incomplete packages raise
visible errors instead of falling back to existing conditions.

## Comparisons

- Existing = today's source layers and RIVM 2022 canopy.
- Masterplan = replacement reference geometry, documented removals and committed planting.
- Green Spine = reference plus additional trees, climbers and optional shelters.
- Development effect = masterplan minus existing.
- Added Green Spine value = proposal minus masterplan.
- Overall change = proposal minus existing.

The corridor boundary is fixed. Public-ground denominators can change with
building footprints. If the route changes, the dashboard suppresses cross-route
shade deltas; a verified common walking network is needed for a stronger comparison.
Existing canopy is held constant with time; committed and additional trees grow
from their planting year. Future removal phasing is not modelled.

Ground, canopy, facade and shelter areas remain distinct. No municipal
quality-weighted green credits, drainage capacity or construction approval are
invented. Layer/parameter changes invalidate the cached results on the next rerun.
