# Green Spine: data and metrics

**Purpose:** respect the urban framework, test additional greening and measure
its incremental benefit. Results are design-screening estimates, not permission
to plant or proof of policy compliance.

Sources: [data inventory](../data/SOURCES.md).
Tunable assumptions: [parameters](../backend/parameters.py).
Scenario contract: [masterplan import](MASTERPLAN_IMPORT.md).

## Evidence and missing information

| Input | Evidence | Use and limitation |
|---|---|---|
| Buildings | 3D BAG extruded masses | Footprint exclusions and geometric shadows, not architectural detail |
| Roads and open ground | OSM-derived polygons | Current surface proxies, not the narrower future boulevard |
| Corridor and route | Draft OSM-derived 909 m alignment | Common assessment boundary; route is not a verified walking network |
| Existing canopy | RIVM Bomenkaart 2022 fractional 10 m cells | Exact cell/corridor intersection weighting for area; indicative discs for shadows/display |
| Soil | Six BRO boreholes, five usable from the surface | Nearest usable profile informs compatibility, not local rooting capacity |
| Trees | Team-curated native tree table and raw plant database | Class, moisture, soil match and diversity; incomplete salt/drought/flood/light traits |
| Climbers | Team's soil-compatible Vine records | Rechecked at the nearest usable borehole and per occupied light band |
| Masterplan GIS | Not yet supplied | No masterplan result until the complete package is supplied |
| Groundwater, utilities, basements, flow, flood/PET rasters | Missing or incomplete | Unknown, not a pass; optional known exclusion layers are honoured |

## Placement

1. Build the 2 m grid inside the corridor. Exclude buildings, roads, known
   utilities, actual water and underground structures.
2. Apply facade/road setbacks, mapped canopy protection and optional shelter exclusions.
3. Rank by sunny-paving exposure, preference for open ground and distance from canopy.
   Strategies describe priorities, not guaranteed optimal shade, connectivity or cost.
4. Select species **and class together** before committing spacing. Compatibility
   below the threshold and incompatible moisture never fall back to an unsuitable
   species. Strict diversity may result in fewer trees than requested.
5. Screen usable depth and available rooting volume. Defaults: small 15 m3 / 1.0 m;
   medium 30 m3 / 1.2 m; large 50 m3 / 1.2 m. These are design assumptions.
   Open ground is preferred; paving always requires conditional engineering.
6. Reserve the candidate rooting polygon so another tree cannot count it again.
   Reservation is conservative: the whole screened zone, not only the minimum
   volume. Rooting may be disconnected or compacted in reality; all proposals
   still need investigation. Facade rootbeds cannot reuse reserved tree-root space.
7. Export a decision for excluded/rejected/unselected cells and a schedule of
   selected trees. No automatic "plant now" approval.

Changing scoring weights no longer changes soil feasibility rules.
Rooting volume is not inferred from a dimensionless paving score.

## Metrics

| Output | Calculation | Interpretation |
|---|---|---|
| Canopy footprint | Retained fractional RIVM coverage + union of committed/new crowns on its uncovered fraction, divided by fixed corridor area | Assumes unknown sub-cell canopy distribution is uniform; baseline and scenarios use the same method |
| Documented canopy loss | Fractional canopy within supplied removal polygons | Not inferred from current road/building overlap; no removal phasing |
| Route shade at 15:00 | Building, crown and elevated shelter shadows on 2 m route samples | Clear-sky solar geometry on 21 June; not air temperature or PET |
| Crown proximity / longest gap | Route within `SHADE_REACH_M` of projected crowns / longest remainder | Not actual sunshine or functional ecological connectivity |
| On mapped open ground | New trunk locations on the open-ground layer / new trees | Not "natural soil", verified depth or absence of a basement |
| Rooting volume | Class-required and screened available volumes; engineered subset separately | Unpriced engineering resource, not a cost estimate |
| Survival-adjusted canopy/shade | Reference + incremental potential benefit times crown-area-weighted survival | Approximation, not an exact probabilistic union or mortality simulation; does not reduce existing canopy |
| Unsealed ground | Geometric union of mapped open ground and proposed pits, clipped to eligible public ground | No duplicate pits, roads, water or buildings |
| Water | Local rainfall = interception + indicative infiltration + roof retention + runoff | No imported runoff or verified tank/storage volume; see [water](../backend/metrics/WATER.md) |
| Facades | Suitable selected wall length times year-dependent climber height | Separate vertical area; rooting, structures, openings and irrigation conditional |
| Wind | Nearby crowns / shelter along tall facades | Proximity proxy only, not a wind-comfort simulation |

Growth is exponential from planting radius to class mature radius. Ten-year
survival assumptions are interpolated from planting and then held constant.
Tree classes and growth must be calibrated with the team.

No baseline nature-score delta is shown: the existing canopy has no species or
resilience inventory. The legacy ecosystem module remains an exploratory
new-planting index; its empty-planting score is `None`, not a fabricated zero.

## Policy and trade-offs

The 30% canopy ambition is a **team corridor target inspired by 3-30-300**, not
proof of the entire neighbourhood rule.

Cluster 1A's annex specifies development greenery (8 m2/dwelling and 10% of
non-residential GFA), 60 mm storage per m2 public paving, accessible cool places
(200 m2, 50% vegetation shade, within 300 m walking) and 50% unsealed public space.
The water text requires 20 mm in designed facilities. These are not applied
indiscriminately to this corridor or other clusters.

The dashboard lists these checks as **not assessed** until the policy boundary,
programme, weighted-green method, accessible spaces, walking network and verified
storage inventory exist. Rain retained in a model storm is not proof of storage
capacity. Built shelter does not establish a vegetation-shaded cool place.

Strategies are compared on explicit canopy, shade, gaps and engineered volume.
There is no invented "best" score or lowest-cost claim without costs.

## Presentation and validation

The dashboard and HTML show indicative massing and canopy symbols. Blender exports
use metre coordinates, matching crown-height bounds, local solar geometry,
procedural vegetation and physically based materials. Materials, leaf detail and
the studio backdrop are illustrative, not additional site evidence.

`python -m unittest discover -s tests -v` checks imports, strict feasibility,
empty cases, canopy accounting, water conservation, shade factors, growth and
render geometry. Streamlit AppTest and headless startup validate the dashboard.
