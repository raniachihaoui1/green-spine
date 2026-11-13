# Vegetation models

Low-poly 3D symbols for the Green Spine map, made by `scripts/make_vegetation_models.py` (needs `pip install trimesh`).
They show a size class, not a species. Reference sizes are in `models.json`; `backend/view.py` reads them to scale each model to the tree's crown radius.

| Model | Height | Width | Used on the map for |
|---|---|---|---|
| `large_tree` | 20 m | 12 m crown | new large and medium trees, existing RIVM canopy |
| `small_tree` | 8 m | 5 m crown | new small trees |
| `medium_bush` | 2 m | 3 m | shrubs on open ground (indicative) |
| `low_vegetation` | 0.5 m | 2 × 2 m | low vegetation on open ground (indicative) |

- `<name>.obj`: Z-up, metres, origin at the base centre (Rhino).
- `<name>.glb`: glTF, Y-up, coloured materials (Blender, viewers).
- `<name>_foliage.glb`, `<name>_trunk.glb`: white parts for the dashboard. deck.gl's ScenegraphLayer ignores vertex colours, so the app colours each part with `get_color` (kept / cleared / plant now / engineered soil). Orientation `[0, 0, 90]` stands them upright.
