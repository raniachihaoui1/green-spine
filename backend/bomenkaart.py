"""Existing canopy from the RIVM Bomenkaart 2022 (10 m cells, % cover by trees > 2.5 m).

The map has no individual trees, species or heights. Each 10 m cell becomes one 'canopy cell':
a disc at the cell centre whose area equals the covered area (cover% x 100 m2), so a 100 % cell
is a disc of r = 5.6 m. Prepared by scripts/clip_bomenkaart.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.ops import unary_union

from . import config as C

FILE = "bomenkaart_2022_fellenoord.npz"


def load_raster(data_dir=C.PROCESSED_DIR):
    p = Path(data_dir) / FILE
    if not p.exists():
        return None
    z = np.load(p)
    return dict(cover=z["cover"].astype(float), x0=float(z["x0"]), y0=float(z["y0"]), cell=float(z["cell"]))


def raster_cells(R, min_cover=C.CANOPY_MIN_COVER) -> pd.DataFrame:
    """All cells with cover >= min_cover, as x, y (cell centre, RD) and cover (%)."""
    rows, cols = np.nonzero(R["cover"] >= min_cover)
    x = R["x0"] + (cols + 0.5) * R["cell"]
    y = R["y0"] - (rows + 0.5) * R["cell"]
    return pd.DataFrame(dict(x=x, y=y, cover=R["cover"][rows, cols]))


def existing_canopy(R, corridor, buildings, road) -> pd.DataFrame:
    """Canopy cells around the corridor, with what the plan does to them.

    in_corridor  cell centre lies inside the corridor (counts for the retention KPI)
    plan_loss    cell centre lies under a planned building or the carriageway: it cannot be kept
    """
    cells = raster_cells(R)
    pts = shapely.points(cells.x.values, cells.y.values)
    near = shapely.contains(corridor.buffer(C.CANOPY_CONTEXT_M), pts)
    cells, pts = cells[near].reset_index(drop=True), pts[near]
    cells["r"] = np.sqrt(cells.cover / 100.0 * R["cell"] ** 2 / np.pi)
    cells["in_corridor"] = shapely.contains(corridor, pts)
    blockers = [g for g, _ in buildings] + ([road] if road is not None and not road.is_empty else [])
    blk = unary_union(blockers) if blockers else None
    cells["plan_loss"] = shapely.contains(blk, pts) if blk is not None and not blk.is_empty else False
    return cells


def baseline_cover_pct(R, corridor) -> float:
    """Exact cell/corridor intersection weighting, including boundary cells."""
    cells, fraction = weighted_cells(R, corridor)
    return float(100 * np.dot(shapely.area(cells), fraction) / corridor.area) if corridor.area else 0.0


def weighted_cells(R, corridor):
    c = raster_cells(R, min_cover=0)
    half = R["cell"] / 2
    x0, y0, x1, y1 = corridor.bounds
    c = c[(c.x + half > x0) & (c.x - half < x1) & (c.y + half > y0) & (c.y - half < y1)]
    cells = shapely.box(c.x - half, c.y - half, c.x + half, c.y + half)
    cells = shapely.intersection(cells, corridor)
    used = shapely.area(cells) > 0
    return cells[used], c.cover.to_numpy()[used] / 100
