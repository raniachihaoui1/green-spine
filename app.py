"""Green Spine dashboard. Run with:  streamlit run app.py"""
import json
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
from pyproj import Transformer
from shapely.geometry import Polygon

from backend import parameters as C
from backend.cover import building_canopies, road_pergola, covered_ground
from backend.data_io import load_layers
from backend.model import build_grid, run_option, kpis, targets_met, crown_radius, canopy_geometry

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


def ring(poly, z=None):
    lon, lat = ll(*poly.exterior.xy)
    if z is None:
        return [[float(a), float(b)] for a, b in zip(lon, lat)]
    return [[float(a), float(b), float(z)] for a, b in zip(lon, lat)]


def polys(geom):
    if geom.is_empty:
        return []
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


@st.cache_data(show_spinner=False)
def load():
    return load_layers("data"), pd.read_csv("data/plants.csv")


@st.cache_data(show_spinner=False)
def structures(on, min_h, width, ext, avoid_road, p_on, p_width, p_len):
    """Building canopies and road pergola for the current sidebar settings."""
    L, _ = load()
    can = building_canopies(L, min_h, width, ext, avoid_road) if on else dict(geom=Polygon(), per_building=[], facade_m=0.0, n_buildings=0)
    per = road_pergola(L["road"], p_width, p_len) if p_on else Polygon()
    return can, per


@st.cache_data(show_spinner="Building grid")
def grid_for(sb_bld, sb_road, avoid_can, can_key):
    L, _ = load()
    no_plant = structures(*can_key)[0]["geom"] if avoid_can else None
    return build_grid(L, sb_bld, sb_road, no_plant)


@st.cache_data(show_spinner="Placing trees")
def option(heat, soil, gap, budget, grid_key):
    L, plants = load()
    return run_option(L, grid_for(*grid_key), plants, dict(heat=heat, soil=soil, gap=gap), budget)


L, plants = load()

# ---------------- sidebar ----------------
st.sidebar.title("Green Spine")
st.sidebar.caption("Fellenoord to the Dommel, Eindhoven")
names = list(C.PROFILES) + ["Custom weights"]
choice = st.sidebar.radio("Option", names, index=0)
budget = st.sidebar.slider("Tree budget", C.TREE_BUDGET_MIN, C.TREE_BUDGET_MAX, C.TREE_BUDGET_DEFAULT, C.TREE_BUDGET_STEP)
year = st.sidebar.select_slider("Year", options=list(range(C.BASE_YEAR, C.YEAR_MAX + 1, 2)), value=C.DEFAULT_YEAR)
st.sidebar.markdown("**Custom weights**")
cw = dict(
    heat=st.sidebar.slider("Shade (heat)", 0.0, 1.0, C.CUSTOM_WEIGHTS_DEFAULT["heat"], 0.05, disabled=choice != "Custom weights"),
    soil=st.sidebar.slider("Cost (use good soil)", 0.0, 1.0, C.CUSTOM_WEIGHTS_DEFAULT["soil"], 0.05, disabled=choice != "Custom weights"),
    gap=st.sidebar.slider("Connectivity", 0.0, 1.0, C.CUSTOM_WEIGHTS_DEFAULT["gap"], 0.05, disabled=choice != "Custom weights"),
)
with st.sidebar.expander("Tree setbacks"):
    sb_bld = st.slider("Distance to buildings (m)", 0.0, 15.0, C.TREE_SETBACK_BUILDING_M, 0.5)
    sb_road = st.slider("Distance to carriageway (m)", 0.0, 10.0, C.TREE_SETBACK_ROAD_M, 0.5)
    avoid_can = st.checkbox("No trees under building canopies", C.TREE_AVOID_CANOPIES)
with st.sidebar.expander("Building canopies (wind)"):
    can_on = st.checkbox("Place canopies", C.CANOPY_ENABLED)
    can_h = st.slider("On buildings taller than (m)", 0.0, 120.0, C.CANOPY_MIN_BUILDING_HEIGHT_M, 1.0, disabled=not can_on)
    can_w = st.slider("Canopy width (m)", 0.5, 10.0, C.CANOPY_WIDTH_M, 0.5, disabled=not can_on)
    can_ext = st.slider("Extension past corners (% of facade length)", 0.0, 100.0, C.CANOPY_EXTENSION_PCT, 5.0, disabled=not can_on)
    can_road = st.checkbox("Keep canopies off the carriageway", C.CANOPY_AVOID_ROAD, disabled=not can_on)
