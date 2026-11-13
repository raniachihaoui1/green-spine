"""Green Spine dashboard. Run with:  streamlit run app.py

Three steps, left to right (team's Miro hierarchy): 1 Choose, 2 See (3D map and the four targets),
3 Results. Computation lives in backend/; every number in backend/parameters.py.
"""
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import shapely
import streamlit as st
from shapely.geometry import Polygon

from backend import parameters as C
from backend import facades as FAC
from backend.cover import building_canopies, road_pergola
from backend.data_io import load_layers
from backend.metrics import covered_ground, ecosystem_score, heat_stress, wind_index, water_retention
from backend.metrics.wind import tall_facades
from backend.model import (base_grid, mask_grid, run_option, kpis, targets_met, canopy_geometry, diversity_check,
                           route_base, soil_context)
from backend.view import LAYERS, build_layers, view_state

st.set_page_config(page_title="Green Spine", layout="wide")

STRATEGIES = {
    "A  Most shade": "Plants first where the paving gets the most sun, to cool the hottest spots.",
    "B  Most connected": "Plants first where the walking line is furthest from any tree, to close the gaps.",
    "C  Lowest cost": "Plants first on open ground, so no engineered soil has to be built.",
    "Custom weights": "Your own mix of heat, soil and gaps (set them under Advanced settings).",
}
KPI_LABELS = {
    "canopy_pct": ("Tree cover", "%", "Share of the corridor under tree crowns"),
    "shade_pct": ("Shaded walk", "%", "Share of the walking line under or next to a crown"),
    "longest_gap_m": ("Longest sunny stretch", " m", "Longest part of the walk with no tree"),
    "natural_soil_pct": ("Trees in real soil", "%", "Trees that need no engineered soil"),
}
GREEN, GREY = "#2EA043", "#8C959F"
LAYER_DEFAULT = ["buildings", "corridor", "canopy", "roads", "facades", "structures", "understorey"]


# ---------------- cached computation ----------------
@st.cache_data(show_spinner="Loading the site and computing sun hours (first run only, about 30 s)")
def load():
    L = load_layers()
    L["route"] = route_base(L)
    tall_facades(L)                                   # cached inside L
    plants = pd.read_csv(Path(C.PROCESSED_DIR) / "plants.csv")
    FB = FAC.facade_sun(FAC.street_facades(L), L)
    return L, plants, base_grid(L, tuple(plants.species)), FB


@st.cache_data(show_spinner=False)
def structures(on, min_h, width, ext, avoid_road, p_on, p_width, p_len):
    L = load()[0]
    can = building_canopies(L, min_h, width, ext, avoid_road) if on else dict(geom=Polygon(), per_building=[], facade_m=0.0, n_buildings=0)
    per = road_pergola(L["road"], p_width, p_len) if p_on else Polygon()
    return can, per


@st.cache_data(show_spinner=False)
def grid_for(sb_bld, sb_road, avoid_can, protect, can_key, enforce=None):
    """Plantable cells. `enforce` (10-20-30 switch) rides along in grid_key but does not change the grid."""
    L, _, g0, _ = load()
    no_plant = structures(*can_key)[0]["geom"] if avoid_can else None
    return mask_grid(g0, L, sb_bld, sb_road, no_plant, protect)


@st.cache_data(show_spinner="Placing trees")
def option(heat, soil, gap, budget, grid_key):
    L, plants, _, _ = load()
    return run_option(L, grid_for(*grid_key), plants, dict(heat=heat, soil=soil, gap=gap), budget, grid_key[-1])


@st.cache_data(show_spinner=False)
def option_kpis(w, budget, grid_key, year):
    return kpis(option(*w, budget, grid_key), load()[0], year)


@st.cache_data(show_spinner=False)
def green_walls(share):
    return FAC.green_facades(load()[3], share)


