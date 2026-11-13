"""Match plant soil preferences to the Fellenoord soil profiles (BRO boreholes).

Written by the team (was plant_fellenoord_compatibility.py in the repo root). Run from the
repo root to rebuild the processed list:

    python -m backend.soil

Reads  data/raw/soil/fellenoord_soil_type.csv and data/raw/plants/plant_database.csv
Writes data/processed/fellenoord_compatible_plants.csv
"""

import csv
import math
import re
from collections import defaultdict
from pathlib import Path

SOIL_COLUMNS = {
    "borehole": "ns3:broId",
    "upper": "ns4:upperBoundary",
    "lower": "ns4:lowerBoundary",
    "anthropogenic": "ns4:anthropogenic",
    "constituent": "ns4:tertiaryConstituent",
    "groundtype": "groundtype",
}
PLANT_TEXTURE_COLUMNS = {
    "coarse": "Adapted to Coarse Textured Soils",
    "fine": "Adapted to Fine Textured Soils",
    "medium": "Adapted to Medium Textured Soils",
}
PLANT_SOIL_COLUMNS = {
    "coarse": "Soil: Light (L)",
    "medium": "Soil: Medium (M)",
    "fine": "Soil: Heavy (H)",
}
_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOIL_CSV = _ROOT / "data" / "raw" / "soil" / "fellenoord_soil_type.csv"
DEFAULT_PLANT_CSV = _ROOT / "data" / "raw" / "plants" / "plant_database.csv"
DEFAULT_OUTPUT_CSV = _ROOT / "data" / "processed" / "fellenoord_compatible_plants.csv"


def _read_csv(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))
    except UnicodeDecodeError:
        with Path(path).open(
            "r", encoding="cp1252", errors="replace", newline=""
        ) as source:
            return list(csv.DictReader(source))


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _truth(value):
    value = str(value or "").strip().casefold()
    if value in {"true", "yes", "ja", "1"}:
        return True
    if value in {"false", "no", "nee", "0"}:
        return False
    return None


def _soil_texture(constituent, groundtype):
    """Map BRO soil labels to the plant database's texture classes."""
    constituent = str(constituent or "").strip().casefold()
    groundtype = str(groundtype or "").strip().casefold()
    if "klei" in constituent or "veen" in constituent:
        return "fine"
    if "silt" in constituent:
        return "medium"
    if "zand" in constituent:
        if "middelgrof" in groundtype or "grof" in groundtype:
            return "coarse"
        return "medium" if "fijn" in groundtype else "coarse"
    return None


def load_soil_profiles(path=DEFAULT_SOIL_CSV):
    """Load sorted soil layers grouped by BRO borehole ID."""
    profiles = defaultdict(list)
    for row in _read_csv(path):
        borehole = (row.get(SOIL_COLUMNS["borehole"]) or "").strip()
        upper = _number(row.get(SOIL_COLUMNS["upper"]))
        lower = _number(row.get(SOIL_COLUMNS["lower"]))
        if not borehole or upper is None or lower is None or lower <= upper:
            continue
        profiles[borehole].append(
            {
                "upper": upper,
                "lower": lower,
                "texture": _soil_texture(
                    row.get(SOIL_COLUMNS["constituent"]),
                    row.get(SOIL_COLUMNS["groundtype"]),
                ),
                "anthropogenic": _truth(row.get(SOIL_COLUMNS["anthropogenic"])),
            }
        )
    for layers in profiles.values():
        layers.sort(key=lambda layer: (layer["upper"], layer["lower"]))
    return dict(profiles)


def _supported_depth(layers):
    depth = 0.0
    for layer in layers:
        if layer["upper"] > depth + 0.1:
            break
        depth = max(depth, layer["lower"])
    return depth


