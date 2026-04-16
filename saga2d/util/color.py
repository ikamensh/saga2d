"""Small colour-math utilities shared across widgets.

These operate on RGBA tuples in the 0-255 range — the same format every
backend and style field uses. Extracted from four identical copies that
used to live in ``saga2d.ui.widgets`` (ProgressBar, List, Tooltip,
TabGroup).
"""

from __future__ import annotations

Color = tuple[int, int, int, int]


def lighten(color: Color, factor: float) -> Color:
    """Return *color* with its RGB channels multiplied by *factor*.

    ``factor == 1.0`` is a no-op; ``> 1.0`` lightens; ``< 1.0`` darkens.
    Alpha is preserved. Channels are clamped to 0-255.

    Examples::

        lighten((100, 100, 100, 255), 1.5)  # -> (150, 150, 150, 255)
        lighten((200, 200, 200, 255), 2.0)  # -> (255, 255, 255, 255) clamped
        lighten((50, 50, 50, 128),  0.5)    # -> (25, 25, 25, 128) alpha kept
    """
    r, g, b, a = color
    return (
        max(0, min(255, int(r * factor))),
        max(0, min(255, int(g * factor))),
        max(0, min(255, int(b * factor))),
        a,
    )
