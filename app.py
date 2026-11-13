"""Respect the framework. Check the ground. Measure the additional value."""
import json
from dataclasses import replace

import pandas as pd
import pydeck as pdk
import streamlit as st

from backend import parameters as P, workflow as W
from backend.metrics.policy import policy_checks
from backend.model import diversity_check, soil_context
from backend.scenarios import input_fingerprint, comparison_table
from backend.view import LAYERS, build_layers, view_state

st.set_page_config(page_title="Green Spine | Evidence-led greening", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
h1, h2, h3 {letter-spacing: -.025em;}
[data-testid="stMetricValue"] {color: #164e36;}
[data-testid="stMetricLabel"] {color: #51645b;}
[data-testid="stSidebar"] {background: #f1f5f1;}
</style>
""", unsafe_allow_html=True)
st.title("Green Spine")
st.markdown("**Respect the masterplan. Test feasible greening. Measure the added value.**")
st.caption("Fellenoord → Dommel · horizontal canopy, ground-rooted facades and optional built shelter")

fingerprint = input_fingerprint()
try:
    existing, masterplan = W.references(fingerprint)
except (ValueError, OSError, KeyError) as exc:
    st.error(f"Cannot load the reference data: {exc}")
    st.stop()

view = st.segmented_control("Assessment state", ["Existing", "Masterplan", "Green Spine"], default="Green Spine")
if masterplan is None:
    st.warning("Masterplan geometry pending. Green Spine currently explores today's layout. "
               "No masterplan compliance or added value against the masterplan can be claimed.")
else:
    st.info(f"Reference: {masterplan['reference']['name']} · {masterplan['reference']['date']} · "
            f"{masterplan['reference']['status']}. Buildings and roads are locked; only additional greening is proposed.")
if view == "Masterplan" and masterplan is None:
    st.info("Supply the documented layer package described in docs/MASTERPLAN_IMPORT.md. "
            "This view deliberately has no substitute geometry or invented metrics.")
    st.stop()

reference = int(masterplan is not None and view != "Existing")
L, plants, grid, _ = W.site(fingerprint, reference)
is_proposal = view == "Green Spine"
reference_label = "masterplan" if reference else "existing conditions"

with st.sidebar:
    st.header("1 · Choose the intervention")
    choice = st.selectbox("Priority", list(P.PROFILES), disabled=not is_proposal)
    st.caption({
        "A  Exposed areas": "Prioritise sunny paving. Not a guarantee of maximum cooling.",
        "B  Canopy gaps": "Prioritise distances from canopy. Compare the resulting gaps.",
        "C  Open ground": "Prefer existing unsealed ground. Not a priced cost optimisation.",
    }[choice])
    budget = st.slider("Maximum additional trees", P.TREE_BUDGET_MIN, P.TREE_BUDGET_MAX,
                       P.TREE_BUDGET_DEFAULT, P.TREE_BUDGET_STEP, disabled=not is_proposal)
    year = st.select_slider("Assessment year", options=list(range(P.BASE_YEAR, P.YEAR_MAX + 1, P.YEAR_STEP)),
                            value=P.DEFAULT_YEAR)
    share = st.slider("Street-facade ambition (%)", 0, 100, int(P.FACADE_GREEN_SHARE_PCT), 5,
                      disabled=not is_proposal, help="Whole suitable walls, up to this share. Rooting, access and structural approval remain conditional.")
    engineering = st.checkbox("Allow conditional engineered rooting space", P.ALLOW_ENGINEERED_SOIL,
                              disabled=not is_proposal)
    enforce = st.checkbox("Enforce 10–20–30 diversity", P.ENFORCE_10_20_30, disabled=not is_proposal)
    with st.expander("Optional shelter proposals"):
        st.caption("Our additions, not assumed masterplan commitments. Traffic, fire access and structures need approval.")
        can_on = st.checkbox("Propose building canopies", P.CANOPY_ENABLED, disabled=not is_proposal)
        per_on = st.checkbox("Propose road pergola", P.PERGOLA_ENABLED, disabled=not is_proposal)
    with st.expander("Map layers"):
        shown = st.multiselect("Visible evidence", list(LAYERS),
                               default=["buildings", "corridor", "canopy", "green", "roads", "facades", "structures"],
                               format_func=lambda k: LAYERS[k][0])
    st.caption("A point is a candidate, not permission to plant. Unknown utilities, groundwater and rooting conditions require site investigation.")

settings = W.Proposal(tuple(P.PROFILES[choice].values()), budget, engineering, enforce, can_on, per_on)
try:
    proposal = W.planting(fingerprint, reference, settings) if is_proposal else None
    trees = proposal.trees if proposal is not None else pd.DataFrame()
    G = W.walls(fingerprint, reference, year, share if is_proposal else 0, settings if is_proposal else None)
    can, per = (W.structures(fingerprint, reference, settings) if is_proposal
                else (L.get("canopies"), L.get("pergola")))
    M = (W.results(fingerprint, reference, settings, year, share) if is_proposal
         else W.baseline(fingerprint, reference, year))
except (ValueError, OSError) as exc:
    st.error(f"Cannot assess this intervention: {exc}")
    st.stop()

left, right = st.columns([3, 1])
with left:
    title = ("Masterplan + Green Spine" if reference else "Existing layout + exploratory Green Spine") if is_proposal else view
    st.subheader(f"2 · {title}")
    deck = pdk.Deck(layers=build_layers(L, grid, trees, year, {k: k in shown for k in LAYERS},
                                      can, per, soil_context(tuple(plants.species)), G["bands"]),
                    map_style="light", initial_view_state=view_state(L), tooltip={"text": "{label}"})
    st.pydeck_chart(deck, height=P.MAP_HEIGHT_PX)
    st.caption("Grey-green: existing canopy symbols, not surveyed tree individuals. Amber: committed plan trees. "
               "Green: proposed trees on mapped open ground. Magenta: engineered rooting space. "
               "Dark walls: conditional climbers. Geometry and materials are indicative.")
with right:
    st.subheader("3 · Read the evidence")
    base = W.baseline(fingerprint, reference, year)
    for key, label, unit in (("canopy_pct", "Canopy footprint", "%"),
                              ("shade_3pm_pct", "Route shade · 21 June, 15:00", "%"),
                              ("longest_gap_m", "Longest canopy-proximity gap", " m"),
                              ("unsealed_pct", "Unsealed public ground", "%")):
        delta = f"{M[key] - base[key]:+.1f}{unit} vs {reference_label}" if is_proposal else None
        st.metric(label, f"{M[key]:.1f}{unit}", delta,
                  delta_color="inverse" if key == "longest_gap_m" else "normal")
    st.caption(f"Canopy ambition: {P.TARGETS['canopy_pct'][1]:g}% (team corridor target). "
               "The gap uses crown proximity, not sunshine or walking access.")
    if is_proposal:
        st.metric("Additional trees", f"{len(trees)} / {budget}")
        st.metric("Facade potential this year", f"{G['area_m2']:,.0f} m²")
        st.caption(f"Survival-adjusted canopy estimate: {M['survival_adjusted_canopy_pct']:.1f}%; "
                   f"shade estimate: {M['heat']['survival_adjusted_shaded_pct']:.1f}%. "
                   "These scale incremental benefit, not an individual mortality simulation.")

comparison, feasibility, water, growth, exports = st.tabs(
    ["What changes?", "Can it be planted?", "Water & policy", "Growth & species", "Presentation & exports"])
with comparison:
    st.markdown("#### Existing → masterplan → additional Green Spine")
    if is_proposal:
        original = W.baseline(fingerprint, 0, year)
        planned = W.baseline(fingerprint, 1, year) if masterplan else None
        table = comparison_table(original, planned, M)
        if masterplan and not existing["centreline"].equals(masterplan["centreline"]):
            table.loc[table.Metric == "Route shade at 15:00",
                      ["Development effect", "Added Green Spine value", "Overall change"]] = None
            st.warning("The route changes between references. Shade values use each route; cross-route shade deltas are not comparable.")
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption("Percentage changes are percentage points. The assessment corridor stays fixed. "
                   "Public-ground percentages may have different denominators when footprints change. Blank means not assessed, never zero.")
        if st.button("Compare all three priorities"):
            rows = []
            for name, weights in P.PROFILES.items():
                candidate = replace(settings, weights=tuple(weights.values()))
                value = W.results(fingerprint, reference, candidate, year, share)
                rows.append({"Priority": name, "Trees": value["trees"], "Canopy (%)": value["canopy_pct"],
                             "Shade (%)": value["shade_3pm_pct"], "Gap (m)": value["longest_gap_m"],
                             "Engineered soil (m³)": value["engineered_soil_m3"]})
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption("Trade-offs, not an automatic 'best' score. Construction and lifecycle prices are not supplied.")
    else:
        st.info("Select Green Spine to measure additions to the selected reference.")

with feasibility:
    st.markdown("#### Feasibility first; benefits second")
    st.warning("All generated planting remains conditional. Borehole compatibility is not proof of local root volume, "
               "groundwater clearance, underground access or structural capacity.")
    a, b, c = st.columns(3)
    a.metric("On mapped open ground", f"{M['natural_soil_pct']:.0f}%" if len(trees) else "Not applicable")
    b.metric("Rootable volume required", f"{M['rooting_volume_required_m3']:,.0f} m³")
    c.metric("Construction-approved trees", "Not assessed")
    st.caption("Volume is screened with class-specific depth and non-overlapping root zones. Missing depth uses a labelled assumption. "
               "Known water, roads, buildings, utility zones and underground structures are excluded. Species and class are chosen before spacing is committed.")
    if len(trees):
        st.dataframe(trees[["order", "common_name", "size_class", "phase", "soil_m3", "available_soil_m3",
                           "depth_evidence", "soil_fit", "borehole_dist_m", "soil_confidence"]].round(2),
                     hide_index=True, width="stretch")
    rejects = pd.DataFrame(proposal.rejections if proposal is not None else [])
    if not rejects.empty:
        st.dataframe(rejects.reason.value_counts().rename_axis("Reason").reset_index(name="Cells"), hide_index=True)
    st.markdown("**Vertical greenery**")
    st.write(f"{G['walls']} candidate walls · {G['area_m2']:,.0f} m² grown climber area · "
             "local borehole match and light checked per occupied floor band.")
    st.caption("Street access, utilities, wall openings, support loads, root depth, irrigation supply and maintenance remain unverified. "
               "Facade area is never added to ground canopy or claimed as verified storm storage.")
    st.dataframe(pd.DataFrame(L["data_status"]), hide_index=True, width="stretch")

with water:
    st.markdown("#### Account for rainfall, not just greenery")
    balance = M["water"]
    st.dataframe(pd.DataFrame([
        {"Component": "Rain on assessed public ground", "m³": balance["storm_m3"]},
        {"Component": "Indicative infiltration", "m³": balance["soak_m3"]},
        {"Component": "Crown interception", "m³": balance["crowns_m3"]},
        {"Component": "Green shelter retention", "m³": balance["roofs_m3"]},
        {"Component": "Remaining runoff", "m³": balance["runoff_m3"]},
    ]), hide_index=True)
    st.caption(f"{P.DESIGN_RAIN_MM:g} mm scenario: components conserve rainfall; overlaps are not counted twice. "
               "No roof-to-tank-to-rootbed routing is assumed without drainage geometry. Fixed infiltration is not measured storage or flood performance.")
    st.dataframe(pd.DataFrame(policy_checks(M)), hide_index=True, width="stretch")
    st.caption("Sources: Cluster 1A passport, annex 2.d.1–2.d.5. Other clusters have different rules. "
               "Wind is only a geometric facade-proximity proxy, not a comfort certification.")

with growth:
    if is_proposal:
        if st.button("Calculate the growth trajectory"):
            st.line_chart(W.growth(fingerprint, reference, settings))
        D = diversity_check(trees)
        st.write(f"10–20–30 rule: {'met' if D['ok'] else 'not met / no planting'}. "
                 f"Largest species {D['species_pct']:.0f}%, genus {D['genus_pct']:.0f}%, family {D['family_pct']:.0f}%.")
        if len(trees):
            st.bar_chart(trees.common_name.value_counts(), horizontal=True)
        st.caption("Exponential class-based crown growth; survival assumptions apply to incremental-benefit estimates. "
                   "No ecological-score delta is invented for existing trees without species data.")

with exports:
    st.markdown("#### Traceable deliverables")
    report = {"view": title, "reference": L["reference"], "year": year,
              "masterplan_available": masterplan is not None, "planting_is_conditional": True,
              "parameters": settings.__dict__, "metrics": M, "data_status": L["data_status"],
              "policy_checks": policy_checks(M)}
    st.download_button("Assessment JSON", json.dumps(report, indent=2, allow_nan=False),
                       "green_spine_assessment.json", "application/json")
    if len(trees):
        st.download_button("Planting schedule CSV", trees.to_csv(index=False), "green_spine_planting.csv", "text/csv")
    if not rejects.empty:
        st.download_button("Cell decisions CSV", rejects.to_csv(index=False), "green_spine_cell_decisions.csv", "text/csv")
    st.download_button("Interactive 3D HTML", deck.to_html(as_string=True), "green_spine_view.html", "text/html")
    if st.button("Prepare high-resolution scene export"):
        from backend.rendering import scene_package
        st.download_button("Blender scene data", json.dumps(scene_package(L, trees, year, can, per, G, title), allow_nan=False),
                           "green_spine_scene.json", "application/json")
    st.caption("High-resolution rendering: use scripts/render_scene.py with Blender and this scene data. "
               "Physically based lighting and materials are illustrative; they do not verify architecture or planting feasibility.")
    st.code('blender --background --python scripts/render_scene.py -- --scene green_spine_scene.json --output green_spine')

with st.expander("Method, assumptions and limits"):
    st.markdown("**Story:** We do not replace the masterplan. We test additional greening within its supplied framework. "
                "Until that framework arrives, this is an existing-condition exploration.\n\n"
                "**Evidence:** 3D BAG masses, RIVM 2022 fractional canopy, OSM surface proxies and a draft route, BRO borehole "
                "compatibility, and the team's plant database. Raster canopy is area-weighted at corridor boundaries. "
                "The 3D trees represent canopy, not a surveyed tree inventory.\n\n"
                "**Not yet evidenced:** groundwater, detailed utilities and basements, pedestrian flows, heat/flood rasters, "
                "species-specific street tolerance, construction costs, structural loads, municipal green-quality weights, "
                "accessible cool places and roof-drainage routes. Unknown is not a pass.\n\n"
                "**Metrics:** canopy is a physical plan-view projection; route shade uses solar geometry; canopy-proximity "
                "gaps are separate from shade; root volumes are screened, not certified; facade, ground and shelter areas "
                "remain separate. Rendering adds no quantitative evidence.")