@st.cache_data(show_spinner="Computing results")
def outputs(w, budget, grid_key, year, can_key):
    L, plants, _, _ = load()
    trees = option(*w, budget, grid_key)
    can, per = structures(*can_key)
    K = option_kpis(w, budget, grid_key, year)
    crowns = canopy_geometry(trees, L, year)
    cover = covered_ground(L, can["geom"], per, crowns)
    none = trees.iloc[0:0]
    return dict(
        eco=ecosystem_score(trees, L, plants, year, K), eco0=ecosystem_score(none, L, plants, year),
        heat=heat_stress(trees, L, year, can["geom"], per), heat0=heat_stress(none, L, year),
        wind=wind_index(trees, L, year, can["geom"], crowns),
        water=water_retention(trees, L, year, cover["green_on_structures_m2"]), water0=water_retention(none, L, year),
        cover=cover,
    )


@st.cache_data(show_spinner=False)
def growth(w, budget, grid_key):
    L = load()[0]
    trees = option(*w, budget, grid_key)
    years = list(range(C.BASE_YEAR, C.YEAR_MAX + 1, 4))
    pct = [100 * canopy_geometry(trees, L, y).intersection(L["corridor"]).area / L["corridor"].area for y in years]
    return pd.DataFrame({"Tree cover (%)": pct, "Target 30%": C.TARGETS["canopy_pct"][1]}, index=years)


L, plants, grid0, FB = load()
S = soil_context(tuple(plants.species))

# ---------------- header ----------------
st.markdown("## Green Spine")
st.caption("A tree corridor from Fellenoord to the Dommel, Eindhoven. **1** choose a strategy and how many trees, "
           "**2** see where they go and whether the targets are met, **3** read the results and download the planting list.")

col_in, col_map, col_out = st.columns([1.0, 2.7, 1.45], gap="medium")

# ---------------- 2. strategy switch (read first: the inputs depend on it) ----------------
with col_map:
    st.markdown("##### 2. See")
    choice = st.segmented_control("Strategy", list(STRATEGIES), default="A  Most shade", label_visibility="collapsed") or "A  Most shade"
    st.caption(STRATEGIES[choice])

# ---------------- 1. choose ----------------
with col_in:
    with st.container(border=True):
        st.markdown("##### 1. Choose")
        budget = st.slider("Trees to plant", C.TREE_BUDGET_MIN, C.TREE_BUDGET_MAX, C.TREE_BUDGET_DEFAULT, C.TREE_BUDGET_STEP)
        year = st.select_slider("Year", options=list(range(C.BASE_YEAR, C.YEAR_MAX + 1, 2)), value=C.DEFAULT_YEAR,
                                help="Trees grow over time; results are shown for this year.")
        green_share = st.slider("Street facades with climbers (%)", 0, 100, int(C.FACADE_GREEN_SHARE_PCT), 5,
                                help="Sunniest walls first. Climbers come from the team's soil-compatible plant list.")
        shown = st.pills("Show on map", list(LAYERS), default=LAYER_DEFAULT, selection_mode="multi",
                         format_func=lambda k: LAYERS[k][0].split(" (")[0])
        show = {k: k in (shown or []) for k in LAYERS}

        with st.expander("Advanced settings"):
            custom = choice == "Custom weights"
            st.markdown("**Custom strategy weights**" + ("" if custom else "  \n:gray[used when Custom weights is selected]"))
            base_w = C.CUSTOM_WEIGHTS_DEFAULT
            cw = dict(
                heat=st.slider("Heat (sunny paving)", 0.0, 1.0, float(base_w["heat"]), 0.05, disabled=not custom),
                soil=st.slider("Soil (open ground)", 0.0, 1.0, float(base_w["soil"]), 0.05, disabled=not custom),
                gap=st.slider("Gaps (far from trees)", 0.0, 1.0, float(base_w["gap"]), 0.05, disabled=not custom),
            )
            st.markdown("**Rules for trees**")
            enforce = st.checkbox("10-20-30 diversity rule (Santamour)", C.ENFORCE_10_20_30,
                                  help="At most 10% per species, 20% per genus, 30% per family.")
            protect = st.checkbox(f"Keep existing trees (≥ {C.CANOPY_PROTECT_COVER:.0f}% cover)", True)
            sb_bld = st.slider("Distance to buildings (m)", 0.0, 15.0, C.TREE_SETBACK_BUILDING_M, 0.5)
            sb_road = st.slider("Distance to roads (m)", 0.0, 10.0, C.TREE_SETBACK_ROAD_M, 0.5)
            avoid_can = st.checkbox("No trees under building canopies", C.TREE_AVOID_CANOPIES)
            st.markdown("**Built shelter**")
            can_on = st.checkbox(f"Wind canopies on buildings over {C.CANOPY_MIN_BUILDING_HEIGHT_M:.0f} m", C.CANOPY_ENABLED)
            can_w = st.slider("Canopy width (m)", 0.5, 10.0, C.CANOPY_WIDTH_M, 0.5, disabled=not can_on)
            per_w = st.slider("Road pergola (% of road width)", 0.0, 100.0, C.PERGOLA_ROAD_PCT, 5.0)

