"""Clip the national RIVM 'Bomenkaart 2022' (10 m, % tree cover > 2.5 m) to the Fellenoord scope.

One-off preparation step; the app itself only needs numpy to read the output.
Needs rasterio (not in requirements.txt):  pip install rasterio

    python scripts/clip_bomenkaart.py path/to/rivm_20231221_bomenkaart_2022.tif
    python scripts/clip_bomenkaart.py <tif> --corridor data/processed/corridor.geojson --margin 300

Without --corridor it clips the default scope box (Kennedyplein to the Dommel, plus margin).
Writes to data/processed/:
    bomenkaart_2022_fellenoord.tif   clipped GeoTIFF (EPSG:28992), for QGIS
    bomenkaart_2022_fellenoord.npz   same grid as numpy array, read by the app
    scope_fellenoord.geojson         the clip box
Source: Atlas Natuurlijk Kapitaal (ANK), http://www.atlasnatuurlijkkapitaal.nl
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds

# Fellenoord, Kennedyplein to the Dommel valley, EPSG:28992 (drawn by eye: the corridor is not final)
SCOPE_BOX = (161000.0, 383600.0, 162700.0, 384800.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--corridor", help="GeoJSON polygon in EPSG:28992; clip around its bounds")
    ap.add_argument("--margin", type=float, default=250.0, help="margin around the scope in metres")
    ap.add_argument("--out", default="data/processed")
    a = ap.parse_args()

    if a.corridor:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        gj = json.loads(Path(a.corridor).read_text(encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        bounds = unary_union([shape(f["geometry"]) for f in feats]).bounds
    else:
        bounds = SCOPE_BOX
    m = a.margin
    box = (np.floor((bounds[0] - m) / 10) * 10, np.floor((bounds[1] - m) / 10) * 10,
           np.ceil((bounds[2] + m) / 10) * 10, np.ceil((bounds[3] + m) / 10) * 10)

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    with rasterio.open(a.tif) as src:
        win = from_bounds(*box, src.transform)
        arr = src.read(1, window=win)
        tr = src.window_transform(win)
        prof = src.profile.copy()
    prof.update(width=arr.shape[1], height=arr.shape[0], transform=tr, blockxsize=16, blockysize=16)
    with rasterio.open(out / "bomenkaart_2022_fellenoord.tif", "w", **prof) as dst:
        dst.write(arr, 1)

    cover = np.where(arr < 0, 0, arr).astype(np.uint8)   # nodata (-9999) means no trees
    np.savez_compressed(out / "bomenkaart_2022_fellenoord.npz", cover=cover,
                        x0=tr.c, y0=tr.f, cell=tr.a, crs="EPSG:28992",
                        source="RIVM / Atlas Natuurlijk Kapitaal, Bomenkaart 2022 (AHN4 + CIR 2022)")
    x0, y0, x1, y1 = box
    (out / "scope_fellenoord.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": [{"type": "Feature", "properties": {"name": "Fellenoord scope + margin", "margin_m": m},
                      "geometry": {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}]},
        indent=1), encoding="utf-8")
    print(f"clip {box}  shape {cover.shape}  mean cover {cover.mean():.1f}%  "
          f"cells >=30%: {(cover >= 30).sum()}  canopy area {cover.sum():.0f} m2")


if __name__ == "__main__":
    main()
