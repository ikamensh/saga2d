"""Authored Shardbound battlefields; layout and objective rules are game content."""
from dataclasses import dataclass, replace

Pos = tuple[int, int]


@dataclass(frozen=True)
class EncounterSpec:
    name: str
    terrain: tuple[tuple[Pos, str], ...]
    player_positions: tuple[Pos, ...]
    enemy_positions: tuple[Pos, ...]
    seal: Pos | None = None
    hold_turns: int = 2
    deadline: int = 8
    exits: tuple[Pos, ...] = ()
    objective: str = 'rout'


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
        objective='hold',
    ),
}

# The final ritual has a western seal and a broad eastern approach. Its short
# deadline trades the chance of early control for the safety of a longer rout.
ENCOUNTERS['last_gate'] = EncounterSpec(
    'The Last Gate',
    tuple(((q, r), 'hills' if (q, r) in {(-1, 0), (0, 0), (1, 0), (2, 0)} else
           'forest' if (q, r) in {(-2, 1), (0, -2), (1, -2), (2, -3)} else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-2, 0), (-3, 1), (-2, -1), (-3, 2), (-2, 1), (-3, 3)),
    ((1, -1), (2, -1), (1, 1), (2, 0), (3, -2), (3, -1), (3, 0)),
    (-1, 0),
    objective='hold',
)


_CROSSING_FOREST = {(-2, -1), (-1, -1), (0, -2), (1, -3), (-1, 3), (0, 2)}
_CROSSING_HILLS = {(0, 0), (1, -1), (2, -2)}
ENCOUNTERS['courier_direct'] = EncounterSpec(
    'Courier’s Crossing',
    tuple(((q, r), 'forest' if (q, r) in _CROSSING_FOREST else 'hills' if (q, r) in _CROSSING_HILLS else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 1), (-2, 0), (-3, 2), (-2, 1), (-2, 2), (-3, 0), (-2, 3)),
    ((1, -1), (2, -2), (1, 1), (2, 0), (2, 1), (3, -2), (3, -1)),
    exits=((3, -3), (3, 0)),
    objective='extract',
)
ENCOUNTERS['courier_guided'] = replace(ENCOUNTERS['courier_direct'],
    player_positions=((-1, 3), (0, 3), (-2, 3), (-1, 2), (0, 2), (-2, 2), (-3, 3)))


_CACHE_FOREST = {(-2, 0), (-1, 0), (0, -2), (1, -2), (1, 0), (0, 1), (-1, 2)}
ENCOUNTERS['supply_cache'] = EncounterSpec(
    'Supply Cache',
    tuple(((q, r), 'forest' if (q, r) in _CACHE_FOREST else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((0, 0), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)),
    ((-3, 0), (3, -3), (3, 0), (0, 3), (2, 1), (-3, 3), (1, 2)),
    exits=((-3, 1), (2, -3)),
    objective='extract',
)


_VAULT_MARSH = {(-1, 1), (-1, 2), (0, 1)}
_VAULT_HILLS = {(-1, -1), (0, -1), (1, -1), (1, -3), (2, -1), (2, 1)}
ENCOUNTERS['vault_crossfire'] = EncounterSpec(
    'Sealed Vault',
    tuple(((q, r), 'marsh' if (q, r) in _VAULT_MARSH else 'hills' if (q, r) in _VAULT_HILLS else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-2, 0), (-2, -1), (-3, 1), (-1, -1), (-2, 1), (-3, 0), (-3, 2)),
    ((2, -1), (-3, 3), (2, 1), (0, -1), (3, -3), (2, 0), (3, -1)),
    exits=((3, -1),),
    objective='extract',
)
ENCOUNTERS['vault_unsealed'] = replace(ENCOUNTERS['vault_crossfire'], exits=((3, -1), (-1, 3)))


_HUNT_FOREST = {(0, -1), (0, 0), (0, 1), (0, 2), (-2, 2), (-1, 2)}
ENCOUNTERS['hunt_compact'] = EncounterSpec(
    'Pack Hunt',
    tuple(((q, r), 'forest' if (q, r) in _HUNT_FOREST else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-1, 0), (0, -1), (-1, 1), (-2, 1), (-1, -1), (-2, 0), (-3, 0)),
    ((1, -2), (2, -1), (2, 1), (-3, 2), (-3, 3), (1, 1), (3, -2)),
)
ENCOUNTERS['hunt_lured'] = replace(ENCOUNTERS['hunt_compact'],
    player_positions=((-1, -2), (-2, -1), (0, -3), (1, -3), (0, -2), (-1, -1), (-2, 0)))