can_key = (can_on, C.CANOPY_MIN_BUILDING_HEIGHT_M, can_w, C.CANOPY_EXTENSION_PCT, C.CANOPY_AVOID_ROAD,
           C.PERGOLA_ENABLED and per_w > 0, per_w, C.PERGOLA_LENGTH_PCT)
grid_key = (sb_bld, sb_road, avoid_can, protect, can_key, enforce)
canopies, pergola = structures(*can_key)

# ---------------- compute ----------------
weights = {n: (w["heat"], w["soil"], w["gap"]) for n, w in C.PROFILES.items()}
weights["Custom weights"] = (cw["heat"], cw["soil"], cw["gap"])
cards = {n: option_kpis(weights[n], budget, grid_key, year) for n in C.PROFILES}
best = max(cards, key=lambda n: (targets_met(cards[n]), cards[n]["canopy_pct"]))
w_sel = weights[choice]
trees = option(*w_sel, budget, grid_key)
K = option_kpis(w_sel, budget, grid_key, year)
base = kpis(trees.iloc[0:0], L, year)
O = outputs(w_sel, budget, grid_key, year, can_key)
G = green_walls(green_share)

# ---------------- 2. map and the four targets ----------------
with col_map:
    layers = build_layers(L, grid0, trees, year, show, canopies["geom"], pergola, S, G["bands"])
    st.pydeck_chart(pdk.Deck(layers=layers, map_style="light", initial_view_state=view_state(L),
                             tooltip={"text": "{label}"}), height=520)
    st.caption("New trees: green = plant now, magenta = needs engineered soil. Grey-green: existing trees kept (RIVM 2022, "
               "height indicative); red: existing trees cleared for a new tree. Light green: shrubs and low vegetation on open "
               "ground (indicative). Dark green walls: climbers. Blue: wind canopies. Orange: road pergola. Hover for details.")

    kc = st.columns(4)
    for col, (key, (label, unit, helptext)) in zip(kc, KPI_LABELS.items()):
        op, target = C.TARGETS[key]
        v = K[key]
        ok = v >= target if op == ">=" else v <= target
        progress = min(v / target, 1.0) if op == ">=" else (min(target / v, 1.0) if v > 0 else 1.0)
        with col.container(border=True):
            st.metric(label, f"{v:.0f}{unit}", None if key == "natural_soil_pct" else f"{v - base[key]:+.0f}{unit.strip()} vs today",
                      delta_color="normal" if op == ">=" else "inverse", help=helptext)
            st.progress(progress, text=("✓ target " if ok else "target ") + f"{'≥' if op == '>=' else '≤'} {target:.0f}{unit}")

    with st.expander(f"Compare strategies in {year}  ·  best fit: {best.strip()}"):
        st.dataframe(pd.DataFrame([{
            "Strategy": n.strip() + ("  ★" if n == best else ""), "Tree cover": f"{k['canopy_pct']:.0f}%",
            "Shaded walk": f"{k['shade_pct']:.0f}%", "Longest sunny stretch": f"{k['longest_gap_m']:.0f} m",
            "Trees in real soil": f"{k['natural_soil_pct']:.0f}%", "Targets met": f"{targets_met(k)} of 4"}
            for n, k in cards.items()]), hide_index=True, width="stretch")
        st.caption("★ = most targets met, then most tree cover.")

