"""Schematic scene visualiser — saga2d's equivalent of ``keras.utils.plot_model``.

Keras's ``plot_model(model, show_shapes=True, to_file="m.png")`` renders
the architecture of a neural network to PNG, with each layer labelled
by type and tensor shape. It's the canonical way to understand what
you've actually built before you train it.

:func:`plot_scene` is the same idea for a saga2d scene: feed in a
setup callback, get back a schematic PNG where each UI widget is a
rectangle labelled by type, with bounds annotated. A quick way to
answer "why is the HUD panel in the wrong place?" or "what does this
scene tree look like?" without wading through code.

Two rendering modes:

*   ``mode="schematic"`` (default) — transparent-fill rectangles with
    widget-type labels on top. Shows structure only. Useful for
    layout debugging.
*   ``mode="overlay"`` — the mock-to-PIL render of the scene *plus*
    widget outlines on top. Useful when you want the actual render
    and the widget bounds side-by-side.

Usage::

    from saga2d.testing import plot_scene

    def setup(game):
        game._scene_stack.push(MyScene())

    plot_scene(setup, "/tmp/my_scene.png", resolution=(800, 600))
    plot_scene(setup, "/tmp/my_scene_overlay.png", mode="overlay")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

from PIL import Image, ImageDraw, ImageFont

from saga2d import Game
from saga2d.testing.mock_renderer import _BUNDLED_FONT, render_mock_scene


# Rotating palette so nested widgets can be distinguished at a glance.
_OUTLINE_PALETTE: tuple[tuple[int, int, int, int], ...] = (
    (255, 90, 90, 255),    # red
    (255, 200, 90, 255),   # yellow
    (90, 220, 130, 255),   # green
    (90, 200, 255, 255),   # blue
    (210, 140, 255, 255),  # violet
    (255, 140, 200, 255),  # pink
)


def plot_scene(
    setup_fn: Callable[[Game], None],
    output_path: str | Path,
    *,
    resolution: tuple[int, int] = (800, 600),
    tick_count: int = 2,
    theme: Any = None,
    mode: Literal["schematic", "overlay"] = "schematic",
    label_font_size: int = 11,
    outline_width: int = 1,
) -> Image.Image:
    """Render a scene's widget tree as a labelled PNG schematic.

    Parameters
    ----------
    setup_fn:      Callback that pushes a scene and configures the game.
    output_path:   Where to write the PNG. Pass an empty string to
                   skip writing (the image is still returned).
    resolution:    Canvas size in pixels.
    tick_count:    Frames to tick before capturing layout. The mock-
                   to-PIL default of 2 ticks is enough for layout to
                   settle.
    theme:         Optional :class:`Theme` passed to :class:`Game`.
    mode:          ``"schematic"`` for structure-only; ``"overlay"``
                   for render + outlines.
    label_font_size: Font size for widget-type labels.
    outline_width: Rectangle outline thickness.

    Returns the :class:`PIL.Image.Image` for further processing.
    """
    game = Game(
        "plot-scene",
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
        # Grab the top scene for introspection.
        top = game._scene_stack.top()
        if top is None:
            raise ValueError(
                "plot_scene: no scene on the stack after setup_fn — "
                "the setup callback must push at least one scene."
            )
        data = top.summary_json(include_bounds=True)

        if mode == "overlay":
            # Start from the actual render, then draw outlines on top.
            from saga2d.testing.mock_renderer import _render_backend_state
            canvas = _render_backend_state(game, resolution).copy()
        else:
            # Schematic: dim background, no actual render.
            bg = data.get("background_color", (0, 0, 0, 255))
            if len(bg) == 3:
                bg = (*bg, 255)
            # Dim the bg slightly so outlines are readable against it.
            dim = tuple(int(c * 0.4) for c in bg[:3]) + (bg[3],)
            canvas = Image.new("RGBA", resolution, dim)
    finally:
        game._teardown()

    draw = ImageDraw.Draw(canvas, "RGBA")
    font = _load_label_font(label_font_size)

    if "ui" in data:
        _draw_widget_bounds(
            draw, data["ui"], depth=0,
            outline_width=outline_width, font=font,
        )

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)

    return canvas


def _load_label_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if _BUNDLED_FONT.exists():
        try:
            return ImageFont.truetype(str(_BUNDLED_FONT), size)
        except OSError:
            pass
    return ImageFont.load_default()


def _widget_label(node: dict[str, Any]) -> str:
    """Format one widget node as a one-line schematic label.

    ``Label "Ring of Pain"`` for static text, ``Label ← reactive``
    for callable-bound. Type name alone for containers.
    """
    type_name = node.get("type", "?")
    pieces = [type_name]
    text = node.get("text")
    if isinstance(text, dict):
        if text.get("reactive"):
            pieces.append("← reactive")
        elif "value" in text and text["value"]:
            trimmed = text["value"][:20]
            pieces.append(f'"{trimmed}"')
    value = node.get("value")
    if isinstance(value, dict):
        if value.get("reactive"):
            pieces.append("← reactive")
        else:
            pieces.append(f"= {value.get('value')}")
    return " ".join(pieces)


def _draw_widget_bounds(
    draw: ImageDraw.ImageDraw,
    node: dict[str, Any],
    depth: int,
    outline_width: int,
    font: Any,
) -> None:
    """Recursively draw each node's bounds + label."""
    bounds = node.get("bounds")
    if bounds is not None:
        x, y, w, h = bounds
        if w > 0 and h > 0:
            color = _OUTLINE_PALETTE[depth % len(_OUTLINE_PALETTE)]
            # Rectangle outline. PIL's `draw.rectangle` with width > 1
            # is inset from both sides; for a 1-px line this is moot.
            draw.rectangle(
                [(x, y), (x + w - 1, y + h - 1)],
                outline=color,
                width=outline_width,
            )
            label = _widget_label(node)
            # Put the label at the top-left corner of the widget,
            # inside the bounds — a black background for contrast.
            bbox = font.getbbox(label)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            lx = x + 2
            ly = y + 2
            draw.rectangle(
                [(lx - 1, ly - 1), (lx + lw + 1, ly + lh + 1)],
                fill=(0, 0, 0, 180),
            )
            draw.text((lx, ly), label, fill=color, font=font)

    for child in node.get("children", []):
        _draw_widget_bounds(
            draw, child, depth + 1,
            outline_width=outline_width, font=font,
        )
