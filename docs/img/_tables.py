"""Builds docs/img/data_table.html and metrics_table.html from the tables in docs/DATA_AND_METRICS.md.
Render to PNG with a headless browser (see README in docs/img)."""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
md = (ROOT / "docs" / "DATA_AND_METRICS.md").read_text(encoding="utf-8")


def table(section):
    block = md.split(f"## {section}")[1].split("\n## ")[0]
    rows = [l for l in block.splitlines() if l.startswith("|")]
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows if not set(r) <= set("|-: ")]
    return cells[0], cells[1:]


def fmt(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)\*(?!\w)", r"<i>\1</i>", s)
    return s


CSS = """
body{margin:0;background:#fff;font-family:'Segoe UI',Roboto,Arial,sans-serif;color:#222}
.wrap{padding:36px 40px 40px}
h1{font-size:30px;margin:0 0 4px;font-weight:700}
h1 span{color:#E91E8C}
p.sub{margin:0 0 22px;color:#555;font-size:15px}
table{border-collapse:collapse;width:100%;font-size:14.5px;line-height:1.38}
th{background:#1f2a24;color:#fff;text-align:left;padding:10px 12px;font-weight:600}
td{padding:9px 12px;vertical-align:top;border-bottom:1px solid #e3e6e4}
tr:nth-child(even) td{background:#f6f8f7}
td:first-child{font-weight:600;color:#1f6b33;white-space:nowrap}
code{font-family:Consolas,monospace;font-size:12.5px;background:#eef1ef;padding:0 3px;border-radius:3px}
.foot{margin-top:16px;color:#666;font-size:13px}
"""


def page(title, sub, head, rows, widths, foot):
    cols = "".join(f'<col style="width:{w}%">' for w in widths)
    th = "".join(f"<th>{fmt(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{fmt(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='wrap'>"
            f"<h1><span>Green Spine</span> · {title}</h1><p class='sub'>{sub}</p>"
            f"<table><colgroup>{cols}</colgroup><tr>{th}</tr>{body}</table><p class='foot'>{foot if foot.startswith('<b>') else fmt(foot)}</p></div></body></html>")


out = pathlib.Path(__file__).parent
h, r = table("1. Data")
refs = md.split("### References")[1].split("\n## ")[0].strip().splitlines()
refs_html = "<br>".join(fmt(l) for l in refs if l.strip())
(out / "data_table.html").write_text(page(
    "Data we used", "Where each dataset comes from, how we collected it, how the model uses it and which KPIs it feeds.",
    h, r, [11, 14, 25, 30, 20],
    "<b>References</b><br>" + refs_html + "<br><br>Fellenoord to the Dommel, Eindhoven · AEC NL Hackathon 2026 · 13 November 2026 · Draft corridor; file details in data/SOURCES.md"), encoding="utf-8")
h, r = table("2. Metrics")
(out / "metrics_table.html").write_text(page(
    "Metrics and KPIs", "How every number on the dashboard is calculated and how it affects the result. "
    "Only the four bold KPIs have targets; they pick the best-fit option.",
    h, r, [13, 42, 13, 32],
    "Values for 2040, 90 trees, draft corridor and placeholder tree classes: provisional · Parameters in backend/parameters.py"), encoding="utf-8")
print("html written")