# ---------------- 3. results ----------------
with col_out:
    with st.container(border=True):
        st.markdown(f"##### 3. Results in {year}")
        E, E0, H, H0, Wt, Wt0, Wd = O["eco"], O["eco0"], O["heat"], O["heat0"], O["water"], O["water0"], O["wind"]
        r1, r2 = st.columns(2)
        r1.metric("Nature score", f"{E['score']:.0f}/100", f"{E['score'] - E0['score']:+.0f} vs today",
                  help="Synergy index: habitat, diversity, connection to the Dommel and tree survival, 0–100.")
        r2.metric("Shade at 3 pm", f"{H['shaded_pct']:.0f}%", f"{H['shaded_pct'] - H0['shaded_pct']:+.0f} vs today",
                  help="Heat stress: share of the walk in shade at 15:00 on the hottest day (21 June).")
        r3, r4 = st.columns(2)
        r3.metric("Rain kept on site", f"{Wt['kept_pct']:.0f}%", f"{Wt['kept_pct'] - Wt0['kept_pct']:+.0f} vs today",
                  help=f"Share of a {C.DESIGN_RAIN_MM:.0f} mm storm that soaks in or is held by trees and green roofs instead of running off.")
        r4.metric("Green facades", f"{G['area_m2']:,.0f} m²", f"{G['walls']} walls on {G['buildings']} buildings",
                  delta_color="off", delta_arrow="off", help="Climbers on street-facing walls, up to 4 floors.")
        r5, r6 = st.columns(2)
        r5.metric("Wind shelter", "n/a" if Wd["index_pct"] is None else f"{Wd['index_pct']:.0f}%",
                  None if Wd["index_pct"] is None else f"{Wd['with_canopies_pct']:.0f}% with canopies", delta_color="off", delta_arrow="off",
                  help=f"Share of the walls of buildings over {C.WIND_TALL_BUILDING_M:.0f} m with a tree within {C.WIND_SHELTER_REACH_M:.0f} m. A proxy, not a wind simulation.")
        r6.metric("Existing trees kept", f"{K['existing_kept_pct']:.0f}%")

        t1, t2, t3, t4 = st.tabs(["Growth", "Species", "Facades", "Planting list"])
        with t1:
            st.line_chart(growth(w_sel, budget, grid_key), height=200, color=[GREEN, GREY], x_label="Year", y_label="Tree cover (%)")
            st.caption(f"{choice.strip()}, {budget} trees. Crowns grow until mature.")
        with t2:
            if len(trees):
                D = diversity_check(trees)
                st.markdown(("✓ " if D["ok"] else "✗ ") + f"**10-20-30 rule {'met' if D['ok'] else 'not met'}**: "
                            f"largest species {D['species_pct']:.0f}% (≤ 10), genus {D['genus_pct']:.0f}% (≤ 20), family {D['family_pct']:.0f}% (≤ 30)."
                            + (f" {D['resized']} trees changed size to keep it." if D["resized"] else ""))
                st.bar_chart(trees.common_name.value_counts().rename("Trees"), height=230, color=GREEN, horizontal=True)
                st.caption("Every species is checked against the soil at its nearest borehole (team's soil algorithm).")
        with t3:
            if G["walls"]:
                st.markdown(f"**{G['share_pct']:.0f}%** of the {G['street_m']:,.0f} m of street facade is green.")
                st.dataframe(pd.DataFrame(G["species"], columns=["Climber", "Walls"]), hide_index=True, width="stretch")
                st.caption("Sunny walls get sun-loving climbers, shady walls get ivy or honeysuckle (shade columns of the plant database).")
            else:
                st.info("No facades greened. Raise the facade slider in 1. Choose.")
        with t4:
            if len(trees):
                sched = trees[["order", "species", "common_name", "size_class", "phase", "soil_fit", "borehole", "x", "y"]].rename(
                    columns={"order": "priority", "x": "x_rd", "y": "y_rd"}).round({"x_rd": 1, "y_rd": 1, "soil_fit": 2})
                st.dataframe(sched, hide_index=True, height=230)
                slug = choice.split()[0].lower()
                d1, d2 = st.columns(2)
                d1.download_button("Planting list (CSV)", sched.to_csv(index=False), f"planting_list_{slug}.csv", "text/csv")
                d2.download_button("Results (JSON)", json.dumps({
                    "strategy": choice.strip(), "year": year, "trees": len(trees),
                    **{k: round(float(v), 2) for k, v in K.items()},
                    "nature_score": round(E["score"], 1), "shade_3pm_pct": round(H["shaded_pct"], 1),
                    "rain_kept_pct": round(Wt["kept_pct"], 1), "green_facade_m2": round(G["area_m2"]),
                }, indent=2), f"results_{slug}_{year}.json", "application/json")

