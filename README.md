# green-spine
Evidence-led greening for Fellenoord, Eindhoven: respect the masterplan framework,
screen additional planting and measure its added value.

https://miro.com/app/board/uXjVEOFK7kA=/

https://docs.google.com/presentation/d/1jpzjV2JB2xp1cfWjxQWiUZYx_7qPBuOxiP1Z4genHXk/edit?slide=id.p#slide=id.p

## Setup

### What you need to install

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.13 (tested on 3.13.14) | [python.org/downloads](https://www.python.org/downloads/) — tick "Add python.exe to PATH" |
| pip | 26.3 | ships with Python; upgraded in step 2 |
| Git | any recent | to clone the repo |

Python packages (installed into the environment by the steps below):

| Package | Minimum ([requirements.txt](requirements.txt)) | Tested version ([requirements-lock.txt](requirements-lock.txt)) |
|---------|---------|---------|
| streamlit | >=1.33 | 1.67.0 |
| pydeck | >=0.8 | 0.9.3 |
| numpy | any | 2.5.4 |
| pandas | any | 3.1.1 |
| shapely | >=2.1 | 2.2.0 |
| pyproj | any | 3.8.0 |

### Create the `gsenv` environment

The `gsenv/` folder is not committed (it is in `.gitignore`) because a virtual environment only works on the machine that created it. Instead, everyone builds an identical copy once from `requirements-lock.txt`, which pins the exact version of every package.

**Quick way** — run the setup script from the repo root:

```powershell
.\setup_gsenv.ps1        # Windows (PowerShell)
```

```bash
bash setup_gsenv.sh      # macOS / Linux
```

**Manual way** — the same steps by hand:

**Windows (PowerShell)**

```powershell
py -3.13 -m venv gsenv
.\gsenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-lock.txt
```

If activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

**macOS / Linux**

```bash
python3.13 -m venv gsenv
source gsenv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-lock.txt
```

Use `requirements-lock.txt` for the exact tested versions, or `requirements.txt` for the latest compatible ones.

### Run the app

With `gsenv` activated (your prompt shows `(gsenv)`):

```bash
streamlit run app.py
```

The app opens at http://localhost:8501. Stop it with `Ctrl+C`; leave the environment with `deactivate`.

### Assessment workflow

Choose **Existing**, **Masterplan** or **Green Spine**. Until a masterplan package
is supplied, Green Spine is explicitly an exploration of today's layout.
Masterplan results and masterplan deltas remain unavailable.

See [masterplan import](docs/MASTERPLAN_IMPORT.md) for the required source-labelled
GeoJSON package, and [data and metrics](docs/DATA_AND_METRICS.md) for calculations,
assumptions and unassessed policy checks.

Planting is conditional: soil compatibility is not construction approval.
Built shelters are optional additions, off by default. Strategies describe
priorities rather than claiming optimal cooling, ecological connectivity or cost.

### Presentation exports

The dashboard exports assessment JSON, planting and cell-decision CSVs, interactive
HTML, and a Blender scene-data JSON (prepare it in **Presentation & exports**).

For physically based, high-resolution illustrative renders, install the standalone
[Blender 4.5 LTS](https://www.blender.org/download/lts/) application. It is optional;
the dashboard does not require Blender or extra Python dependencies.

```powershell
blender --background --python scripts\render_scene.py -- --scene green_spine_scene.json --output green_spine
```

This writes a self-contained `.blend` scene and a 2560 x 1440 denoised Cycles PNG.
Both retain an indicative/source label. Buildings are source footprint extrusions;
materials and procedural trees are illustrations, not surveyed architectural
detail. Existing and proposed renders use the same camera and solar position.
HTML viewing needs internet for its browser libraries and basemap.

### Tests

```powershell
.\gsenv\Scripts\python.exe -m unittest discover -s tests -v
```

The locked Shapely version already supports constrained triangulation used by the
renderer. No package was added to the dashboard runtime.

### Data

The real Fellenoord layers are already in `data/processed/`; raw inputs are in `data/raw/`. To download them again, or to rebuild them around a corridor line you drew yourself (one line, for example from geojson.io):

```bash
python scripts/fetch_data.py
python scripts/fetch_data.py --centreline my_line.geojson
```

Sources, licences and assumptions are listed in [data/SOURCES.md](data/SOURCES.md). The download needs internet; if OpenStreetMap is busy the script retries and may need a second run.

To add tree species from `data/raw/plants/plant_database.csv`: run `python scripts/build_plants.py`, mark the native ones in `data/processed/plants_candidates.csv`, then run `python scripts/build_plants.py --apply`.

To rebuild the soil-compatible plant list from the BRO boreholes: `python -m backend.soil`.

Project scope, method and status: [docs/PROJECT_SCOPE.md](docs/PROJECT_SCOPE.md).

### Adding a package

```bash
pip install <package>
pip freeze > requirements-lock.txt
```

Also add it to `requirements.txt` so the others get it.
