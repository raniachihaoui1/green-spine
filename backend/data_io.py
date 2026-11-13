"""Load real layers from data/ when present (GeoJSON in EPSG:28992), else demo data.

Expected files:
  corridor.geojson        one Polygon
  centreline.geojson      one LineString
  buildings.geojson       Polygons, property 'height' (m)
  road.geojson            Polygons of carriageway (blocked)
  unpaved.geojson         Polygons of open ground
  trees_existing.geojson  Points, property 'crown_radius' (m, optional)
Optional: utilities.geojson, wet_zone.geojson

Existing canopy: if data/bomenkaart_2022_fellenoord.npz exists (tools/clip_bomenkaart.py), the RIVM
Bomenkaart 2022 replaces trees_existing.geojson / the demo trees as the existing canopy, so nothing is
counted twice.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union
from .demo_data import make_demo
from . import bomenkaart

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
    L = _load_geometry(data_dir)
    R = bomenkaart.load_raster(data_dir)
    if R is not None:
        L["existing"] = bomenkaart.existing_canopy(R, L["corridor"], L["buildings"], L["road"])
        L["canopy_context"] = bomenkaart.raster_cells(R)
        L["baseline_rivm_pct"] = bomenkaart.baseline_cover_pct(R, L["corridor"])
        L["canopy_source"] = "RIVM Bomenkaart 2022 (10 m)"
    else:
        L["existing"] = _points_to_cells(L)
        L["canopy_context"] = L["existing"][["x", "y", "cover"]]
        L["baseline_rivm_pct"] = None
        L["canopy_source"] = "demo trees" if L["demo"] else "trees_existing.geojson"
    return L


def _points_to_cells(L) -> pd.DataFrame:
    """Fallback: individual tree points in the same table format as the raster cells."""
    t = L.get("existing_trees") or []
    df = pd.DataFrame(dict(x=[p.x for p, _ in t], y=[p.y for p, _ in t], r=[float(r) for _, r in t]))
    df["cover"] = np.pi * df.r ** 2
    pts = shapely.points(df.x.values, df.y.values)
    df["in_corridor"] = shapely.contains(L["corridor"], pts) if len(df) else []
    blk = unary_union([g for g, _ in L["buildings"]] + [L["road"]])
    df["plan_loss"] = shapely.contains(blk, pts) if len(df) else []
    return df


def _load_geometry(data_dir="data") -> dict:
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
