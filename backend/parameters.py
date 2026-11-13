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

# STARTING VALUES: crown radius at maturity (m), spacing (m), soil need (0-1),
# crown growth (m of radius per year), rooting volume (m3) if soil is engineered.
TREE_CLASSES = {
    "large":  dict(r_mature=7.0, spacing=12.0, soil_need=0.80, growth=0.25, soil_m3=30),
    "medium": dict(r_mature=4.5, spacing=8.0,  soil_need=0.50, growth=0.20, soil_m3=15),
    "small":  dict(r_mature=2.5, spacing=5.0,  soil_need=0.30, growth=0.12, soil_m3=6),
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

# 10-20-30 diversity rule (Santamour): max share per species, genus, family
MAX_SPECIES, MAX_GENUS, MAX_FAMILY = 0.10, 0.20, 0.30

# =============================================================================
# 4. Planting strategies (weights: heat, soil, gap)
# =============================================================================
PROFILES = {
    "A  Most shade":     dict(heat=0.60, soil=0.10, gap=0.30),
    "B  Most connected": dict(heat=0.20, soil=0.15, gap=0.65),
    "C  Lowest cost":    dict(heat=0.20, soil=0.60, gap=0.20),
}
CUSTOM_WEIGHTS_DEFAULT = dict(heat=0.40, soil=0.30, gap=0.30)

# =============================================================================
# 5. Building canopies (wind shelter for pedestrians at tall buildings)
# =============================================================================
# A canopy is a horizontal shelter fixed to the facade at pedestrian level. It breaks the
# downdraught that tall buildings push down to the street. It also shelters the ground
# below from rain and sun, and its top can carry small greenery (extensive green roof).
CANOPY_ENABLED = True
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
PERGOLA_ENABLED = True
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
# 8. KPI targets
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
