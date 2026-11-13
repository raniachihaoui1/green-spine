"""pydeck map layers for the dashboard. All geometry comes in RD (EPSG:28992) and is
converted to WGS84 here, for display only."""
import base64
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pydeck as pdk
import shapely
from pyproj import Transformer
from . import parameters as C
from .model import crown_radius, existing_cleared

_to_wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

# Map layer switches shown in the Inputs panel: key -> (label, on by default)
LAYERS = {
    "buildings": ("Buildings (3D BAG)", True),
    "corridor": ("Corridor and walking line", True),
    "canopy": ("Existing canopy (RIVM 2022)", True),
    "green": ("Green areas", True),
    "water": ("Water and wet ground", True),
    "roads": ("Roads", True),
    "sun": ("Sun hours, 21 June", False),
    "boreholes": ("Soil boreholes (BRO)", True),
    "structures": ("Building canopies and pergola", True),
    "facades": ("Green facades", True),
    "understorey": ("Shrubs and low vegetation (indicative)", True),
}

BARK = [101, 76, 52, 255]
KEPT_GREEN = [96, 125, 90, 235]       # existing canopy that stays
CLEARED_RED = [200, 40, 40, 240]      # existing canopy cleared for a new tree
NEW_GREEN = [46, 160, 67, 235]        # new tree, plant now
NEW_MAGENTA = [233, 30, 140, 235]     # new tree, needs engineered soil


# ---------------- 3D vegetation models ----------------
@lru_cache(maxsize=None)
def model_info():
    """Reference sizes from models.json, or None when the models have not been built."""
    f = Path(C.VEG_MODEL_DIR) / "models.json"
    return json.loads(f.read_text(encoding="utf-8")) if C.USE_3D_MODELS and f.exists() else None


@lru_cache(maxsize=None)
def _model_uri(name, part):
    """The .glb as a data URI: the browser gets it inline, so no static file serving is needed."""
    f = Path(C.VEG_MODEL_DIR) / f"{name}_{part}.glb"
    return "data:model/gltf-binary;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else None


def _model_layers(df, name, foliage_color, trunk_color=BARK):
    """ScenegraphLayers (foliage + trunk) for rows with lon, lat, scale, label. foliage_color: list or column name.
    The models are Y-up glTF; orientation [0, 0, 90] stands them upright in deck.gl."""
    out = []
    for part, color in (("foliage", foliage_color), ("trunk", trunk_color)):
        uri = _model_uri(name, part)
        if uri is None or not len(df):
            continue
        out.append(pdk.Layer("ScenegraphLayer", df[["lon", "lat", "scale", "label"] + ([color] if isinstance(color, str) else [])],
                             scenegraph=pdk.types.String(uri), get_position=["lon", "lat"], get_orientation=[0, 0, 90],
                             get_scale="scale", get_color=color, size_scale=1, _lighting="pbr", pickable=True))
    return out


def _crown_r(name):
    return model_info()[name]["crown_d_m"] / 2


def understorey_points(L):
    """Indicative shrubs and low vegetation on open ground in the corridor (computed once, kept in L)."""
    if "_understorey" not in L:
        green = L["unpaved"].intersection(L["corridor"]) if not L["unpaved"].is_empty else None
        rows = []
        if green is not None and not green.is_empty:
            rng = np.random.default_rng(3)
            for kind, step in (("low_vegetation", C.UNDERSTOREY_VEG_SPACING_M), ("medium_bush", C.UNDERSTOREY_BUSH_SPACING_M)):
                x0, y0, x1, y1 = green.bounds
                X, Y = np.meshgrid(np.arange(x0, x1, step), np.arange(y0, y1, step))
                x = X.ravel() + rng.uniform(-0.3, 0.3, X.size) * step
                y = Y.ravel() + rng.uniform(-0.3, 0.3, Y.size) * step
                inside = shapely.contains(green, shapely.points(x, y))
                rows.append(pd.DataFrame(dict(x=x[inside], y=y[inside], kind=kind,
                                              rot=rng.uniform(0, 360, int(inside.sum())))))
        L["_understorey"] = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["x", "y", "kind", "rot"])
    return L["_understorey"]


def ll(x, y):
    lon, lat = _to_wgs.transform(np.asarray(x, float), np.asarray(y, float))
    return lon, lat


