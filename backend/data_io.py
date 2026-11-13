"""Load real layers from data/ when present (GeoJSON in EPSG:28992), else demo data.

Expected files:
  corridor.geojson        one Polygon
  centreline.geojson      one LineString
  buildings.geojson       Polygons, property 'height' (m)
  road.geojson            Polygons of carriageway (blocked)
  unpaved.geojson         Polygons of open ground
  trees_existing.geojson  Points, property 'crown_radius' (m, optional)
Optional: utilities.geojson, wet_zone.geojson
"""
import json
from pathlib import Path
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union
from .demo_data import make_demo

EMPTY = Polygon()


def _features(path: Path):
    if not path.exists():
        return []
    gj = json.loads(path.read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    return [(shape(f["geometry"]), f.get("properties") or {}) for f in feats if f.get("geometry")]


def _union(path: Path):
    geoms = [g for g, _ in _features(path)]
    return unary_union(geoms) if geoms else EMPTY


def load_layers(data_dir="data") -> dict:
    d = Path(data_dir)
    if not (d / "corridor.geojson").exists() or not (d / "centreline.geojson").exists():
        return make_demo()
    corridor = _union(d / "corridor.geojson")
    centreline = _features(d / "centreline.geojson")[0][0]
    return dict(
        corridor=corridor,
        centreline=centreline,
        buildings=[(g, float(p.get("height", 15))) for g, p in _features(d / "buildings.geojson")],
        road=_union(d / "road.geojson"),
        utilities=_union(d / "utilities.geojson"),
        unpaved=_union(d / "unpaved.geojson"),
        existing_trees=[(g, float(p.get("crown_radius", 3.0))) for g, p in _features(d / "trees_existing.geojson")],
        wet_zone=_union(d / "wet_zone.geojson"),
        demo=False,
    )
