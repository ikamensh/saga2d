"""Motion-aware cross-check helpers — a filmstrip of sequential frames.

iter-47's cross-check of the Ring of Pain combat animation surfaced a
limitation of the iter-38/41 single-frame cross-check: a bolt mid-
flight in a still PNG can be read as "duplicated sprites" rather than
"intentional animation." A single cosmetic frame can't express motion
coherence to a vision-only reviewer.

iter-48 fixes this by:

*   :func:`render_scene_sequence` runs a scene setup, captures N frames
    at a caller-specified dt, and returns them as a list of PIL images.
*   :func:`filmstrip` composites N images into a labelled grid (one
    PNG) — the cheapest motion representation that still renders
    inline in a prompt.

The caller feeds the filmstrip to the cross-check prompt with a
motion-aware instruction ("these are sequential frames; describe the
motion") and gets back a review that actually understands the
animation's intent.

For a full animated-GIF approach, PIL's ``save(..., format="GIF",
save_all=True, append_images=...)`` also works — use the sequence
returned by :func:`render_scene_sequence` directly. Filmstrips have
the advantage of rendering inline in API responses and being
inspectable by a human without a GIF player.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from saga2d import Game
from saga2d.testing.mock_renderer import _BUNDLED_FONT, _render_backend_state


def render_scene_sequence(
    setup_fn: Callable[[Game], None],
    *,
    n_frames: int = 4,
    dt_per_frame: float = 1 / 30,
    warmup_ticks: int = 0,
    resolution: tuple[int, int] = (800, 600),
    theme=None,
) -> list[Image.Image]:
    """Render *n_frames* sequential frames of a scene setup.

    Runs ``setup_fn(game)`` once, then captures a frame after every
    ``dt_per_frame`` seconds of simulated time. An optional
    ``warmup_ticks`` lets the caller advance the scene past its
    initial state before starting the sequence (e.g. to skip the
    bolt-spawn frame and land on the bolt mid-flight).

    Unlike :func:`saga2d.testing.mock_renderer.render_mock_scene`,
    this keeps the same :class:`Game` alive for the entire sequence —
    the sprite/emitter state persists across frames so motion is
    captured as intended.

    Parameters
    ----------
    setup_fn:      One-shot scene setup callback.
    n_frames:      Number of frames to capture.
    dt_per_frame:  Simulated time between captures, in seconds. The
                   default 1/30 gives 30 fps sampling.
    warmup_ticks:  Number of ``game.tick(dt_per_frame)`` calls to
                   fire BEFORE the first capture. ``0`` means the
                   first captured frame is immediately post-setup.
    resolution:    Canvas size.
    theme:         Optional :class:`Theme`.
    """
    if n_frames < 1:
        raise ValueError(f"n_frames must be >= 1, got {n_frames}")
    game = Game(
        "filmstrip-render",
        resolution=resolution,
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=theme,
    )
    try:
        setup_fn(game)
        for _ in range(warmup_ticks):
            game.tick(dt=dt_per_frame)
        frames: list[Image.Image] = []
        for _ in range(n_frames):
            game.tick(dt=dt_per_frame)
            frames.append(_render_backend_state(game, resolution))
        return frames
    finally:
        game._teardown()


def filmstrip(
    frames: list[Image.Image],
    *,
    cols: int | None = None,
    pad: int = 8,
    bg_color: tuple[int, int, int, int] = (20, 20, 24, 255),
    label_frames: bool = True,
    label_font_size: int = 14,
) -> Image.Image:
    """Composite *frames* into a single grid-layout PNG.

    The default grid picks the smallest ``cols × rows`` that fits
    all frames with ``cols`` being roughly ``sqrt(n)`` (so 4 frames →
    2×2, 6 frames → 3×2, 9 frames → 3×3).

    When ``label_frames`` is ``True``, each cell shows a ``[k]``
    label in its top-left corner — frame-0 is labelled ``[0]``,
    frame-1 is ``[1]``, etc. Helps a reviewer refer to specific
    frames in the critique.
    """
    if not frames:
        raise ValueError("filmstrip: frames must be non-empty")

    n = len(frames)
    if cols is None:
        import math
        cols = max(1, int(math.ceil(math.sqrt(n))))
    rows = (n + cols - 1) // cols

    fw, fh = frames[0].size
    for f in frames[1:]:
        if f.size != (fw, fh):
            raise ValueError(
                f"filmstrip: all frames must share a size, got {f.size} vs {(fw, fh)}"
            )

    canvas_w = cols * fw + (cols + 1) * pad
    canvas_h = rows * fh + (rows + 1) * pad
    canvas = Image.new("RGBA", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(canvas, "RGBA")

    font = _load_label_font(label_font_size)

    for i, frame in enumerate(frames):
        r, c = divmod(i, cols)
        x = pad + c * (fw + pad)
        y = pad + r * (fh + pad)
        canvas.paste(frame, (x, y))
        if label_frames:
            label = f"[{i}]"
            bbox = font.getbbox(label)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            draw.rectangle(
                [(x + 4, y + 4), (x + 4 + lw + 8, y + 4 + lh + 6)],
                fill=(0, 0, 0, 200),
            )
            draw.text(
                (x + 8, y + 6), label,
                fill=(255, 230, 160, 255), font=font,
            )

    return canvas


def save_sequence_gif(
    frames: list[Image.Image],
    output_path: str | Path,
    *,
    duration_ms: int = 80,
    loop: int = 0,
) -> None:
    """Save a scene sequence as an animated GIF.

    Uses PIL's native ``save_all`` path. Caller's choice between
    filmstrip (one PNG, inline-renderable) and GIF (true animation,
    requires a player). iter-48 ships the filmstrip path as the
    cross-check default; GIF is here for human inspection.
    """
    if not frames:
        raise ValueError("save_sequence_gif: frames must be non-empty")
    # GIF palette: convert RGBA to P mode with transparency index.
    converted = [f.convert("P", palette=Image.Palette.ADAPTIVE) for f in frames]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    converted[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=converted[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True,
    )


def _load_label_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if _BUNDLED_FONT.exists():
        try:
            return ImageFont.truetype(str(_BUNDLED_FONT), size)
        except OSError:
            pass
    return ImageFont.load_default()
