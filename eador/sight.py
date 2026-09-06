"""Shardbound's forest and smoke visibility, without combat or framework policy."""
from collections.abc import Collection, Mapping

Pos = tuple[int, int]


def _crosses_hex(source, delta, cell, offset) -> bool:
    """Clip a segment against the three pairs of sides of a pointy axial hex."""
    q, r = source[0] - cell[0] + offset[0], source[1] - cell[1] + offset[1]
    dq, dr = delta
    enter, leave = 0.0, 1.0
    for origin, slope in ((2 * q + r, 2 * dq + dr),
                          (q + 2 * r, dq + 2 * dr), (q - r, dq - dr)):
        if slope == 0:
            if abs(origin) >= 1:
                return False
        else:
            first, last = sorted(((-1 - origin) / slope, (1 - origin) / slope))
            enter, leave = max(enter, first), min(leave, last)
            if enter >= leave:
                return False
    return True


def line_of_sight(terrain: Mapping[Pos, str], source: Pos, target: Pos, *,
                  smoke: Collection[Pos] = ()) -> bool:
    """Whether either edge of a straight hex ray is clear.

    Intervening forest and missing cells block sight; endpoint forest is cover,
    not an obstruction. Smoke blocks either endpoint or an intervening cell.
    Seeing one's own cell always succeeds. Range, melee and unit bodies are the
    caller's concern. Endpoints outside this battlefield raise ValueError.
    """
    if source not in terrain or target not in terrain:
        raise ValueError('Sight endpoints must be on the battlefield.')
    if source == target:
        return True
    if source in smoke or target in smoke:
        return False
    dq, dr = target[0] - source[0], target[1] - source[1]
    blockers = [(q, r) for q in range(min(source[0], target[0]), max(source[0], target[0]) + 1)
                for r in range(min(source[1], target[1]), max(source[1], target[1]) + 1)
                if (q, r) not in (source, target)
                and ((q, r) not in terrain or terrain[q, r] == 'forest' or (q, r) in smoke)]
    # Offset parallel rays to either side, perpendicular in world coordinates.
    # A shot along a shared hex edge is clear if either whole ray is clear;
    # this avoids choosing an arbitrary favored direction at geometric ties.
    for sign in (-1, 1):
        offset = (-(dq + 2 * dr) * sign * 1e-7, (2 * dq + dr) * sign * 1e-7)
        if not any(_crosses_hex(source, (dq, dr), cell, offset) for cell in blockers):
            return True
    return False