def ring(poly, z=None):
    lon, lat = ll(*poly.exterior.xy)
    if z is None:
        return [[float(a), float(b)] for a, b in zip(lon, lat)]
    return [[float(a), float(b), float(z)] for a, b in zip(lon, lat)]


def polys(geom):
    if geom is None or geom.is_empty:
        return []
    return [g for g in (geom.geoms if hasattr(geom, "geoms") else [geom]) if g.geom_type == "Polygon"]


def _fill(geom, color, label):
    return pdk.Layer("PolygonLayer", [{"p": ring(p), "label": label} for p in polys(geom)], get_polygon="p",
                     get_fill_color=color, stroked=False, pickable=True)


def build_layers(L, grid, trees, year, show, canopies=None, pergola=None, boreholes=None, facades=None):
    """List of pydeck layers for the switched-on map layers."""
    layers = []
    if show.get("corridor"):
        layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p), "label": "Corridor"} for p in polys(L["corridor"])],
                                get_polygon="p", get_fill_color=[235, 235, 235, 140],
                                get_line_color=[120, 120, 120], line_width_min_pixels=1, pickable=False))
    if show.get("green") and not L["unpaved"].is_empty:
        layers.append(_fill(L["unpaved"], [190, 225, 180, 200], "Green area (open ground)"))
    if show.get("water") and not L["wet_zone"].is_empty:
        layers.append(_fill(L["wet_zone"], [150, 200, 235, 170], "Wet ground near the Dommel"))
    if show.get("roads") and not L["road"].is_empty:
        layers.append(_fill(L["road"], [90, 90, 90, 200], "Road"))
    if show.get("sun"):
        s = grid[["x", "y", "sun_hours"]].copy()
        s["lon"], s["lat"] = ll(s.x, s.y)
        f = (s.sun_hours / max(s.sun_hours.max(), 1e-9)).values[:, None]
        lo, hi = np.array([255, 247, 214]), np.array([217, 72, 1])       # pale yellow to deep orange
        s["color"] = (lo + f * (hi - lo)).astype(int).tolist()
        s["label"] = s.sun_hours.map(lambda v: f"{v:.1f} h of direct sun on 21 June")
        layers.append(pdk.Layer("ScatterplotLayer", s[["lon", "lat", "color", "label"]], get_position=["lon", "lat"],
                                get_radius=1.15, get_fill_color="color", stroked=False, pickable=True))
    if show.get("corridor"):
        lon, lat = ll(*L["centreline"].xy)
        layers.append(pdk.Layer("PathLayer", [{"path": [[float(a), float(b)] for a, b in zip(lon, lat)], "label": "Walking line"}],
                                get_path="path", get_color=[233, 30, 140], width_min_pixels=2, pickable=True))
    if show.get("buildings"):
        layers.append(pdk.Layer("PolygonLayer", [{"p": ring(b), "h": h, "label": f"Building, {h:.0f} m"} for b, h in L["buildings"]],
                                get_polygon="p", extruded=True, get_elevation="h",
                                get_fill_color=[205, 205, 205, 255], pickable=True))
    if show.get("structures"):
        if canopies is not None and not canopies.is_empty:
            layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p, C.CANOPY_HEIGHT_M), "label": "Building canopy"} for p in polys(canopies)],
                                    get_polygon="p", extruded=True, get_elevation=C.CANOPY_THICKNESS_M,
                                    get_fill_color=[30, 120, 200, 220], pickable=True))
        if pergola is not None and not pergola.is_empty:
            layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p, C.PERGOLA_HEIGHT_M), "label": "Road pergola"} for p in polys(pergola)],
                                    get_polygon="p", extruded=True, get_elevation=0.3,
                                    get_fill_color=[240, 160, 40, 200], pickable=True))
    ex = L["existing"]
    models = model_info()
    if show.get("canopy") and len(ex):
        e = ex.copy()
        e["lon"], e["lat"] = ll(e.x, e.y)
        e["cleared"] = existing_cleared(trees, L)
        e["label"] = [f"Existing canopy, {c:.0f}% tree cover (RIVM 10 m cell)" + (" · cleared for a new tree" if cl else "")
                      for c, cl in zip(e.cover, e.cleared)]
        if models:
            e["color"] = [CLEARED_RED if cl else KEPT_GREEN for cl in e.cleared]
            k = 1 / _crown_r(C.EXISTING_TREE_MODEL)
            e["scale"] = [[r * k] * 3 for r in e.r]
            layers += _model_layers(e, C.EXISTING_TREE_MODEL, "color")
        else:
            e["color"] = [CLEARED_RED if cl else [120, 140, 120, int(90 + 1.4 * min(c, 100))] for c, cl in zip(e.cover, e.cleared)]
            layers.append(pdk.Layer("ScatterplotLayer", e, get_position=["lon", "lat"], get_radius="r",
                                    get_fill_color="color", stroked=False, pickable=True))
    if show.get("understorey") and models:
        u = understorey_points(L)
        if len(u) and len(trees):     # keep the symbols out of the new crowns
            rr = crown_radius(trees.size_class, year) + C.UNDERSTOREY_CLEAR_OF_TRUNK_M
            d = np.hypot(u.x.values[:, None] - trees.x.values[None, :], u.y.values[:, None] - trees.y.values[None, :])
            u = u[~(d < rr[None, :]).any(axis=1)]
        if len(u):
            u = u.copy()
            u["lon"], u["lat"] = ll(u.x, u.y)
            for kind, color, label in (("low_vegetation", [140, 175, 85, 255], "Low vegetation (indicative, on open ground)"),
                                       ("medium_bush", [70, 125, 60, 255], "Medium bush (indicative, on open ground)")):
                g = u[u.kind == kind].assign(label=label)
                g["scale"] = [[1.0, 1.0, 1.0]] * len(g)
                layers += _model_layers(g, kind, color)
    if show.get("boreholes") and boreholes:
        b = pd.DataFrame([dict(id=k, x=v[0], y=v[1], used=k in used) for used in [boreholes["usable"]]
                          for k, v in boreholes["positions"].items()])
        b["lon"], b["lat"] = ll(b.x, b.y)
        b["color"] = b.used.map(lambda u: [140, 90, 40, 240] if u else [170, 170, 170, 200])
        b["label"] = b.apply(lambda r: f"BRO borehole {r.id}" + ("" if r.used else " (no usable profile from the surface)"), axis=1)
        layers.append(pdk.Layer("ScatterplotLayer", b, get_position=["lon", "lat"], get_radius=5,
                                get_fill_color="color", get_line_color=[255, 255, 255], stroked=True,
                                line_width_min_pixels=1, pickable=True))
    if show.get("facades") and facades is not None and len(facades):
        from .facades import strip
        colors = {"full sun": [70, 150, 50, 235], "part shade": [40, 120, 70, 235], "full shade": [20, 90, 70, 235]}
        rows = [{"p": ring(strip(b), b.band_bottom), "h": float(b.green_h), "color": colors[b.sun_class],
                 "label": f"Green facade: {b.climber}, {b.sun_class} ({b.sun_hours:.0f} h sun on 21 June)"}
                for b in facades.itertuples()]
        layers.append(pdk.Layer("PolygonLayer", rows, get_polygon="p", extruded=True, get_elevation="h",
                                get_fill_color="color", pickable=True))
    if len(trees):
        d = trees.copy()
        d["lon"], d["lat"] = ll(d.x, d.y)
        d["r"] = crown_radius(d.size_class, year)
        d["h"] = d.r * 1.8
        d["color"] = d.engineered.map(lambda e: NEW_MAGENTA if e else NEW_GREEN)
        d["label"] = (d.common_name + " (" + d.size_class + ") · " + d.phase + " · soil fit "
                      + d.soil_fit.map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f}") + " at " + d.borehole.astype(str))
        if models:
            d["model"] = d.size_class.map(C.TREE_MODEL)
            for name, grp in d.groupby("model"):
                grp = grp.copy()
                grp["scale"] = [[r / _crown_r(name)] * 3 for r in grp.r]   # crown matches the grown radius
                layers += _model_layers(grp, name, "color")
        else:
            for _, grp in d.groupby("size_class"):
                layers.append(pdk.Layer("ColumnLayer", grp, get_position=["lon", "lat"], radius=float(grp.r.mean()),
                                        get_elevation="h", elevation_scale=1, get_fill_color="color", pickable=True))
    return layers


def view_state(L):
    c = L["corridor"].centroid
    lon, lat = ll([c.x], [c.y])
    return pdk.ViewState(longitude=float(lon[0]), latitude=float(lat[0]), zoom=16.2, pitch=50, bearing=-20)
