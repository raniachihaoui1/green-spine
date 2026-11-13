"""All tunable numbers in one place. Values marked STARTING VALUE are placeholders
for the team to confirm; they are not sourced standards."""

CELL = 2.0          # grid cell size in metres
BASE_YEAR = 2026
YEARS = (2026, 2040, 2060)
PLANTING_RADIUS = 1.0   # crown radius at planting, metres (STARTING VALUE)
GAP_CAP = 50.0          # distance to canopy beyond which the gap score is 1
SOIL_UNPAVED = 1.0      # plantability of open ground
SOIL_PAVED = 0.35       # plantability under paving (STARTING VALUE)
MIN_SCORE = 0.15        # below this nothing is planted

# STARTING VALUES: crown radius at maturity (m), spacing (m), soil need (0-1),
# crown growth (m of radius per year), rooting volume (m3) if soil is engineered.
TREE_CLASSES = {
    "large":  dict(r_mature=7.0, spacing=12.0, soil_need=0.80, growth=0.25, soil_m3=30),
    "medium": dict(r_mature=4.5, spacing=8.0,  soil_need=0.50, growth=0.20, soil_m3=15),
    "small":  dict(r_mature=2.5, spacing=5.0,  soil_need=0.30, growth=0.12, soil_m3=6),
}

# Targets. Canopy 30% follows the 3-30-300 rule; the others are team proposals.
TARGETS = {
    "canopy_pct":       (">=", 30.0),
    "shade_pct":        (">=", 60.0),
    "longest_gap_m":    ("<=", 25.0),
    "natural_soil_pct": (">=", 60.0),
}

# Weight profiles: (heat, soil, gap)
PROFILES = {
    "A  Most shade":     dict(heat=0.60, soil=0.10, gap=0.30),
    "B  Most connected": dict(heat=0.20, soil=0.15, gap=0.65),
    "C  Lowest cost":    dict(heat=0.20, soil=0.60, gap=0.20),
}

# 10-20-30 diversity rule
MAX_SPECIES, MAX_GENUS, MAX_FAMILY = 0.10, 0.20, 0.30

# Sun study (backend/sun.py): clear-sky direct sun on one design day.
DESIGN_DAY = (6, 21)        # month, day: summer solstice, the hottest sun geometry
LAT, LON = 51.4437, 5.4800  # Fellenoord, Eindhoven
SUN_STEP_H = 0.5            # time step in hours
MIN_SUN_ALTITUDE = 10.0     # degrees; lower sun is ignored (very long shadows, little heat)
CROWN_BASE, CROWN_TOP = 0.6, 1.8   # crown spans these multiples of its radius in height (STARTING VALUE)
ROUTE_STEP = 2.0            # metres between sample points on the walking route