def _required_root_depth(plant, default_root_depth):
    value = (plant.get("Root Depth, Minimum (meters)") or "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    depth = _number(match.group()) if match else None
    return depth if depth is not None and depth > 0 else default_root_depth


def _plant_supports_texture(plant, texture):
    if texture is None:
        return None
    value = _truth(plant.get(PLANT_TEXTURE_COLUMNS[texture]))
    return (
        value if value is not None else _truth(plant.get(PLANT_SOIL_COLUMNS[texture]))
    )


def _score_plant(plant, layers, default_root_depth):
    root_depth = _required_root_depth(plant, default_root_depth)
    if _supported_depth(layers) + 1e-9 < root_depth:
        return None

    known_depth = compatible_depth = anthropogenic_depth = 0.0
    for layer in layers:
        thickness = max(0.0, min(layer["lower"], root_depth) - layer["upper"])
        if thickness == 0:
            continue
        if layer["anthropogenic"] is True:
            anthropogenic_depth += thickness
        supports = _plant_supports_texture(plant, layer["texture"])
        if supports is not None:
            known_depth += thickness
            if supports:
                compatible_depth += thickness
    if known_depth == 0:
        return None

    texture_score = compatible_depth / known_depth
    anthropogenic_fraction = anthropogenic_depth / root_depth
    return max(0.0, texture_score - 0.1 * anthropogenic_fraction)


def select_compatible_plants(
    borehole_id=None,
    soil_csv=DEFAULT_SOIL_CSV,
    plant_csv=DEFAULT_PLANT_CSV,
    min_compatibility=0.6,
    default_root_depth=1.0,
):
    """Return ranked plants compatible with a borehole or any profile.

    Minimum root depth is treated as required profile depth; missing values use
    ``default_root_depth``. Texture fit is weighted by layer thickness. Because
    plant data has no anthropogenic-soil tolerance field, its profile share is
    a small score penalty rather than a hard exclusion. Returned records add
    ``compatibility_score`` and ``compatible_boreholes``. Use a threshold of
    1.0 to require no known texture mismatches.
    """
    if not 0 <= min_compatibility <= 1:
        raise ValueError("min_compatibility must be between 0 and 1")
    if default_root_depth <= 0:
        raise ValueError("default_root_depth must be greater than zero")

    profiles = load_soil_profiles(soil_csv)
    if borehole_id is not None:
        borehole_id = str(borehole_id)
        if borehole_id not in profiles:
            raise KeyError(f"Unknown borehole ID: {borehole_id}")
        profiles = {borehole_id: profiles[borehole_id]}

    selected = []
    for plant in _read_csv(plant_csv):
        if not (plant.get("species") or "").strip():
            continue
        scores = {
            profile_id: _score_plant(plant, layers, default_root_depth)
            for profile_id, layers in profiles.items()
        }
        matches = [
            profile_id
            for profile_id, score in scores.items()
            if score is not None and score >= min_compatibility
        ]
        if matches:
            result = dict(plant)
            result["compatibility_score"] = round(
                max(scores[key] for key in matches), 3
            )
            result["compatible_boreholes"] = matches
            selected.append(result)
    return sorted(
        selected, key=lambda plant: (-plant["compatibility_score"], plant["species"])
    )


def save_compatible_plants(
    selected,
    plant_csv=DEFAULT_PLANT_CSV,
    output_csv=DEFAULT_OUTPUT_CSV,
):
    """Write matching source plant rows, without compatibility metadata."""
    selected_species = {plant["species"] for plant in selected}
    source_rows = _read_csv(plant_csv)
    if not source_rows:
        return 0

    fieldnames = list(source_rows[0])
    rows_to_write = []
    written_species = set()
    for row in source_rows:
        species = (row.get("species") or "").strip()
        if species in selected_species and species not in written_species:
            rows_to_write.append(row)
            written_species.add(species)

    with Path(output_csv).open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_to_write)
    return len(rows_to_write)


if __name__ == "__main__":
    selected = select_compatible_plants()
    count = save_compatible_plants(selected)
    print(f"Saved {count} compatible plants to {DEFAULT_OUTPUT_CSV.name}")


# ---------------------------------------------------------------------------
# Helpers for the app (added 13 Nov 2026): borehole positions and a
# species x borehole score table, so each 2 m cell can use its nearest borehole.
# ---------------------------------------------------------------------------
def borehole_positions(path=DEFAULT_SOIL_CSV):
    """{borehole id: (x, y)} in RD (EPSG:28992), from the BRO 'pos' column."""
    out = {}
    for row in _read_csv(path):
        bid = (row.get(SOIL_COLUMNS["borehole"]) or "").strip()
        pos = (row.get("ns2:pos") or "").split()
        if bid and len(pos) == 2 and bid not in out:
            out[bid] = (float(pos[0]), float(pos[1]))
    return out


def compatibility_table(species, soil_csv=DEFAULT_SOIL_CSV, plant_csv=DEFAULT_PLANT_CSV,
                        default_root_depth=1.0):
    """Soil-fit score (0-1, or None when the profile cannot be judged) for each
    species in `species` at each borehole: {borehole: {species: score}}."""
    wanted = set(species)
    profiles = load_soil_profiles(soil_csv)
    table = {b: {} for b in profiles}
    for plant in _read_csv(plant_csv):
        name = (plant.get("species") or "").strip()
        if name not in wanted:
            continue
        for b, layers in profiles.items():
            if name not in table[b]:
                table[b][name] = _score_plant(plant, layers, default_root_depth)
    return table
