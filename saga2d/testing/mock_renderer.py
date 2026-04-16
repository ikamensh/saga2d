"""Mock-backend → PIL renderer for visual verification without pyglet.

After 28 iterations of pyglet-cocoa's empty-screens state blocking
subprocess rendering, the /loop needed a different path to see what
a saga2d scene actually looks like. This module consumes the mock
backend's recorded draw operations (``rects`` / ``circles`` /
``images`` / ``texts`` / ``clear_color``) and paints an approximate
PIL image.

It is **not pixel-identical** to the pyglet backend — anti-aliasing,
exact font metrics, and alpha blending will differ. But layout,
palette, composition, and "is the HUD where I expected it?" all
resolve faithfully. Good enough for:

* Visual regression snapshots where pyglet is unavailable.
* Cross-check loops (iter-7's dual-model review) that read PNGs.
* Manual "just save the PNG and look at it" debugging.

Usage::

    from saga2d.testing.mock_renderer import render_mock_scene

    def setup(game):
        game._scene_stack.push(MyScene())
    img = render_mock_scene(setup, resolution=(800, 600))
    img.save("/tmp/preview.png")
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from saga2d import Game


_REPO_ASSETS = Path(__file__).resolve().parents[2] / "assets"
_BUNDLED_FONT = _REPO_ASSETS / "fonts" / "Cinzel.ttf"


def render_mock_scene(
    setup_fn: Callable[[Game], None],
    *,
    resolution: tuple[int, int] = (800, 600),
    tick_count: int = 2,
    theme=None,
) -> Image.Image:
    """Run *setup_fn* inside a mock-backend Game and return a PIL image."""
    game = Game(
        "mock-render",
        resolution=resolution,
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=theme,
    )
    try:
        setup_fn(game)
        for _ in range(tick_count):
            game.tick(dt=1 / 60)
        return _render_backend_state(game, resolution)
    finally:
        game._teardown()


def _render_backend_state(
    game: Game, resolution: tuple[int, int],
) -> Image.Image:
    backend = game.backend
    w, h = resolution

    clear = getattr(backend, "clear_color", None)
    canvas = Image.new("RGBA", (w, h), _rgba(clear) if clear else (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Painter's order: rects → circles → images → text. Not a true
    # z-order (the mock backend doesn't record one) but good enough
    # for layout verification on the example scenes.

    for rect in backend.rects:
        color = _apply_opacity(rect["color"], rect.get("opacity", 1.0))
        x, y, rw, rh = rect["x"], rect["y"], rect["width"], rect["height"]
        if rw <= 0 or rh <= 0:
            continue
        draw.rectangle([(x, y), (x + rw - 1, y + rh - 1)], fill=color)

    for circle in backend.circles:
        color = _apply_opacity(circle["color"], circle.get("opacity", 1.0))
        cx, cy, r = circle["x"], circle["y"], circle["radius"]
        if r <= 0:
            continue
        draw.ellipse(
            [(cx - r, cy - r), (cx + r, cy + r)],
            fill=color,
        )

    for blit in backend.images:
        img = _lookup_blit_image(backend, blit["image"])
        if img is None:
            continue
        bw, bh = blit["width"], blit["height"]
        if bw <= 0 or bh <= 0:
            continue
        resized = img.resize((bw, bh), Image.LANCZOS)
        canvas.alpha_composite(resized, (blit["x"], blit["y"]))

    font_cache: dict[int, ImageFont.FreeTypeFont] = {}
    for text_entry in backend.texts:
        color = text_entry["color"]
        if len(color) == 3:
            color = (*color, 255)
        font_size = text_entry["font_size"]
        font = _get_font(font_cache, font_size)
        x, y = _apply_text_anchor(
            text_entry["text"],
            text_entry["x"], text_entry["y"],
            text_entry.get("anchor_x", "left"),
            text_entry.get("anchor_y", "baseline"),
            font,
        )
        draw.text((x, y), text_entry["text"], fill=color, font=font)

    return canvas


def _rgba(color: tuple[int, ...]) -> tuple[int, int, int, int]:
    if len(color) == 3:
        return (*color, 255)
    return tuple(color)  # type: ignore[return-value]


def _apply_opacity(color, opacity: float) -> tuple[int, int, int, int]:
    rgba = _rgba(color)
    if opacity >= 0.999:
        return rgba
    return (rgba[0], rgba[1], rgba[2], int(rgba[3] * opacity))


def _get_font(cache: dict, size: int) -> ImageFont.FreeTypeFont:
    if size not in cache:
        if _BUNDLED_FONT.exists():
            try:
                cache[size] = ImageFont.truetype(str(_BUNDLED_FONT), size)
                return cache[size]
            except OSError:
                pass
        cache[size] = ImageFont.load_default()
    return cache[size]


def _apply_text_anchor(
    text: str, x: int, y: int, anchor_x: str, anchor_y: str,
    font: ImageFont.FreeTypeFont,
) -> tuple[int, int]:
    """PIL's text() draws with the top-left of the text as origin. The
    saga2d mock backend records anchor intent ("center", "right", etc.);
    translate to a PIL top-left."""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    if anchor_x == "center":
        x -= tw // 2
    elif anchor_x == "right":
        x -= tw
    if anchor_y == "center":
        y -= th // 2
    elif anchor_y == "baseline" or anchor_y == "bottom":
        y -= th
    # anchor_y == "top" → no translation
    return x, y


def _lookup_blit_image(backend, handle) -> Image.Image | None:
    """Resolve a mock-backend image handle back to a PIL image."""
    loaded = getattr(backend, "_loaded_images", None)
    if loaded is None:
        return None
    for path, h in loaded.items():
        if h == handle and Path(path).is_file():
            try:
                return Image.open(path).convert("RGBA")
            except OSError:
                return None
    return None
