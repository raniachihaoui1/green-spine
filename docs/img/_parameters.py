"""Builds docs/img/parameters.html and options.html. Values are read live from backend/parameters.py;
the option results (2040, 90 trees, 10-20-30 rule on) are the run of 13 November 2026, 15:50.
Render to PNG with headless Edge, like _tables.py."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from backend import parameters as P  # noqa: E402
from _tables import CSS, fmt  # noqa: E402

TC = P.TREE_CLASSES
GUESS, SRC, TEAM, CHOICE = "Starting value", "Source", "Team proposal", "User choice"
EXTRA_CSS = """
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12.5px;font-weight:600;white-space:nowrap}
.t-src{background:#dcefdf;color:#1f6b33}.t-guess{background:#fde8d4;color:#9a4a06}.t-team{background:#e4e7f6;color:#33408f}.t-choice{background:#eceeed;color:#444}
h2{font-size:18px;margin:26px 0 8px;color:#1f2a24}
td.num{white-space:nowrap}
.yes{color:#1f6b33;font-weight:700}.no{color:#b3261e;font-weight:700}
.best td{background:#eaf6ec !important}
"""


def tag(s):
    cls = {SRC: "t-src", GUESS: "t-guess", TEAM: "t-team", CHOICE: "t-choice"}[s]
    return f"<span class='tag {cls}'>{s}</span>"


def tbl(head, rows, widths):
    cols = "".join(f'<col style="width:{w}%">' for w in widths)
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join(f"<tr{' class=best' if r and r[0] == '__best__' else ''}>" +
                   "".join(f"<td>{c}</td>" for c in (r[1:] if r and r[0] == '__best__' else r)) + "</tr>" for r in rows)
    return f"<table><colgroup>{cols}</colgroup><tr>{th}</tr>{body}</table>"


def page(title, sub, inner, foot):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}{EXTRA_CSS}</style></head><body><div class='wrap'>"
            f"<h1><span>Green Spine</span> · {title}</h1><p class='sub'>{sub}</p>{inner}<p class='foot'>{foot}</p></div></body></html>")


H = ["Parameter", "Value", "What it does", "Status", "In the app"]
W = [17, 20, 39, 11, 13]
groups = {
    "Trees": [
        ("Large tree", f"crown radius {TC['large']['r_mature']:.1f} m, {TC['large']['spacing']:.0f} m apart", "Mature size and planting distance of a large tree", GUESS, "File"),
        ("Medium tree", f"crown radius {TC['medium']['r_mature']:.1f} m, {TC['medium']['spacing']:.0f} m apart", "Same for a medium tree", GUESS, "File"),
        ("Small tree", f"crown radius {TC['small']['r_mature']:.1f} m, {TC['small']['spacing']:.0f} m apart", "Same for a small tree", GUESS, "File"),
        ("Crown growth", f"{TC['large']['growth']} / {TC['medium']['growth']} / {TC['small']['growth']} m per year", f"Crown radius grows from {P.PLANTING_RADIUS:.0f} m at planting, linearly, until mature (large / medium / small)", GUESS, "File"),
        ("Soil need", f"{TC['large']['soil_need']} / {TC['medium']['soil_need']} / {TC['small']['soil_need']}", f"Soil quality each size needs (0–1). Open ground = {P.SOIL_UNPAVED}, paving = {P.SOIL_PAVED}; below the need, the tree needs engineered soil", GUESS, "File"),
        ("Engineered soil", f"{TC['large']['soil_m3']} / {TC['medium']['soil_m3']} / {TC['small']['soil_m3']} m³", "Rooting volume to build when a tree is planted in paving", GUESS, "File"),
        ("Tree budget", f"{P.TREE_BUDGET_DEFAULT} trees ({P.TREE_BUDGET_MIN}–{P.TREE_BUDGET_MAX})", "How many trees to plant", CHOICE, "Slider"),
        ("Target year", f"{P.DEFAULT_YEAR} ({P.BASE_YEAR}–{P.YEAR_MAX})", "Year the results are shown for", CHOICE, "Slider"),
    ],
    "Where trees may go": [
        ("Grid", f"{P.CELL:.0f} × {P.CELL:.0f} m", "The route is split into squares of this size", GUESS, "File"),
        ("Distance to buildings", f"{P.TREE_SETBACK_BUILDING_M:.0f} m", "No trunk closer to a facade", GUESS, "Slider"),
        ("Distance to roads", f"{P.TREE_SETBACK_ROAD_M:.0f} m", "No trunk closer to the carriageway", GUESS, "Slider"),
        ("Keep existing trees", f"cover ≥ {P.CANOPY_PROTECT_COVER:.0f}% + {P.CANOPY_ROOT_BUFFER_M:.0f} m root zone", "No new trunk where the RIVM map shows this much tree cover", TEAM, "Switch"),
        ("Soil fit", f"score ≥ {P.SOIL_MIN_COMPATIBILITY}", "A species must match the soil at the nearest borehole this well (team's soil algorithm)", TEAM, "File"),
        ("10-20-30 rule", f"≤ {P.MAX_SPECIES:.0%} / {P.MAX_GENUS:.0%} / {P.MAX_FAMILY:.0%}", "Most trees allowed per species / genus / family; a tree changes size rather than break it", SRC, "Switch"),
    ],
    "Targets": [
        ("Canopy cover", "≥ 30%", "Share of the corridor under tree crowns (3-30-300 rule)", SRC, "KPI bar"),
        ("Shaded route", "≥ 60%", "Share of the walking line under or within 2 m of a crown", TEAM, "KPI bar"),
        ("Longest gap", "≤ 25 m", "Longest stretch of walking line without a crown", TEAM, "KPI bar"),
        ("Trees in natural soil", "≥ 60%", "Share of trees that need no engineered soil", TEAM, "KPI bar"),
        ("Unsealed ground", "≥ 50%", "Share of public ground not paved (cluster passport 1A; annex not yet checked)", SRC, "Synergy index"),
    ],
    "Sun, wind and shelter": [
        ("Design day", "21 June, every 30 min, sun above 10°", "Day used for sun hours and shadows", GUESS, "File"),
        ("Heat check", f"{P.HEAT_CHECK_HOUR_LOCAL:.0f}:00", "Moment of the heat-stress check (route in shade)", TEAM, "File"),
        ("Tall building", f"> {P.WIND_TALL_BUILDING_M:.0f} m", "Gets a wind canopy; its facades count for the wind index", GUESS, "Slider"),
        ("Wind shelter reach", f"{P.WIND_SHELTER_REACH_M:.0f} m", "A facade counts as sheltered with a tree crown this close", GUESS, "File"),
        ("Building canopy", f"{P.CANOPY_WIDTH_M:.0f} m wide, +{P.CANOPY_EXTENSION_PCT:.0f}% past corners", "Shelter strip along every facade of a tall building", GUESS, "Sliders"),
        ("Road pergola", f"{P.PERGOLA_ROAD_PCT:.0f}% of road width, {P.PERGOLA_HEIGHT_M:.0f} m high", "Shelter strip over the middle of the carriageway", GUESS, "Sliders"),
        ("Survival", f"{P.SURVIVAL_NATURAL_SOIL:.0%} natural soil, {P.SURVIVAL_ENGINEERED_SOIL:.0%} engineered", "Expected survival after 10 years (synergy index)", GUESS, "File"),
    ],
}
inner = ""
for g, rows in groups.items():
    inner += f"<h2>{g}</h2>" + tbl(H, [[f"<b>{fmt(a)}</b>", fmt(b), fmt(c), tag(d), fmt(e)] for a, b, c, d, e in rows], W)
out = pathlib.Path(__file__).parent
(out / "parameters.html").write_text(page(
    "Parameters", "The numbers the app works with. All live in backend/parameters.py; the ones marked Slider or Switch can be changed in the dashboard.",
    inner, "<span class='tag t-src'>Source</span> from a policy or published rule · <span class='tag t-team'>Team proposal</span> agreed by the team, not policy · "
           "<span class='tag t-guess'>Starting value</span> placeholder to confirm · <span class='tag t-choice'>User choice</span> set in the dashboard"
           "<br><br>Green Spine · Fellenoord to the Dommel, Eindhoven · AEC NL Hackathon 2026 · 13 November 2026"), encoding="utf-8")

# ---- options
pr = P.PROFILES
wt = tbl(["Option", "Idea", "Heat weight", "Soil weight", "Gap weight", "Plants first where…"], [
    ["<b>A · Most shade</b>", "Cool the hottest paving", f"<b>{pr['A  Most shade']['heat']}</b>", pr['A  Most shade']['soil'], pr['A  Most shade']['gap'], "the ground gets the most sun on 21 June"],
    ["<b>B · Most connected</b>", "Close the gaps in the green line", pr['B  Most connected']['heat'], pr['B  Most connected']['soil'], f"<b>{pr['B  Most connected']['gap']}</b>", "the walking line is furthest from any crown"],
    ["<b>C · Lowest cost</b>", "Use the ground that can carry trees", pr['C  Lowest cost']['heat'], f"<b>{pr['C  Lowest cost']['soil']}</b>", pr['C  Lowest cost']['gap'], "there is open ground, so no engineered soil is needed"],
    ["<b>Custom</b>", "Your own mix", f"{P.CUSTOM_WEIGHTS_DEFAULT['heat']} (slider)", f"{P.CUSTOM_WEIGHTS_DEFAULT['soil']} (slider)", f"{P.CUSTOM_WEIGHTS_DEFAULT['gap']} (slider)", "your weights say"],
], [15, 22, 10, 10, 10, 33])


def yn(ok):
    return "<span class='yes'>✓</span>" if ok else "<span class='no'>✗</span>"


R = [  # option, canopy, shade, gap, natural soil, engineered m3, synergy, heat, wind
    ("Today (existing trees only)", 9.4, 44, 174, None, None, 17, 33, 12),
    ("A · Most shade", 15.7, 57, 69, 40, 1215, 57, 43, 12),
    ("B · Most connected", 17.2, 64, 81, 52, 975, 59, 49, 14),
    ("C · Lowest cost", 16.1, 68, 68, 100, 0, 70, 49, 15),
]
rows = []
for n, c, s, g, ns, e, y, h, w in R:
    met = None if ns is None else (c >= 30) + (s >= 60) + (g <= 25) + (ns >= 60)
    row = [f"<b>{n}</b>",
           f"{c:.0f}% {yn(c >= 30)}", f"{s}% {yn(s >= 60)}", f"{g} m {yn(g <= 25)}",
           "–" if ns is None else f"{ns}% {yn(ns >= 60)}", "–" if e is None else f"{e:,} m³",
           f"{y}", f"{h}%", f"{w}%", "–" if met is None else f"<b>{met} of 4</b>"]
    rows.append(["__best__"] + row if n.startswith("C") else row)
rt = tbl(["Option", "Canopy cover ≥ 30%", "Shaded route ≥ 60%", "Longest gap ≤ 25 m", "Natural soil ≥ 60%",
          "Engineered soil", "Synergy index", "Heat stress (shade 15:00)", "Wind index", "Targets met"], rows,
         [17, 9, 9, 9, 9, 9, 8, 10, 8, 12])
(out / "options.html").write_text(page(
    "Planting options", "Every option plants the same number of trees on the same site. Only the weights differ: they decide which squares are planted first.",
    "<h2>How each option chooses</h2>" + wt +
    "<p class='foot' style='margin-top:8px'>Each square gets a score = heat weight × sun on paving + soil weight × soil quality + gap weight × distance to the nearest crown. "
    "The highest-scoring free square gets a tree, its neighbours within the spacing are blocked, and this repeats until the budget is used.</p>"
    "<h2>What each option achieves in 2040 (90 trees)</h2>" + rt,
    "Highlighted: best fit (most targets met, then most canopy). Synergy index 0–100, heat stress = share of the walking line in shade at 15:00 on 21 June, "
    "wind index = share of tall-building facade with a tree crown within 10 m. Draft corridor, placeholder tree sizes, 10-20-30 rule on: provisional."
    "<br><br>Green Spine · Fellenoord to the Dommel, Eindhoven · AEC NL Hackathon 2026 · 13 November 2026"), encoding="utf-8")
print("html written")
