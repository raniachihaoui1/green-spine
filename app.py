"""Green Spine dashboard. Run with:  streamlit run app.py"""
import json
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
from pyproj import Transformer

from backend import config as C
from backend.data_io import load_layers
from backend.model import build_grid, run_option, kpis, targets_met, crown_radius

st.set_page_config(page_title="Green Spine", layout="wide")
_to_wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

KPI_LABELS = {
    "canopy_pct": ("Canopy cover", "%"),
    "shade_pct": ("Shaded route", "%"),
    "longest_gap_m": ("Longest gap", " m"),
    "natural_soil_pct": ("Trees in natural soil", "%"),
}


def ll(x, y):
    lon, lat = _to_wgs.transform(np.asarray(x), np.asarray(y))
    return lon, lat


def ring(poly):
    lon, lat = ll(*poly.exterior.xy)
    return [[float(a), float(b)] for a, b in zip(lon, lat)]


def polys(geom):
    if geom.is_empty:
        return []
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


@st.cache_data(show_spinner=False)
def load():
    L = load_layers("data")
    return L, build_grid(L), pd.read_csv("data/plants.csv")


@st.cache_data(show_spinner="Placing trees")
def option(heat, soil, gap, budget):
    L, grid, plants = load()
    return run_option(L, grid, plants, dict(heat=heat, soil=soil, gap=gap), budget)


L, grid, plants = load()

# ---------------- sidebar ----------------
st.sidebar.title("Green Spine")
st.sidebar.caption("Fellenoord to the Dommel, Eindhoven")
names = list(C.PROFILES) + ["Custom weights"]
choice = st.sidebar.radio("Option", names, index=0)
budget = st.sidebar.slider("Tree budget", 20, 200, 90, 5)
year = st.sidebar.select_slider("Year", options=list(range(C.BASE_YEAR, 2061, 2)), value=2040)
st.sidebar.markdown("**Custom weights**")
cw = dict(
    heat=st.sidebar.slider("Shade (heat)", 0.0, 1.0, 0.4, 0.05, disabled=choice != "Custom weights"),
    soil=st.sidebar.slider("Cost (use good soil)", 0.0, 1.0, 0.3, 0.05, disabled=choice != "Custom weights"),
    gap=st.sidebar.slider("Connectivity", 0.0, 1.0, 0.3, 0.05, disabled=choice != "Custom weights"),
)
if L["demo"]:
    st.sidebar.warning("Demo data. Geometry is synthetic until the real layers are in data/.")

# ---------------- compute ----------------
results = {}
for name, w in C.PROFILES.items():
    t = option(w["heat"], w["soil"], w["gap"], budget)
    results[name] = (t, kpis(t, L, year))
if choice == "Custom weights":
    t = option(cw["heat"], cw["soil"], cw["gap"], budget)
    results[choice] = (t, kpis(t, L, year))
best = max(results, key=lambda n: (targets_met(results[n][1]), results[n][1]["canopy_pct"]))
trees, K = results[choice]
base = kpis(trees.iloc[0:0], L, year)

# ---------------- header and option cards ----------------
st.title("Green Spine")
st.caption("A native-tree corridor generated from site data. Compare three planting strategies, then export the planting schedule.")

cols = st.columns(len(results))
for col, (name, (t, k)) in zip(cols, results.items()):
    with col.container(border=True):
        tag = "  ·  best fit" if name == best else ""
        st.markdown(f"**{name}**{tag}")
        a, b = st.columns(2)
        a.metric("Canopy", f"{k['canopy_pct']:.0f}%")
        b.metric("Shaded route", f"{k['shade_pct']:.0f}%")
        a.metric("Longest gap", f"{k['longest_gap_m']:.0f} m")
        b.metric("Natural soil", f"{k['natural_soil_pct']:.0f}%")
        st.caption(f"{k['trees']} trees · {k['species']} species · {targets_met(k)} of {len(C.TARGETS)} targets met in {year}")

