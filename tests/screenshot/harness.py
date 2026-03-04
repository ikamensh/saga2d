"""Screenshot testing harness — render scenes offscreen and compare to golden PNGs.

Two public functions:

* ``render_scene(setup_fn, ...)`` — create a headless pyglet Game, set up
  sprites/scenes via *setup_fn*, tick, capture, clean up, return PIL Image.
* ``assert_screenshot(image, name, ...)`` — compare against a golden PNG in
  ``tests/screenshot/golden/``.  Auto-creates the golden on first run.

Usage in a test::

    from tests.screenshot.harness import render_scene, assert_screenshot

    def test_tree_sprite():
        def setup(game):
            img = game.assets.image("tree")
            Sprite(img)
            game.tick(dt=0.016)

        image = render_scene(setup, tick_count=1)
        assert_screenshot(image, "tree_sprite")
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image

from saga2d import Game

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------
_HARNESS_DIR = Path(__file__).resolve().parent
GOLDEN_DIR = _HARNESS_DIR / "golden"
OUTPUT_DIR = _HARNESS_DIR / "output"


# ---------------------------------------------------------------------------
# render_scene
# ---------------------------------------------------------------------------

def render_scene(
    setup_fn: Callable[[Game], None],
    *,
    tick_count: int = 1,
    resolution: tuple[int, int] = (320, 240),
) -> Image.Image:
    """Render a scene offscreen and return a PIL Image of the result.

    1. Creates a real pyglet ``Game`` with ``visible=False``.
    2. Calls ``setup_fn(game)`` — the caller pushes scenes, creates sprites,
       etc.
    3. Ticks *tick_count* frames (``dt=1/60``).
    4. Captures the framebuffer via ``game.backend.capture_frame()``.
    5. Tears down the backend and restores module-level state.

    Args:
        setup_fn:    Receives the ``Game`` instance.  Set up sprites, push
                     scenes, etc.  May call ``game.tick()`` itself if it
                     needs to advance time during setup.
        tick_count:  Number of ``game.tick(dt=1/60)`` calls *after*
                     ``setup_fn`` returns.  Default 1 — enough to render
                     one frame so ``capture_frame()`` has pixels to read.
        resolution:  ``(width, height)`` of the offscreen window.

    Returns:
        A Pillow ``Image.Image`` (RGBA) of the captured framebuffer.
    """
    import saga2d.rendering.sprite as _sprite_mod
    import saga2d.util.tween as _tween_mod

    old_game = _sprite_mod._current_game
    old_tween = _tween_mod._tween_manager
    game = None

    try:
        game = Game(
            "Screenshot Test",
            resolution=resolution,
            fullscreen=False,
            backend="pyglet",
            visible=False,
        )

        setup_fn(game)

        dt = 1.0 / 60.0
        for _ in range(tick_count):
            game.tick(dt=dt)

        # capture_frame() reads from GL_FRONT_LEFT — the frame just
        # displayed by end_frame()/flip().  The tick above has already
        # done begin_frame → draw → batch.draw → flip, so the front
        # buffer contains the rendered scene.
        image = game.backend.capture_frame()

        return image
    finally:
        # Tear down the pyglet window (only if Game() succeeded).
        if game is not None:
            game._backend.quit()
        # Restore module-level singletons so other tests aren't polluted.
        _sprite_mod._current_game = old_game
        _tween_mod._tween_manager = old_tween


# ---------------------------------------------------------------------------
# assert_screenshot
# ---------------------------------------------------------------------------

def assert_screenshot(
    image: Image.Image,
    name: str,
    *,
    max_diff_percent: float = 1.0,
    max_pixel_distance: int = 10,
) -> None:
    """Compare *image* against the golden PNG ``tests/screenshot/golden/{name}.png``.

    If the golden does not exist, *image* is saved as the new golden and the
    assertion **passes** (first-run bootstrapping).

    If the golden exists, a per-pixel comparison is performed:

    * A pixel "differs" when any RGBA channel deviates by more than
      *max_pixel_distance* (0–255 scale).
    * The assertion fails when the percentage of differing pixels exceeds
      *max_diff_percent*.

    On failure, two diagnostic files are written to
    ``tests/screenshot/output/``:

    * ``{name}_actual.png``  — what the test produced.
    * ``{name}_diff.png``    — red overlay highlighting differing pixels.

    Args:
        image:              The captured framebuffer image.
        name:               Basename (no extension) used for the golden file
                            and any failure artifacts.
        max_diff_percent:   Maximum percentage (0–100) of pixels that may
                            differ.  Default 1.0%.
        max_pixel_distance: Per-channel tolerance (0–255).  Pixels within
                            this distance are considered matching.
                            Default 10.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    golden_path = GOLDEN_DIR / f"{name}.png"

    # --- First run: save as new golden, pass ---
    if not golden_path.exists():
        image.save(golden_path)
        return

    # --- Load golden and compare ---
    golden = Image.open(golden_path).convert("RGBA")

    # Size mismatch is always a hard failure.
    if image.size != golden.size:
        _save_failure_artifacts(image, golden, name)
        raise AssertionError(
            f"Screenshot '{name}' size mismatch: "
            f"actual {image.size} vs golden {golden.size}"
        )

    actual_data = image.tobytes()
    golden_data = golden.tobytes()

    width, height = image.size
    total_pixels = width * height

    diff_count = 0
    # Build a diff image: transparent where matching, red where different.
    diff_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    diff_pixels = diff_img.load()

    # Walk every pixel (4 bytes each: R, G, B, A).
    for y in range(height):
        row_offset = y * width * 4
        for x in range(width):
            px_offset = row_offset + x * 4
            r_a, g_a, b_a, a_a = actual_data[px_offset : px_offset + 4]
            r_g, g_g, b_g, a_g = golden_data[px_offset : px_offset + 4]

            if (
                abs(r_a - r_g) > max_pixel_distance
                or abs(g_a - g_g) > max_pixel_distance
                or abs(b_a - b_g) > max_pixel_distance
                or abs(a_a - a_g) > max_pixel_distance
            ):
                diff_count += 1
                diff_pixels[x, y] = (255, 0, 0, 180)

    diff_percent = (diff_count / total_pixels) * 100.0

    if diff_percent > max_diff_percent:
        _save_failure_artifacts(image, diff_img, name)
        raise AssertionError(
            f"Screenshot '{name}' differs from golden: "
            f"{diff_percent:.2f}% pixels differ "
            f"(threshold {max_diff_percent}%, "
            f"tolerance {max_pixel_distance}/255). "
            f"See tests/screenshot/output/{name}_actual.png and "
            f"tests/screenshot/output/{name}_diff.png"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_failure_artifacts(
    actual: Image.Image,
    diff_or_golden: Image.Image,
    name: str,
) -> None:
    """Write actual and diff images to the output directory."""
    actual.save(OUTPUT_DIR / f"{name}_actual.png")
    diff_or_golden.save(OUTPUT_DIR / f"{name}_diff.png")