# ---------------- below: details ----------------
with st.expander("Built shelter: wind canopies and road pergola"):
    CG = O["cover"]
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Covered ground", f"{CG['covered_m2']:,.0f} m²", f"{CG['covered_public_pct']:.1f}% of public ground", delta_color="off", delta_arrow="off")
    g2.metric("Wind canopies", f"{CG['canopy_m2']:,.0f} m²", f"{canopies['n_buildings']} buildings", delta_color="off", delta_arrow="off")
    g3.metric("Road pergola", f"{CG['pergola_m2']:,.0f} m²", f"{CG['road_covered_pct']:.0f}% of the road", delta_color="off", delta_arrow="off")
    g4.metric("Greenery on top", f"{CG['green_on_structures_m2']:,.0f} m²", f"holds {CG['green_retention_m3']:,.0f} m³ rain", delta_color="off", delta_arrow="off")

with st.expander("How it works, data and limits"):
    far = sorted((L["corridor"].distance(shapely.Point(*xy)), b) for b, xy in S["positions"].items())
    st.markdown(
        "**How it works.** The route is split into 2 × 2 m squares. Squares in buildings, on roads, too close to facades or under "
        "existing trees are skipped. Each remaining square gets a score from sun on paving, soil and distance to the nearest tree, "
        "weighted by the strategy. The best square gets a tree, its neighbours are blocked, and this repeats. Each tree gets a native "
        "species that fits the soil at its nearest borehole and keeps the 10-20-30 rule. Climbers go on the sunniest street walls first.\n\n"
        "**Data.** Buildings: 3D BAG. Existing trees: RIVM Bomenkaart 2022. Roads, green, water and the draft route: OpenStreetMap. "
        f"Soil: 6 BRO boreholes from DINOloket ({', '.join(f'{d:.0f} m' for d, _ in far)} from the corridor). "
        "Plants: the team's plant database and soil algorithm. Full list: data/SOURCES.md and docs/DATA_AND_METRICS.md.\n\n"
        "**Limits.** The route is a draft and roads are today's layout. Tree sizes, growth and most targets are starting values "
        "(backend/parameters.py). Sun is for one clear day; wind is a proxy, not a simulation; rain retention uses fixed soak-in "
        "and interception values, not a flood model. Not modelled: air temperature, utilities, people flow.")