# ---------------- map ----------------
left, right = st.columns([3, 2])
with left:
    st.subheader(f"{choice.strip()} in {year}")
    layers = [pdk.Layer("PolygonLayer", [{"p": ring(p)} for p in polys(L["corridor"])], get_polygon="p",
                        get_fill_color=[235, 235, 235, 160], get_line_color=[150, 150, 150], line_width_min_pixels=1)]
    if not L["unpaved"].is_empty:
        layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p)} for p in polys(L["unpaved"])], get_polygon="p",
                                get_fill_color=[190, 225, 180, 200], stroked=False))
    if not L["road"].is_empty:
        layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p)} for p in polys(L["road"])], get_polygon="p",
                                get_fill_color=[90, 90, 90, 200], stroked=False))
    layers.append(pdk.Layer("PolygonLayer", [{"p": ring(b), "h": h} for b, h in L["buildings"]], get_polygon="p",
                            extruded=True, get_elevation="h", get_fill_color=[205, 205, 205, 255]))
    if L["existing_trees"]:
        lon, lat = ll([p.x for p, _ in L["existing_trees"]], [p.y for p, _ in L["existing_trees"]])
        ex = pd.DataFrame(dict(lon=lon, lat=lat, r=[r for _, r in L["existing_trees"]]))
        ex["h"] = ex.r * 1.8
        ex["label"] = "Existing tree"
        layers.append(pdk.Layer("ColumnLayer", ex, get_position=["lon", "lat"], radius=3.5, get_elevation="h",
                                elevation_scale=1, get_fill_color=[120, 140, 120, 220], pickable=True))
    if len(trees):
        d = trees.copy()
        d["lon"], d["lat"] = ll(d.x, d.y)
        d["r"] = crown_radius(d.size_class, year)
        d["h"] = d.r * 1.8
        d["color"] = d.engineered.map(lambda e: [233, 30, 140, 230] if e else [46, 160, 67, 230])
        d["label"] = d.common_name + " (" + d.size_class + ") · " + d.phase
        for cls, grp in d.groupby("size_class"):
            layers.append(pdk.Layer("ColumnLayer", grp, get_position=["lon", "lat"], radius=float(grp.r.mean()),
                                    get_elevation="h", elevation_scale=1, get_fill_color="color", pickable=True))
    c = L["corridor"].centroid
    clon, clat = ll([c.x], [c.y])
    st.pydeck_chart(pdk.Deck(layers=layers, map_style="light",
                             initial_view_state=pdk.ViewState(longitude=float(clon[0]), latitude=float(clat[0]),
                                                              zoom=16.3, pitch=50, bearing=-20),
                             tooltip={"text": "{label}"}), height=520)
    st.caption("Green: plant now in existing soil. Magenta: needs engineered soil. Grey-green: existing trees.")

with right:
    st.subheader("Against targets")
    rows = []
    for key, (op, val) in C.TARGETS.items():
        label, unit = KPI_LABELS[key]
        ok = (K[key] >= val) if op == ">=" else (K[key] <= val)
        rows.append({"Metric": label, "Today": f"{base[key]:.0f}{unit}", str(year): f"{K[key]:.0f}{unit}",
                     "Target": f"{'at least' if op == '>=' else 'at most'} {val:.0f}{unit}", "Met": "Yes" if ok else "No"})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("'Today' is the corridor with existing trees only. Natural soil has no baseline because nothing new is planted yet.")
    m1, m2 = st.columns(2)
    m1.metric("Engineered soil needed", f"{K['engineered_soil_m3']:.0f} m³")
    m2.metric("Largest species share", f"{K['max_species_share_pct']:.0f}%", help="10-20-30 rule: at most 10% per species")
    if len(trees):
        st.subheader("Species mix")
        st.bar_chart(trees.common_name.value_counts(), height=260, color="#2EA043")

# ---------------- planner outputs ----------------
st.subheader("Planting schedule")
if len(trees):
    sched = trees[["order", "species", "common_name", "size_class", "phase", "moisture", "soil_m3", "x", "y"]].rename(
        columns={"order": "priority", "soil_m3": "rooting_volume_m3", "x": "x_rd", "y": "y_rd"}).round({"x_rd": 1, "y_rd": 1})
    st.dataframe(sched, hide_index=True, height=260)
    d1, d2, _ = st.columns([1, 1, 3])
    slug = choice.split()[0].lower()
    d1.download_button("Download schedule (CSV)", sched.to_csv(index=False), f"planting_schedule_{slug}.csv", "text/csv")
    d2.download_button("Download KPIs (JSON)", json.dumps({"option": choice.strip(), "year": year, **{k: round(float(v), 2) for k, v in K.items()}}, indent=2),
                       f"kpis_{slug}_{year}.json", "application/json")
else:
    st.info("No trees placed with these settings.")

with st.expander("Assumptions"):
    st.markdown(
        "- Tree class sizes, growth rates and rooting volumes are starting values to be confirmed by the team.\n"
        "- Soil is approximated as paved versus unpaved until a soil layer is added.\n"
        "- Heat is approximated as paved ground far from existing canopy.\n"
        "- Underground utilities are an assumed no-plant strip.\n"
        "- The 30% canopy target follows the 3-30-300 rule; the other targets are team proposals.")
