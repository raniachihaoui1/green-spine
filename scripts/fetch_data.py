"""Download free public data for the corridor and write the layers the app reads.

Run from the repo root, inside gsenv:

    python scripts/fetch_data.py                               # draft corridor from OpenStreetMap
    python scripts/fetch_data.py --centreline my_line.geojson  # use a line drawn by the team

The --centreline file holds one LineString, in WGS84 (for example drawn at
geojson.io) or in EPSG:28992; the script detects which. Everything written to
data/ is in EPSG:28992. Sources and counts are recorded in data/SOURCES.md.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.ops import polygonize, unary_union

UA = "data-fetch-script/1.0"
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]
BAG3D_WFS = "https://data.3dbag.nl/api/BAG3D/wfs"
TREES_API = "https://data.eindhoven.nl/api/explore/v2.1/catalog/datasets/bomen/exports/geojson"

# Where to look for the draft route: the Fellenoord road and its continuation to the Dommel.
SEARCH_BBOX = (51.4405, 5.4690, 51.4480, 5.4910)          # south, west, north, east
ROUTE_NAMES = "^(Fellenoord|Professor Doctor Dorgelolaan)$"

# ASSUMPTIONS (starting values, not surveyed):
HALF_WIDTH = 30.0             # corridor reaches this far either side of the centreline, metres
LANE_WIDTH = 3.2              # metres per traffic lane
ROAD_HALF = dict(secondary=3.5, secondary_link=3.0, primary=3.5, tertiary=3.0, unclassified=3.0,
                 residential=2.75, service=2.0, busway=3.5, cycleway=1.5)   # half carriageway width by road type
RIVER_HALF = 6.0              # the Dommel is removed from the corridor this far either side of its line
WET_REACH = 30.0              # ground within this distance of the Dommel counts as wet
CROWN_PER_HEIGHT = 0.3        # crown radius = this x tree height (crown about 0.6 x height wide)
SHADOW_MARGIN = 400.0         # buildings this far outside the corridor are still fetched (long low-sun shadows)

to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True).transform
to_wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True).transform


def transform(func, geom):
    """Reproject a geometry with a pyproj transform function."""
    return shapely.transform(geom, lambda xy: np.column_stack(func(xy[:, 0], xy[:, 1])))


def http(url, data=None, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:            # network errors are retried, then reported
            last = e
            time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"Download failed: {url.split('?')[0]} ({last})")


def overpass(query):
    body = urllib.parse.urlencode({"data": query}).encode()
    last = None
    # The public servers are often at capacity (HTTP 502/429/504): go round them
    # with a growing pause, as their own error message asks.
    order = [0, 0, 1, 0, 0, 2, 0, 0]          # mostly the main server; a mirror now and then
    for attempt in range(8):
        host = OVERPASS[order[attempt]]
        try:
            req = urllib.request.Request(host, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=75) as r:
                return json.loads(r.read())["elements"]
        except Exception as e:
            last = f"{host.split('/')[2]}: {e}"
            time.sleep(min(60, 5 * (attempt + 1)))
    raise RuntimeError(f"OpenStreetMap download failed after 8 attempts ({last}). The servers are busy; run the script again in a few minutes.")


def way_line(el):
    return transform(to_rd, LineString([(p["lon"], p["lat"]) for p in el["geometry"]]))


def wgs_bbox(geom, margin):
    minx, miny, maxx, maxy = geom.buffer(margin).bounds
    w, s = to_wgs(minx, miny)
    e, n = to_wgs(maxx, maxy)
    return s, w, n, e


def write(path, feats):
    fc = dict(type="FeatureCollection", name=path.stem,
              crs=dict(type="name", properties=dict(name="urn:ogc:def:crs:EPSG::28992")),
              features=[dict(type="Feature", properties=p, geometry=mapping(g)) for g, p in feats])
    path.write_text(json.dumps(fc), encoding="utf-8")


def parts(geom):
    if geom.is_empty:
        return []
    return [g for g in (geom.geoms if hasattr(geom, "geoms") else [geom]) if g.geom_type == "Polygon"]


# ---------- corridor ----------
def draft_centreline():
    """Mid-line of the Fellenoord / Dorgelolaan carriageways, from the west end to the Dommel."""
    s, w, n, e = SEARCH_BBOX
    els = overpass(f'[out:json][timeout:60];(way["highway"~"^(secondary|primary|tertiary)$"]["name"~"{ROUTE_NAMES}"]'
                   f'({s},{w},{n},{e});way["waterway"="river"]({s},{w},{n},{e}););out tags geom;')
    roads = [way_line(x) for x in els if "highway" in x["tags"]]
    river = unary_union([way_line(x) for x in els if "waterway" in x["tags"]])
    if not roads or river.is_empty:
        raise RuntimeError("Could not find the Fellenoord road or the Dommel in OpenStreetMap.")
    cross = unary_union(roads).intersection(river)
    if cross.is_empty:
        raise RuntimeError("The road does not reach the Dommel in the search area.")
    x_end = min(p.x for p in (cross.geoms if hasattr(cross, "geoms") else [cross]))
    # Both carriageways are sampled every 5 m; averaging the samples in 25 m slices
    # along the west-east run of the road gives the line between them.
    pts = np.array([(p.x, p.y) for r in roads for p in
                    shapely.line_interpolate_point(r, np.arange(0, r.length, 5.0))])
    pts = pts[pts[:, 0] <= x_end]
    bins = np.floor((pts[:, 0] - pts[:, 0].min()) / 25.0).astype(int)
    mid = [pts[bins == b].mean(axis=0) for b in np.unique(bins)]
    return LineString(mid).simplify(2.0), river


def read_centreline(path):
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    geoms = [shape(f.get("geometry", f)) for f in feats]
    lines = [g for g in geoms if g.geom_type == "LineString"]
    if len(lines) != 1:
        raise RuntimeError(f"{path} must contain exactly one LineString; found {len(lines)}.")
    line = lines[0]
    if abs(line.coords[0][0]) <= 180:            # degrees, so WGS84
        line = transform(to_rd, line)
    return line


# ---------- layers ----------
def fetch_osm_layers(corridor):
    s, w, n, e = wgs_bbox(corridor, 60)
    bb = f"({s},{w},{n},{e})"
    green = ('["landuse"~"^(grass|village_green|meadow|forest|flowerbed|recreation_ground)$"]',
             '["leisure"~"^(park|garden)$"]', '["natural"~"^(scrub|wood|grassland|heath)$"]')
    q = ('[out:json][timeout:90];(way["highway"]' + bb + ';way["waterway"="river"]' + bb + ';way["natural"="water"]' + bb + ';'
         + "".join(f"way{g}{bb};relation{g}{bb};" for g in green) + ');out tags geom;')
    els = overpass(q)
    roads, rivers, water, unpaved = [], [], [], []
    for el in els:
        t = el.get("tags", {})
        if el["type"] == "way" and "geometry" in el:
            line = way_line(el)
            if t.get("highway") in ROAD_HALF:
                half = ROAD_HALF[t["highway"]]
                try:
                    if t["highway"] != "cycleway" and "lanes" in t:
                        half = max(half, float(t["lanes"]) * LANE_WIDTH / 2)
                except ValueError:
                    pass
                roads.append(line.buffer(half, cap_style="flat"))
            elif t.get("waterway") == "river":
                rivers.append(line)
            elif "highway" not in t and line.is_ring and len(line.coords) >= 4:
                poly = Polygon(line.coords).buffer(0)
                (water if t.get("natural") == "water" else unpaved).append(poly)
        elif el["type"] == "relation":
            outer = [transform(to_rd, LineString([(p["lon"], p["lat"]) for p in m["geometry"]]))
                     for m in el.get("members", []) if m.get("role") == "outer" and "geometry" in m]
            unpaved.extend(polygonize(unary_union(outer)) if outer else [])
    return unary_union(roads), unary_union(rivers), unary_union(water), unary_union(unpaved)


def fetch_buildings(corridor):
    minx, miny, maxx, maxy = corridor.buffer(SHADOW_MARGIN).bounds
    out, start, page = [], 0, 1000
    while True:
        qs = urllib.parse.urlencode(dict(
            service="WFS", version="2.0.0", request="GetFeature", typeNames="BAG3D:lod12",
            outputFormat="application/json", srsName="EPSG:28992", count=page, startIndex=start,
            bbox=f"{minx:.0f},{miny:.0f},{maxx:.0f},{maxy:.0f}"))
        feats = json.loads(http(f"{BAG3D_WFS}?{qs}"))["features"]
        for f in feats:
            p = f["properties"]
            top, ground = p.get("b3_h_70p"), p.get("b3_h_maaiveld")
            if top is None or ground is None or not f.get("geometry"):
                continue
            h = float(top) - float(ground)          # roof height (70th percentile) above ground level
            if h < 2.0:
                continue
            for poly in parts(shape(f["geometry"]).buffer(0)):
                out.append((poly, dict(height=round(h, 1), bag_id=p.get("identificatie"))))
        if len(feats) < page:
            return out
        start += page


def fetch_trees(corridor):
    s, w, n, e = wgs_bbox(corridor, 40)
    qs = urllib.parse.urlencode(dict(where=f"in_bbox(geo_point_2d, {s}, {w}, {n}, {e})", limit=-1))
    feats = json.loads(http(f"{TREES_API}?{qs}"))["features"]
    area, out = corridor.buffer(40), []
    for f in feats:
        if not f.get("geometry"):
            continue
        pt = Point(to_rd(*f["geometry"]["coordinates"][:2]))
        if not area.contains(pt):
            continue
        p = f["properties"]
        nums = [float(v) for v in "".join(c if c.isdigit() or c == "." else " " for c in str(p.get("hoogte") or "")).split()]
        height = sum(nums) / len(nums) if nums else 8.0       # height class such as "6-9" -> 7.5 m
        r = float(np.clip(CROWN_PER_HEIGHT * height, 1.5, 8.0))
        out.append((pt, dict(crown_radius=round(r, 1), height_class=p.get("hoogte"),
                             species=p.get("boomsoort"), planted=p.get("plantjaar"))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--centreline", help="GeoJSON with one LineString drawn by the team (WGS84 or EPSG:28992)")
    ap.add_argument("--half-width", type=float, default=HALF_WIDTH, help="corridor half width in metres")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(exist_ok=True)

    if a.centreline:
        line, origin = read_centreline(a.centreline), f"drawn by the team ({Path(a.centreline).name})"
    else:
        (line, _), origin = draft_centreline(), "DRAFT: mid-line of the Fellenoord / Dorgelolaan carriageways from OpenStreetMap"
    print(f"Centreline: {line.length:.0f} m, {origin}")

    corridor = line.buffer(a.half_width, cap_style="flat")
    road, river, water, unpaved = fetch_osm_layers(corridor)
    wet_water = unary_union([river.buffer(RIVER_HALF), water])
    corridor = max(parts(corridor.difference(wet_water)), key=lambda p: p.area)     # keep the land side
    print(f"Corridor: {corridor.area / 1e4:.2f} ha")
    buildings = fetch_buildings(corridor)
    print(f"Buildings: {len(buildings)} parts")
    trees = fetch_trees(corridor)
    print(f"Existing trees: {len(trees)}")

    road = road.intersection(corridor.buffer(5))
    unpaved = unpaved.intersection(corridor).difference(road)
    wet = river.buffer(WET_REACH).intersection(corridor)
    write(out / "centreline.geojson", [(line, dict(origin=origin))])
    write(out / "corridor.geojson", [(corridor, dict(half_width_m=a.half_width))])
    write(out / "buildings.geojson", buildings)
    write(out / "road.geojson", [(p, {}) for p in parts(road)])
    write(out / "unpaved.geojson", [(p, {}) for p in parts(unpaved)])
    write(out / "trees_existing.geojson", trees)
    write(out / "wet_zone.geojson", [(p, {}) for p in parts(wet)])

    in_corr = sum(corridor.contains(p) for p, _ in trees)
    (out / "SOURCES.md").write_text(f"""# Data sources

