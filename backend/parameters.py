"""Green Spine: every tunable parameter in one place.

This is the single parameter file for the project. Code reads its numbers from
here and nowhere else; the dashboard sliders use these values as defaults.

Labels used in the comments:
  STARTING VALUE  placeholder for the team to confirm, not a sourced standard
  SOURCE          taken from a policy or published rule (named in the comment)

Units: metres, square metres, cubic metres, years, percent (0-100) unless noted.
Coordinates are RD New (EPSG:28992).
"""

# =============================================================================
# 1. General
# =============================================================================
CELL = 2.0              # grid cell size (m)
BASE_YEAR = 2026        # "today" for growth and KPIs
YEARS = (2026, 2040, 2060)  # years shown in reports
YEAR_MAX = 2060         # last year on the year slider
DEFAULT_YEAR = 2040     # year selected when the app opens

# =============================================================================
# 2. Site scoring (2 m grid)
# =============================================================================
GAP_CAP = 50.0          # distance to canopy (m) beyond which the gap score is 1
SOIL_UNPAVED = 1.0      # plantability of open ground (0-1)
SOIL_PAVED = 0.35       # plantability under paving (0-1). STARTING VALUE
MIN_SCORE = 0.15        # cells scoring below this are never planted

# =============================================================================
# 3. Trees: size classes, placement and growth
# =============================================================================
PLANTING_RADIUS = 1.0   # crown radius at planting (m). STARTING VALUE

# STARTING VALUES: radius/spacing/depth (m), growth constant (1/year), minimum
# rootable volume (m3). Not a structural or arboricultural approval.
TREE_CLASSES = {
    "large":  dict(r_mature=7.0, spacing=12.0, root_depth=1.2, growth=0.05, soil_m3=50),
    "medium": dict(r_mature=4.5, spacing=9.0, root_depth=1.2, growth=0.08, soil_m3=30),
    "small":  dict(r_mature=2.5, spacing=6.0, root_depth=1.0, growth=0.12, soil_m3=15),
}

# Tree budget slider
TREE_BUDGET_DEFAULT = 90
TREE_BUDGET_MIN, TREE_BUDGET_MAX, TREE_BUDGET_STEP = 20, 200, 5

# Setbacks: no new trunk closer than this to a building facade or a carriageway edge.
# STARTING VALUES. The dashboard prompt suggests 3 / 5 / 7 m per size class for facades;
# one value is used here until the per-class rule is built.
TREE_SETBACK_BUILDING_M = 5.0
TREE_SETBACK_ROAD_M = 2.0
TREE_AVOID_CANOPIES = True     # no new trunk under a building canopy (crown would clash)

# Existing canopy (RIVM Bomenkaart 2022, 10 m cells, % cover by trees > 2.5 m)
CANOPY_MIN_COVER = 10.0        # ignore cells with less tree cover than this (%). STARTING VALUE
CANOPY_CONTEXT_M = 50.0        # show existing canopy up to this distance outside the corridor (m). STARTING VALUE

# 10-20-30 diversity rule. SOURCE: Santamour, F.S. (1990), Trees for urban planting: diversity, uniformity,
# and common sense. At most 10 % of trees per species, 20 % per genus, 30 % per family.
MAX_SPECIES, MAX_GENUS, MAX_FAMILY = 0.10, 0.20, 0.30
ENFORCE_10_20_30 = True   # True: a tree steps down to a smaller size class rather than break the rule

# =============================================================================
# 4. Planting strategies (weights: heat, soil, gap)
# =============================================================================
PROFILES = {
    "A  Exposed areas": dict(heat=0.60, soil=0.10, gap=0.30),
    "B  Canopy gaps":   dict(heat=0.20, soil=0.15, gap=0.65),
    "C  Open ground":   dict(heat=0.20, soil=0.60, gap=0.20),
}
CUSTOM_WEIGHTS_DEFAULT = dict(heat=0.40, soil=0.30, gap=0.30)

# =============================================================================
# 5. Building canopies (wind shelter for pedestrians at tall buildings)
# =============================================================================
# A canopy is a horizontal shelter fixed to the facade at pedestrian level. It breaks the
# downdraught that tall buildings push down to the street. It also shelters the ground
# below from rain and sun, and its top can carry small greenery (extensive green roof).
CANOPY_ENABLED = False          # additional proposal, never an assumed masterplan commitment
CANOPY_MIN_BUILDING_HEIGHT_M = 30.0   # canopies only on buildings taller than this. STARTING VALUE
CANOPY_WIDTH_M = 3.0                  # depth of the canopy, measured out from the facade. STARTING VALUE
CANOPY_EXTENSION_PCT = 10.0           # extra canopy length beyond the building corners, as % of
                                      # the facade length, split evenly over both ends.
                                      # 0 = canopy stops at the corners. STARTING VALUE
