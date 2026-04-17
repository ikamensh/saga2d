"""Visual-regression snapshot tests via the iter-38 mock-to-PIL renderer.

:func:`assert_scene_matches_png_snapshot` is the visual counterpart to
:func:`saga2d.testing.assert_scene_matches_snapshot` (iter-15). Where
the JSON snapshot captures *declared structure* (which widgets, which
anchors, which text_styles), the PNG snapshot captures *rendered
output* (pixel-identical mock-to-PIL). The two pair up nicely:

* A structural change that doesn't affect pixels (e.g. renaming a
  style constant to point to an equivalent colour) fails the JSON
  snapshot but not the PNG — flagging a refactor, not a regression.
* A layout shift where widgets re-anchor without restructuring (a
  ``margin`` bump, a ``spacing`` change) fails the PNG but not the
  JSON — flagging a visual change that structure alone couldn't see.
* A combined structural-plus-visual change fails both — the
  unambiguous "new feature shipped" case.

Parallel to Keras's ``model.save_weights()`` / ``load_weights()``:
saga2d now persists a scene's *visual output* for regression testing.

Mock-to-PIL is pixel-deterministic (see
:func:`tests.util.test_mock_renderer`), so a byte-identical PNG
comparison is sufficient — no fuzzy-tolerance matching.

Example usage::

    from saga2d.testing import assert_scene_matches_png_snapshot

    def test_ring_of_pain_visual_regression():
        def setup(game):
            game._scene_stack.push(RingOfPainScene())

        assert_scene_matches_png_snapshot(
            setup, "ring_of_pain",
            snapshot_dir=Path(__file__).parent / "png_snapshots",
            resolution=(800, 600),
            theme=build_theme(),
        )

First run writes the snapshot. Subsequent runs compare. On mismatch,
raises ``AssertionError`` and writes a ``{name}.actual.png`` alongside
the stored snapshot so the diff is inspectable.

Bulk accept new snapshots:

    SAGA2D_UPDATE_PNG_SNAPSHOTS=1 pytest
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from saga2d import Game
from saga2d.testing.mock_renderer import render_mock_scene


_UPDATE_ENV_VAR = "SAGA2D_UPDATE_PNG_SNAPSHOTS"


def _should_update_snapshots() -> bool:
    raw = os.environ.get(_UPDATE_ENV_VAR, "")
    return raw.strip().lower() in ("1", "true", "yes", "on")


def assert_scene_matches_png_snapshot(
    setup_fn: Callable[[Game], None],
    name: str,
    snapshot_dir: Path | str,
    *,
    resolution: tuple[int, int] = (800, 600),
    tick_count: int = 2,
    theme=None,
) -> None:
    """Compare a scene's mock-to-PIL render to a stored PNG snapshot.

    On first run (no snapshot file), writes the rendered PNG and
    returns. On subsequent runs, compares byte-for-byte and raises
    ``AssertionError`` on any divergence — the mock-to-PIL renderer
    is deterministic (``test_render_is_deterministic_for_identical_input``).

    On a failed match, a sibling ``{name}.actual.png`` is written next
    to the stored snapshot so the user can diff the two visually.

    Bulk-accept new snapshots with
    ``SAGA2D_UPDATE_PNG_SNAPSHOTS=1 pytest``.

    Parameters
    ----------
    setup_fn:     Callback receiving the :class:`Game`. Must push a
                  scene or otherwise configure the game before the
                  initial ticks.
    name:         Snapshot file basename (no extension).
    snapshot_dir: Directory holding the snapshot PNGs.
    resolution:   Canvas size in pixels. Bake into the snapshot name
                  if you ever test multiple resolutions.
    tick_count:   Number of ``game.tick(dt=1/60)`` calls before
                  capturing. Default ``2`` matches the iter-38
                  renderer default.
    theme:        Optional :class:`Theme` passed through to the
                  :class:`Game` constructor (so theme-style Labels
                  resolve correctly).
    """
    snapshot_dir = Path(snapshot_dir)
    snapshot_path = snapshot_dir / f"{name}.png"
    image = render_mock_scene(
        setup_fn, resolution=resolution, tick_count=tick_count, theme=theme,
    )

    if _should_update_snapshots():
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        image.save(snapshot_path)
        return

    if not snapshot_path.exists():
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        image.save(snapshot_path)
        return

    # Byte-identical comparison. Mock-to-PIL is deterministic so this
    # is sufficient — no fuzzy tolerance needed.
    from io import BytesIO
    buf = BytesIO()
    image.save(buf, format="PNG")
    actual_bytes = buf.getvalue()
    stored_bytes = snapshot_path.read_bytes()

    if actual_bytes == stored_bytes:
        return

    # Write the actual render alongside the snapshot so the caller
    # can open both and see what changed.
    actual_path = snapshot_dir / f"{name}.actual.png"
    image.save(actual_path)
    raise AssertionError(
        f"PNG snapshot '{name}' does not match {snapshot_path}.\n"
        f"Actual render written to {actual_path}.\n"
        f"Inspect both images to identify the drift. To accept:\n"
        f"  rm {actual_path} {snapshot_path} && pytest        "
        f"(rebuilds this one)\n"
        f"  SAGA2D_UPDATE_PNG_SNAPSHOTS=1 pytest              "
        f"(rebuilds all)"
    )
