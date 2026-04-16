"""Procedural position helpers for world-space layouts.

Game UIs routinely need N things arranged in a ring (radial menus, Ring
of Pain / Slay the Spire map nodes, turn-order wheels), a grid (inventory,
spell books, tile selection), or a line (card hands, status-effect rows).
These are pure math — no framework entanglement — but every game ends up
writing its own cos/sin loop. These helpers are the saga2d equivalent of
``keras.Sequential``: the caller says *what* they want, not *where every
pixel goes*.

Complement to :meth:`saga2d.ui.layout.compute_flow_layout`, which handles
UI-tree children. The helpers here return raw ``(x, y)`` tuples in
logical screen or world pixels; game code applies them to sprites,
cards, or draw calls.
"""

from __future__ import annotations

import math

Pos = tuple[float, float]


def ring_positions(
    count: int,
    center: Pos,
    radius: float,
    *,
    start_angle: float = -math.pi / 2,
    arc: float = 2 * math.pi,
) -> list[Pos]:
    """Return *count* positions evenly spaced on a ring.

    *start_angle* defaults to ``-π/2`` (12 o'clock, top of the ring). Angles
    increase clockwise in typical screen-y-down coordinates, so indices
    proceed 12 → 3 → 6 → 9 by default.

    *arc* defaults to a full circle. Set to ``math.pi`` to arrange things
    along the top half only, or to ``math.pi / 2`` for a 90° fan. When
    *arc* is a full circle, *count* positions fit exactly around; when
    *arc* is partial, positions include both endpoints.

    Examples::

        # 8 evenly-spaced nodes on a ring of radius 200 around (400, 300)
        positions = ring_positions(8, (400, 300), 200)

        # 5 cards fanning over a 60° arc at the bottom of the screen
        positions = ring_positions(
            5, (400, 700), 300,
            start_angle=-math.pi/2 - math.pi/6,
            arc=math.pi/3,
        )
    """
    if count <= 0:
        return []
    cx, cy = center
    if count == 1:
        return [(cx + radius * math.cos(start_angle), cy + radius * math.sin(start_angle))]

    is_full = math.isclose(abs(arc), 2 * math.pi, rel_tol=1e-9)
    step = arc / count if is_full else arc / (count - 1)
    return [
        (
            cx + radius * math.cos(start_angle + step * i),
            cy + radius * math.sin(start_angle + step * i),
        )
        for i in range(count)
    ]


def grid_positions(
    count: int,
    *,
    columns: int,
    cell: Pos,
    origin: Pos = (0.0, 0.0),
) -> list[Pos]:
    """Return *count* positions on a row-major grid.

    *cell* is ``(cell_w, cell_h)`` — the distance between neighbouring
    cells. *origin* is the centre of cell (0, 0). Positions are yielded
    in row-major order; the grid grows downward on screen (y increases).

    Examples::

        # Inventory: 4 columns, 12 items, cell 56x56, starting at (100, 80)
        positions = grid_positions(12, columns=4, cell=(56, 56), origin=(100, 80))
    """
    if count <= 0:
        return []
    if columns <= 0:
        raise ValueError("columns must be >= 1")
    ox, oy = origin
    cw, ch = cell
    return [
        (ox + (i % columns) * cw, oy + (i // columns) * ch)
        for i in range(count)
    ]


def line_positions(
    count: int,
    *,
    start: Pos,
    end: Pos,
) -> list[Pos]:
    """Return *count* positions evenly spaced along a line from *start* to *end*.

    Endpoints are included. ``count == 1`` places the single position at
    the midpoint of *start* → *end*.
    """
    if count <= 0:
        return []
    if count == 1:
        return [((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)]
    sx, sy = start
    ex, ey = end
    return [
        (sx + (ex - sx) * i / (count - 1), sy + (ey - sy) * i / (count - 1))
        for i in range(count)
    ]