CANOPY_HEIGHT_M = 4.5                 # height of the canopy above street level (3D view). STARTING VALUE
CANOPY_THICKNESS_M = 0.4              # slab thickness (3D view only)
CANOPY_MIN_FACADE_M = 4.0             # facades shorter than this get no canopy (small jogs in footprints)
CANOPY_AVOID_ROAD = True              # cut canopies back where they would overhang the carriageway
CANOPY_GREEN_FRACTION = 0.8           # share of the canopy top planted with small greenery (0-1). STARTING VALUE
CANOPY_SUN_FACTOR = 1.0               # share of sun blocked under the canopy (0-1). 1 = closed roof
CANOPY_RAIN_FACTOR = 1.0              # share of rain kept off the ground under the canopy (0-1)

# =============================================================================
# 6. Road pergola (shelter over the middle of the carriageway)
# =============================================================================
# A strip of pergola along the centre axis of the carriageway, high enough for traffic.
PERGOLA_ENABLED = False         # additional proposal; requires traffic/structural approval
PERGOLA_ROAD_PCT = 30.0               # pergola width as % of the carriageway width, centred on
                                      # the road axis. 0 = no pergola, 100 = whole width. STARTING VALUE
PERGOLA_LENGTH_PCT = 100.0            # share of the road length covered, centred on the middle
                                      # of each road section. STARTING VALUE
PERGOLA_HEIGHT_M = 5.0                # underside height; must stay above the 4.2 m traffic clearance
PERGOLA_GREEN_FRACTION = 0.6          # share of the pergola top with climbers / small greenery (0-1). STARTING VALUE
PERGOLA_SUN_FACTOR = 1.0              # share of sun blocked (0-1). Lower for an open, climber-only pergola
PERGOLA_RAIN_FACTOR = 1.0             # share of rain kept off (0-1). Lower for an open pergola

# =============================================================================
# 7. Covered-ground analysis
# =============================================================================
GREEN_ROOF_RETENTION_L_M2 = 25.0      # rain held by small greenery on canopies/pergola (litres per m2). STARTING VALUE
DESIGN_RAIN_MM = 70.0                 # design storm for the rain proxy (mm in 2 h, Klimaateffectatlas scenario)
WALK_ZONE_HALF_WIDTH_M = 4.0          # walking zone either side of the centreline

# =============================================================================
# 8. Ecosystem score (method: backend/metrics/ECOSYSTEM_SCORE.md)
# =============================================================================
# Weights of the four parts. They are normalised, so only their ratio matters.
ECO_WEIGHTS = dict(habitat=0.25, diversity=0.25, connectivity=0.25, resilience=0.25)
ECO_AGGREGATION = "arithmetic"        # "arithmetic" (weighted mean) or "geometric" (a weak part pulls the total down)

# Sub-weights inside each part (each set sums to 1)
ECO_HABITAT_W = dict(canopy=0.5, layered=0.3, unsealed=0.2)
ECO_DIVERSITY_W = dict(shannon=0.4, native=0.3, wildlife=0.3)
ECO_CONNECTIVITY_W = dict(gap=0.7, dommel=0.3)
ECO_RESILIENCE_W = dict(natural_soil=0.6, survival=0.4)

# Targets used to scale each indicator to 0-1
ECO_CANOPY_TARGET_PCT = 30.0          # SOURCE: 3-30-300 rule
ECO_UNSEALED_TARGET_PCT = 50.0        # SOURCE: cluster passport 1A, >= 50 % unsealed public space
ECO_TREE_PIT_M2 = 9.0                 # unsealed tree pit per tree planted in paving (m2). STARTING VALUE
ECO_GAP_ZERO_M = 100.0                # canopy gap (m) at which the connectivity score reaches 0
ECO_DIVERSITY_RULE_STRICT = False     # True: diversity part = 0 when the 10-20-30 rule is broken;
                                      # False: multiply by 0.5 instead (starter table is too small to pass)
ECO_WILDLIFE_SHARE_DEFAULT = 0.5      # share of species with wildlife value when the plant table has no
                                      # 'wildlife' column. STARTING VALUE, replace with the plant database
SURVIVAL_NATURAL_SOIL = 0.85          # expected survival after 10 years in natural soil. STARTING VALUE (prompt)
SURVIVAL_ENGINEERED_SOIL = 0.70       # expected survival after 10 years in engineered soil. STARTING VALUE

