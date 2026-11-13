"""Source-labelled reference scenarios. No masterplan file means no masterplan result."""
import json
import math
from pathlib import Path

import pandas as pd
import shapely
from shapely.geometry import Polygon

from . import parameters as P
from .data_io import _features
from .metrics import covered_ground, heat_stress, water_retention, wind_index
from .model import canopy_geometry, kpis, route_base

EMPTY = Polygon()
REQUIRED_LAYERS = {
    "buildings": ("Polygon", "MultiPolygon"),
    "road": ("Polygon", "MultiPolygon"),
    "centreline": ("LineString",),
    "unpaved": ("Polygon", "MultiPolygon"),
    "water": ("Polygon", "MultiPolygon"),
    "canopy_removals": ("Polygon", "MultiPolygon"),
    "committed_trees": ("Point",),
}
OPTIONAL_LAYERS = {
    "utilities": ("Polygon", "MultiPolygon"),
    "underground": ("Polygon", "MultiPolygon"),
    "soil_zones": ("Polygon", "MultiPolygon"),
    "canopies": ("Polygon", "MultiPolygon"),
    "pergola": ("Polygon", "MultiPolygon"),
}
CHART_METRICS = {
    "canopy_pct": ("Canopy footprint", "%"),
    "shade_3pm_pct": ("Route shade at 15:00", "%"),
    "rain_kept_pct": ("Indicative storm retention", "%"),
    "unsealed_pct": ("Unsealed public ground", "%"),
}


def input_fingerprint():
    """Include data, soil sources and parameter/code changes in Streamlit cache keys."""
    roots = (Path(P.PROCESSED_DIR), Path(P.RAW_DIR) / "soil", Path(P.RAW_DIR) / "plants", Path("backend"))
    files = sorted({p for root in roots for p in root.rglob("*")
                    if p.is_file() and p.suffix.lower() in {".csv", ".geojson", ".json", ".npz", ".py"}})
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)


