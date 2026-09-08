# Forest ground and worker body motion

Native pyglet captures from the real Warband MapView, with procedural assets
registered through the gameplay path. Rendered at 1280×800 logical resolution
on a 2× display, zoomed to inspect the forest edge.

```sh
uv run python -m pytest tests/warband/test_view.py tests/framework/test_render3d.py -q
uv run python tools/verify_warband_forest.py docs/evidence/warband-forest-2026-09-08
```

Result: **26 tests passed** and the native verifier completed successfully.
The new ground regression failed in all six theme/scale combinations before
the fix and passed after it. It compares ground pixels before and after
felling trees, including chunk edges. The live verifier observes all four
chopping poses, then waits for the harvested tree to disappear and the worker
to carry lumber.

Visually inspected `summer-forest.png`, `winter-forest.png`,
`wasteland-forest.png`, `summer-cleared.png`, `chop1.png` and `chop3.png`:

- The ground flows through forests without dark tree-tile squares.
- Narrow firs and bare trees have faint, feathered contact shade.
- The felled trees leave matching ground, with their shading removed.
- Workers lean back during wind-up and forward at impact, with planted feet
  and gripping hands following the axe in three facing directions.

`workers-chopping.gif` is a cropped native frame sequence of the same live
harvest; the four `chop*.png` files preserve individual poses.