# =============================================================================
# 9. Sun study, heat stress and wind (backend/sun.py, backend/metrics/heat.py, wind.py)
# =============================================================================
DESIGN_DAY = (6, 21)        # month, day: summer solstice, the hottest sun geometry
LAT, LON = 51.4437, 5.4800  # Fellenoord, Eindhoven
SUN_STEP_H = 0.5            # time step in hours
MIN_SUN_ALTITUDE = 10.0     # degrees; lower sun is ignored (very long shadows, little heat)
CROWN_BASE, CROWN_TOP = 0.6, 1.8   # crown spans these multiples of its radius in height. STARTING VALUE
ROUTE_STEP = 2.0            # metres between sample points on the walking route
HEAT_CHECK_HOUR_LOCAL = 15.0   # heat-stress check: shade on the route at this local time (CEST). SOURCE: dashboard prompt KPI 2
UTC_OFFSET_H = 2.0          # CEST in June
WIND_TALL_BUILDING_M = 30.0 # wind index looks at buildings taller than this. STARTING VALUE (same as canopy threshold)
WIND_SHELTER_REACH_M = 10.0 # a facade counts as sheltered with a canopy or tree crown within this distance. STARTING VALUE
WIND_CORRIDOR_REACH_M = 30.0   # only facades within this distance of the corridor count. STARTING VALUE

# =============================================================================
# 10. Existing canopy protection and soil (RIVM Bomenkaart, BRO boreholes)
# =============================================================================
CANOPY_PROTECT_COVER = 30.0     # cells with at least this RIVM tree cover (%) keep their trees. STARTING VALUE (prompt 6.4)
CANOPY_ROOT_BUFFER_M = 3.0      # no new trunk within crown + this distance of protected canopy. STARTING VALUE (prompt 6.4)
SOIL_MIN_COMPATIBILITY = 0.6    # species must reach this soil-fit score at the nearest borehole (0-1). Teammate's script default
SOIL_DEFAULT_ROOT_DEPTH_M = 1.0 # root depth used when the plant database has none. Teammate's script default
SOIL_ASSUMED_USABLE_DEPTH_M = 1.2  # m; STARTING VALUE when no local usable-depth survey exists
SOIL_CONFIDENCE_REACH_M = 100.0    # m; STARTING VALUE: flag distant borehole extrapolation
ALLOW_ENGINEERED_SOIL = True      # STARTING VALUE: allow conditional root-volume provision
SURVIVAL_HORIZON_YEARS = 10        # years; STARTING VALUE: interpolate to the stated survival, then hold

# =============================================================================
# 11. Data folders
# =============================================================================
RAW_DIR = "data/raw"            # as received; never edited
PROCESSED_DIR = "data/processed"  # what the app reads; made by the scripts in scripts/ and backend/soil.py

# =============================================================================
# 12. Green facades (backend/facades.py) and water (backend/metrics/water.py)
# =============================================================================
FACADE_REACH_M = 15.0           # facades within this distance of the corridor count as street facades. STARTING VALUE
FACADE_MIN_LENGTH_M = 4.0       # shorter wall segments are ignored (small jogs)
FACADE_MAX_HEIGHT_M = 12.0      # ground-rooted climbers green up to about four floors. STARTING VALUE
FACADE_BAND_M = 3.0             # facade is checked for sun per band of this height (one floor)
FACADE_GREEN_SHARE_PCT = 50.0   # share of street facade length to green, sunniest walls first. User choice (slider)
CLIMBER_MIN_HEIGHT_M = 2.5      # a climber must reach at least this height to count (from the plant database)
CLIMBER_PREFERRED_HEIGHT_M = 6.0  # climbers reaching two floors are preferred, then species are spread. STARTING VALUE
FACADE_SUN_FULL_H = 6.0         # >= this many sun hours on 21 June: wall needs a full-sun climber
FACADE_SUN_PART_H = 3.0         # >= this: part shade; below: full shade
FACADE_GROWTH_K = 0.12         # 1/year; STARTING VALUE: indicative climber establishment
FACADE_INITIAL_HEIGHT_M = 0.5  # m; STARTING VALUE: planted climber height
FACADE_ROOTBED_DEPTH_M = 1.0   # m out from wall; STARTING VALUE, not confirmed rooting volume
FACADE_STRIP_M = 0.4          # m; STARTING VALUE: display thickness only

CROWN_INTERCEPTION_MM = 1.5     # rain a tree crown holds per storm (mm over its area). STARTING VALUE
INFILTRATION_MM = 50.0          # rain that open ground and tree pits soak up during the design storm (mm). STARTING VALUE

# =============================================================================
# 13. KPI targets
# =============================================================================
# Canopy 30% follows the 3-30-300 rule (SOURCE); the others are team proposals.
TARGETS = {
    "canopy_pct":       (">=", 30.0),
    "shade_pct":        (">=", 60.0),
    "longest_gap_m":    ("<=", 25.0),
    "natural_soil_pct": (">=", 60.0),
}