def _read_layer(directory, name, spec, kinds):
    if not isinstance(spec, dict) or not all(isinstance(spec.get(k), str) and spec[k].strip()
                                           for k in ("file", "source")):
        raise ValueError(f"Masterplan {name}: provide a file and a non-empty source.")
    path = (directory / spec["file"]).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError(f"Masterplan {name}: file must exist inside the masterplan directory.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ValueError(f"Masterplan {name}: expected a GeoJSON FeatureCollection.")
    if any(not f.get("geometry") for f in data["features"]):
        raise ValueError(f"Masterplan {name}: null geometry is not allowed.")
    features = _features(path)
    for geom, props in features:
        if geom.is_empty or not geom.is_valid or geom.geom_type not in kinds:
            raise ValueError(f"Masterplan {name}: invalid or unexpected {geom.geom_type} geometry.")
        x0, y0, x1, y1 = geom.bounds
        west, south, east, north = P.RD_BOUNDS
        if not (west <= x0 <= x1 <= east and south <= y0 <= y1 <= north):
            raise ValueError(f"Masterplan {name}: coordinates are not plausible EPSG:28992 metres.")
        if name == "buildings" and not _positive(props.get("height")):
            raise ValueError("Masterplan buildings: every footprint needs a positive height in metres.")
        if name == "committed_trees":
            if props.get("size_class") not in P.TREE_CLASSES or not isinstance(props.get("species"), str):
                raise ValueError("Committed trees need species and a known size_class.")
            if not isinstance(props.get("planting_year"), int) or isinstance(props["planting_year"], bool):
                raise ValueError("Committed trees need an integer planting_year.")
    return features


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def load_masterplan(existing, directory=P.MASTERPLAN_DIR):
    """Complete replacement reference, fixed corridor boundary; explicit empty layers are valid."""
    directory = Path(directory)
    manifest = directory / "scenario.json"
    if not manifest.exists():
        return None
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    if meta.get("crs") != "EPSG:28992":
        raise ValueError("Masterplan scenario.json must declare crs = EPSG:28992.")
    for key in ("name", "source", "date"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"Masterplan scenario.json needs {key}.")
    if meta.get("status") not in ("documented", "indicative"):
        raise ValueError("Masterplan status must be documented or indicative; neither certifies compliance.")
    specs = meta.get("layers")
    if not isinstance(specs, dict) or not REQUIRED_LAYERS.keys() <= specs.keys():
        raise ValueError("Masterplan needs layers: " + ", ".join(REQUIRED_LAYERS))
    unknown = specs.keys() - (REQUIRED_LAYERS.keys() | OPTIONAL_LAYERS.keys())
    if unknown:
        raise ValueError("Unknown masterplan layers: " + ", ".join(sorted(unknown)))
    data = {name: _read_layer(directory, name, specs[name], kinds)
            for name, kinds in (REQUIRED_LAYERS | OPTIONAL_LAYERS).items() if name in specs}
    if len(data["centreline"]) != 1:
        raise ValueError("Masterplan needs exactly one continuous assessment route.")
    line = data["centreline"][0][0]
    if not existing["corridor"].covers(line):
        raise ValueError("Masterplan route must stay inside the fixed assessment corridor.")
    if not line.length:
        raise ValueError("Masterplan route must have positive length.")
    L = {k: v for k, v in existing.items() if not k.startswith("_") and k != "route"}
    for key in ("road", "unpaved", "water", "canopy_removals", "utilities", "underground", "canopies", "pergola"):
        L[key] = shapely.union_all([g for g, _ in data.get(key, [])])
    L["soil_zones"] = data.get("soil_zones", [])
    L["centreline"] = line
    L["buildings"] = [(g, float(p["height"])) for g, p in data["buildings"]]
    L["bld_union"] = shapely.union_all([g for g, _ in L["buildings"]])
    L["committed"] = pd.DataFrame([
        dict(x=g.x, y=g.y, size_class=p["size_class"], species=p["species"],
             planting_year=p["planting_year"], engineered=bool(p.get("engineered", False)))
        for g, p in data["committed_trees"]])
    L["reference"] = meta
    L["demo"] = False
    L["data_status"] = [
        {"layer": name, "status": "supplied" if name in specs else "unknown",
         "source": specs[name]["source"] if name in specs else "No scenario-specific evidence"}
        for name in REQUIRED_LAYERS | OPTIONAL_LAYERS
    ]
    L["route"] = route_base(L)
    return L


def situation_metrics(L, trees, year, canopies=None, pergola=None, facades_m2=0.0):
    canopies = L.get("canopies", EMPTY) if canopies is None else canopies
    pergola = L.get("pergola", EMPTY) if pergola is None else pergola
    K = kpis(trees, L, year)
    crowns = canopy_geometry(trees, L, year)
    cover = covered_ground(L, canopies, pergola, crowns)
    heat = heat_stress(trees, L, year, canopies, pergola)
    wind = wind_index(trees, L, year, canopies, crowns)
    water = water_retention(trees, L, year, canopies=canopies, pergola=pergola)
    return dict(**K, shade_3pm_pct=heat["shaded_pct"], rain_kept_pct=water["kept_pct"],
                wind_pct=wind["with_canopies_pct"], unsealed_pct=water["unsealed_pct"],
                rain_kept_m3=water["kept_m3"], runoff_m3=water["runoff_m3"],
                covered_m2=cover["covered_m2"], green_on_structures_m2=cover["green_on_structures_m2"],
                green_facade_m2=facades_m2, heat=heat, water=water, cover=cover)


def comparison_table(existing, masterplan, proposal):
    """Never produce a masterplan delta without a masterplan."""
    rows = []
    for key, (label, unit) in CHART_METRICS.items():
        a, b, c = existing[key], masterplan[key] if masterplan else None, proposal[key]
        rows.append({"Metric": label, "Unit": unit, "Existing": a, "Masterplan": b, "Proposal": c,
                     "Development effect": None if b is None else b - a,
                     "Added Green Spine value": None if b is None else c - b,
                     "Overall change": c - a})
    return pd.DataFrame(rows)
