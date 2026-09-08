# Warband procedural art — 2026-09-08

Generated with `uv run python tools/verify_warband_art.py
docs/evidence/warband-art-2026-09-08` through the real pyglet backend.

Inspected the building and unit catalogs, all seasonal tree catalogs, crystal
deposits, the settlement at normal scale, and axe contact in the lumber camp.
The animated GIF records three workers executing actual harvest orders in
different directions; the verifier asserts that all four chopping poses occur.

- `01_buildings.png`: nine purpose-specific building designs.
- `02_units.png`, `03_workers.png`: seven unit roles, actions, chopping and cargo.
- `04_*`: twenty trees and twenty crystal rocks in each of three map themes.
- `05_crystal_mines.png`: twenty gold outcrop variants.
- `06_*`, `07_*`: normal/close settlement views using the actual MapView and HUD.
- `08_*`, `09_*`: working lumber camp, swing poses, contact chips and animation.

Validation: **240 tests passed** with `uv run python -m pytest tests/warband
tests/framework/test_render3d.py -q`. Integration regressions cover stable
forest/mine variants after loading, the harvesting-to-carry transition, pause
behavior, and incremental image warming. A separate image digest check found
twenty different rendered images in every resource bank (140 total).

These are local art and rendering checks, not a multiplayer or long-match soak.