Written by `scripts/fetch_data.py` on {dt.date.today().isoformat()}. All layers are in EPSG:28992.

| File | Source | Licence | Content |
|---|---|---|---|
| `centreline.geojson` | {origin} | {'OpenStreetMap, ODbL' if not a.centreline else 'team'} | {line.length:.0f} m |
| `corridor.geojson` | Centreline widened by {a.half_width:.0f} m each side, minus the Dommel | derived | {corridor.area / 1e4:.2f} ha |
| `buildings.geojson` | 3D BAG, layer lod12 (https://3dbag.nl) | CC BY 4.0 | {len(buildings)} building parts; `height` = roof (70th percentile) minus ground level |
| `trees_existing.geojson` | Eindhoven open data, "bomen" (https://data.eindhoven.nl/explore/dataset/bomen/) | see dataset page | {len(trees)} trees within 40 m of the corridor, {in_corr} inside it |
| `road.geojson` | OpenStreetMap roads and cycleways (https://www.openstreetmap.org) | ODbL | {road.area:.0f} m² |
| `unpaved.geojson` | OpenStreetMap grass, parks, gardens, scrub, woodland | ODbL | {unpaved.area:.0f} m² |
| `wet_zone.geojson` | Ground within {WET_REACH:.0f} m of the Dommel (OpenStreetMap) | ODbL | {wet.area:.0f} m² |

## Assumptions in these layers

These are starting values set in `scripts/fetch_data.py`, not survey data.

- The corridor is the centreline widened by {a.half_width:.0f} m each side.
- Roads are OpenStreetMap centre lines widened by road type ({LANE_WIDTH} m per lane where lanes are tagged). They show today's layout, not the planned narrower boulevard.
- Footpaths are not blocked; they count as paved ground that needs engineered soil.
- Tree crown radius is {CROWN_PER_HEIGHT} x the middle of the municipal height class (for example "6-9" m gives {CROWN_PER_HEIGHT * 7.5:.1f} m), limited to 1.5 to 8 m. The dataset has no crown size.
- Building height is one value per building part (flat extrusion).
- No utilities layer: underground cables and pipes are not included.
- Soil is not measured: OpenStreetMap green areas count as open ground, everything else as paved.
""", encoding="utf-8")
    print(f"Wrote 7 layers and SOURCES.md to {out}/")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")