# Shading: a crown within this distance of the centreline still shades the path (m)
SHADE_REACH_M = 2.0

# =============================================================================
# 14. 3D vegetation models on the map (backend/view.py, scripts/make_vegetation_models.py)
# =============================================================================
# Low-poly symbols, not species. The map scales each model so its crown matches the tree's crown radius.
USE_3D_MODELS = True            # False: draw trees as columns and existing canopy as flat discs (faster)
VEG_MODEL_DIR = "data/processed/vegetation_models"
TREE_MODEL = {"large": "large_tree", "medium": "large_tree", "small": "small_tree"}   # size class -> model
EXISTING_TREE_MODEL = "large_tree"   # RIVM canopy cells; height follows the crown, so it is INDICATIVE
UNDERSTOREY_VEG_SPACING_M = 4.0      # one low-vegetation patch (2 x 2 m) per this spacing on open ground. STARTING VALUE
UNDERSTOREY_BUSH_SPACING_M = 10.0    # one medium bush per this spacing on open ground. STARTING VALUE
UNDERSTOREY_CLEAR_OF_TRUNK_M = 2.0   # no bush or patch drawn within crown radius + this of a tree. Display only

# =============================================================================
# 15. Assessment and export
# =============================================================================
MASTERPLAN_DIR = "data/processed/masterplan"
RD_BOUNDS = (0.0, 250000.0, 300000.0, 650000.0)  # m; broad Dutch RD extent, input-validation guard
POLICY_STORAGE_MM = 60.0       # SOURCE: cluster 1A annex 2.d.3; per m2 public paving, not corridor-wide law
POLICY_DESIGNED_STORAGE_MM = 20.0  # SOURCE: cluster 1A water text
POLICY_UNSEALED_PCT = 50.0     # SOURCE: cluster 1A annex 2.d.5, within that cluster only
POLICY_COOL_AREA_M2 = 200.0    # SOURCE: cluster 1A annex 2.d.4
POLICY_COOL_SHADE_PCT = 50.0   # SOURCE: cluster 1A, vegetation shade, not built shelter
POLICY_COOL_DISTANCE_M = 300.0 # SOURCE: cluster 1A annex 2.d.4, walking-network distance
POLICY_GREEN_DWELLING_M2 = 8.0 # SOURCE: cluster 1A annex 2.d.1; not student-housing policy
POLICY_GREEN_GFA_SHARE = 0.10  # SOURCE: cluster 1A annex 2.d.2, non-residential GFA
MAP_HEIGHT_PX = 620           # px; STARTING VALUE: dashboard presentation
MAP_ZOOM, MAP_PITCH, MAP_BEARING = 16.2, 55, -20  # STARTING VALUES: camera
YEAR_STEP = 2                 # years; STARTING VALUE: reporting interval
RENDER_WIDTH, RENDER_HEIGHT = 2560, 1440  # px; STARTING VALUES: presentation export
RENDER_SAMPLES = 48           # samples/pixel; STARTING VALUE: Cycles denoised render
RENDER_CONTEXT_M = 100.0      # m; STARTING VALUE: building context outside assessment boundary
RENDER_SEED = 7               # STARTING VALUE: deterministic illustrative vegetation
RENDER_STYLE = {              # STARTING VALUES: illustrative material/vegetation settings
    "ground": (0.57, 0.56, 0.51, 1.0), "road": (0.095, 0.105, 0.11, 1.0),
    "green": (0.19, 0.28, 0.09, 1.0), "building": (0.70, 0.69, 0.64, 1.0),
    "leaf": (0.065, 0.20, 0.025, 1.0), "bark": (0.16, 0.085, 0.035, 1.0),
    "water": (0.09, 0.25, 0.28, 1.0), "structure": (0.36, 0.38, 0.31, 1.0),
    "backdrop": (0.85, 0.87, 0.85, 1.0), "backdrop_span_ratio": 3.0,
    "leaf_count": 2600, "leaf_size_radius_ratio": 0.045, "branch_count": 18,
    "trunk_radius_ratio": 0.035, "cylinder_sides": 8, "seed": RENDER_SEED,
    "aerial_distance_ratio": 0.85, "aerial_height_ratio": 0.60,
    "camera_margin_ratio": 1.22, "sun_energy": 3.0, "sky_strength": 0.35,
    "sun_angle_rad": 0.0093, "surface_offset_m": 0.025, "stamp_font_px": 18,
    "roughness": 0.78, "noise_scale": 8.0, "bump_strength": 0.15,
    "bump_distance_m": 0.035,
}

