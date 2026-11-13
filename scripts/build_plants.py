"""Turn the tree rows of plant_database.csv into the table the app reads.

Run from the repo root, inside gsenv:

    python scripts/build_plants.py            # writes data/plants_candidates.csv for the team to review
    python scripts/build_plants.py --apply    # adds the approved candidates to data/plants.csv

The database has no "native" flag, no family and no common name, and the project
plants native species only. So nothing is added automatically: in
data/plants_candidates.csv, set native to "yes" and fill in family and common_name
for each species the team approves, then run with --apply.
"""
import argparse
import re
from pathlib import Path

import pandas as pd

DB, PLANTS, CANDIDATES = Path("plant_database.csv"), Path("data/plants.csv"), Path("data/plants_candidates.csv")

# ASSUMPTION (starting values): size class from the largest height the database gives.
MEDIUM_FROM, LARGE_FROM = 10.0, 20.0     # metres
MOISTURE = {"Moisture: Dry (D)": "dry", "Moisture: Moist (M)": "moist", "Moisture: Wet (We)": "wet"}


def max_height(text):
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(text))]
    return max(nums) if nums else None


def size_class(h):
    if h is None:
        return ""
    return "large" if h >= LARGE_FROM else "medium" if h >= MEDIUM_FROM else "small"


def candidates():
    db = pd.read_csv(DB, encoding="latin-1")
    trees = db[db.plant_type.astype(str).str.contains("Tree", case=False)].copy()
    known = pd.read_csv(PLANTS).set_index("species")
    rows = []
    for r in trees.to_dict("records"):
        sp = str(r["species"]).strip()
        h = max_height(r["Plant Height"])
        moist = ";".join(tag for col, tag in MOISTURE.items() if str(r.get(col)).upper() == "TRUE")
        k = known.loc[sp] if sp in known.index else None
        rows.append(dict(
            species=sp,
            common_name=k.common_name if k is not None else "",
            genus=sp.split()[0],
            family=k.family if k is not None else "",
            native=k.native if k is not None else "",
            size_class=k.size_class if k is not None else size_class(h),
            soil_moisture=k.soil_moisture if k is not None else moist,
            in_app="yes" if k is not None else "no",
            db_plant_type=r["plant_type"], db_height=r["Plant Height"], db_size_class=size_class(h), db_moisture=moist))
    return pd.DataFrame(rows).sort_values(["in_app", "species"], ascending=[False, True])


def apply():
    c = pd.read_csv(CANDIDATES, dtype=str).fillna("")
    plants = pd.read_csv(PLANTS, dtype=str).fillna("")
    ok = c[(c.native.str.lower() == "yes") & ~c.species.isin(plants.species)]
    missing = ok[(ok.family == "") | (ok.common_name == "") | (ok.size_class == "") | (ok.soil_moisture == "")]
    if len(missing):
        raise SystemExit("These approved species still miss family, common_name, size_class or soil_moisture:\n  "
                         + "\n  ".join(missing.species))
    if ok.empty:
        print("Nothing to add: no new species is marked native = yes in data/plants_candidates.csv.")
        return
    out = pd.concat([plants, ok[plants.columns]], ignore_index=True)
    out.to_csv(PLANTS, index=False)
    print(f"Added {len(ok)} species; data/plants.csv now has {len(out)}.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="add approved candidates to data/plants.csv")
    if ap.parse_args().apply:
        apply()
    else:
        c = candidates()
        c.to_csv(CANDIDATES, index=False)
        print(f"Wrote {CANDIDATES}: {len(c)} tree species, {(c.in_app == 'yes').sum()} already in the app, "
              f"{(c.in_app == 'no').sum()} to review.")
