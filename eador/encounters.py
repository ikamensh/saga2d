"""Authored Shardbound battlefields; layout and objective rules are game content."""
from dataclasses import dataclass

Pos = tuple[int, int]


@dataclass(frozen=True)
class EncounterSpec:
    name: str
    terrain: tuple[tuple[Pos, str], ...]
    player_positions: tuple[Pos, ...]
    enemy_positions: tuple[Pos, ...]
    seal: Pos
    hold_turns: int = 2
    deadline: int = 8


_WATCH_FOREST = {(-1, 1), (-1, 2), (0, -1), (1, -2)}
_WATCH_HILLS = {(0, 0), (0, 1), (1, 0)}

ENCOUNTERS = {
    'border_watch': EncounterSpec(
        'Border Watch',
        tuple(((q, r), 'forest' if (q, r) in _WATCH_FOREST else 'hills' if (q, r) in _WATCH_HILLS else 'plains')
              for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
        ((-3, 1), (-2, 0), (-3, 2), (-2, 1), (-2, 2), (-3, 0), (-2, 3)),
        ((1, -1), (3, -1), (2, -2), (2, 0), (2, 1), (3, -3), (3, -2)),
        (0, 0),
    ),
}