with st.sidebar.expander("Road pergola"):
    per_w = st.slider("Pergola width (% of road width, centred)", 0.0, 100.0, C.PERGOLA_ROAD_PCT, 5.0)
    per_l = st.slider("Pergola length (% of road length, centred)", 0.0, 100.0, C.PERGOLA_LENGTH_PCT, 5.0)
can_key = (can_on, can_h, can_w, can_ext, can_road, C.PERGOLA_ENABLED and per_w > 0, per_w, per_l)
grid_key = (sb_bld, sb_road, avoid_can, can_key)
canopies, pergola = structures(*can_key)
if L["demo"]:
    st.sidebar.warning("Demo data. Geometry is synthetic until the real layers are in data/.")

# ---------------- compute ----------------
results = {}
for name, w in C.PROFILES.items():
    t = option(w["heat"], w["soil"], w["gap"], budget, grid_key)
    results[name] = (t, kpis(t, L, year))
if choice == "Custom weights":
    t = option(cw["heat"], cw["soil"], cw["gap"], budget, grid_key)
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
    if not canopies["geom"].is_empty:
        layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p, C.CANOPY_HEIGHT_M), "label": "Building canopy"}
                                                 for p in polys(canopies["geom"])],
                                get_polygon="p", extruded=True, get_elevation=C.CANOPY_THICKNESS_M,
                                get_fill_color=[30, 120, 200, 220], pickable=True))
    if not pergola.is_empty:
        layers.append(pdk.Layer("PolygonLayer", [{"p": ring(p, C.PERGOLA_HEIGHT_M), "label": "Road pergola"}
                                                 for p in polys(pergola)],
                                get_polygon="p", extruded=True, get_elevation=0.3,
                                get_fill_color=[240, 160, 40, 200], pickable=True))
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
    st.caption("Green: plant now in existing soil. Magenta: needs engineered soil. Grey-green: existing trees. "
               "Blue: building canopies. Orange: road pergola.")

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

# ---------------- covered ground ----------------
st.subheader("Covered ground: canopies and pergola")
crowns = canopy_geometry(trees, L, year)
CG = covered_ground(L, canopies["geom"], pergola, crowns)
g1, g2, g3, g4 = st.columns(4)
g1.metric("Covered ground in corridor", f"{CG['covered_m2']:,.0f} m²", f"{CG['covered_public_pct']:.1f}% of public ground", delta_color="off", delta_arrow="off")
g2.metric("Canopies", f"{CG['canopy_m2']:,.0f} m²", f"{canopies['n_buildings']} buildings · {canopies['facade_m']:,.0f} m facade", delta_color="off", delta_arrow="off")
g3.metric("Road pergola", f"{CG['pergola_m2']:,.0f} m²", f"{CG['road_covered_pct']:.0f}% of carriageway", delta_color="off", delta_arrow="off")
g4.metric("Small greenery on structures", f"{CG['green_on_structures_m2']:,.0f} m²", f"holds {CG['green_retention_m3']:,.0f} m³ rain", delta_color="off", delta_arrow="off")
h1, h2, h3, h4 = st.columns(4)
h1.metric("Pedestrian ground under canopies", f"{CG['pedestrian_covered_m2']:,.0f} m²")
h2.metric("Sheltered from sun / rain", f"{CG['sun_sheltered_m2']:,.0f} / {CG['rain_sheltered_m2']:,.0f} m²")
h3.metric("Rain kept off the ground", f"{CG['rain_kept_off_m3']:,.0f} m³", f"per {C.DESIGN_RAIN_MM:.0f} mm storm", delta_color="off", delta_arrow="off")
h4.metric("Sheltered route", f"{CG['route_sheltered_all_pct']:.0f}%", f"{CG['route_sheltered_structures_pct']:.0f}% from structures alone", delta_color="off", delta_arrow="off")
st.caption(f"Canopies sit on buildings taller than {can_h:.0f} m, {can_w:.1f} m wide, running {can_ext:.0f}% of the facade length past the corners. "
           f"Areas count only inside the corridor ({CG['canopy_total_m2']:,.0f} m² of canopy in total). "
           f"Sheltered route = share of the centreline under canopies, pergola or tree crowns in {year}. Geometry is indicative.")

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
        "- Trees keep a set distance from facades and the carriageway (Tree setbacks).\n"
        "- Building canopies are indicative strips along every facade of tall buildings; a wind study is needed to size them.\n"
        "- The road pergola is a strip centred on the carriageway; road width is estimated per road section.\n"
        "- All starting values live in backend/parameters.py.\n"
        "- The 30% canopy target follows the 3-30-300 rule; the other targets are team proposals.")
