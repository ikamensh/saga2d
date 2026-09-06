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

# One assembly, several manual plans: finish the caster, anchor the carrier,
# occupy its push landing, or take a mobile ranged flank through the marsh.
ENCOUNTERS['runebound_causeway'] = EncounterSpec(
    'Runebound Causeway',
    tuple(((q, r), 'marsh' if q in (0, 1) and (q, r) != (0, 0) else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-2, -1), (-3, 1), (-2, 0), (-2, 1), (-3, 2), (-2, 2)),
    ((0, 0), (2, -1), (2, 1), (-3, 3)),
    exits=((3, -3),), deadline=5, objective='extract',
)


_RELIEF_MARSH = {(-1, -2), (1, -3), (-2, -1), (-1, -1), (-1, 0), (-1, 1), (-1, 2)}
ENCOUNTERS['relief_forward'] = EncounterSpec(
    'Relief Column',
    tuple(((q, r), 'marsh' if (q, r) in _RELIEF_MARSH else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-1, -1), (0, -1), (-2, -1), (0, -2), (-1, -2), (-2, 0), (-1, 0)),
    ((3, 0), (3, -1), (1, 2), (2, 1)),
    (0, -2), deadline=4, objective='hold',
)
ENCOUNTERS['relief_western'] = replace(ENCOUNTERS['relief_forward'],
    player_positions=((-3, 0), (-2, 0), (-3, 1), (-2, -1), (-1, -2), (-2, 1), (-3, 2)))

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
    ((1, -1), (2, -1), (2, 1), (-3, 2), (-3, 3), (1, 1), (3, -2)),
)
ENCOUNTERS['hunt_lured'] = replace(ENCOUNTERS['hunt_compact'],
    player_positions=((0, -2), (-1, -2), (1, -3), (0, -3), (1, -2), (3, -3), (-2, -1)))


_OBSERVATORY_FOREST = {(-1, 0), (0, -1), (0, 1), (1, -2), (1, 1), (-2, 1)}
_OBSERVATORY_HILLS = {(0, 0), (1, 0), (1, -3), (3, -1), (0, 3)}
ENCOUNTERS['observatory_covered'] = EncounterSpec(
    'Broken Observatory',
    tuple(((q, r), 'forest' if (q, r) in _OBSERVATORY_FOREST else 'hills' if (q, r) in _OBSERVATORY_HILLS else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-2, 0), (-3, 1), (-2, -1), (-2, 1), (-3, 2), (-2, 2)),
    ((1, 0), (3, -1), (1, -3), (0, 3), (2, 0), (2, 1), (3, -3)),
    (0, 0),
    objective='hold',
)
ENCOUNTERS['observatory_clear'] = replace(ENCOUNTERS['observatory_covered'],
    terrain=tuple((pos, 'plains' if pos == (-1, 0) else terrain)
                  for pos, terrain in ENCOUNTERS['observatory_covered'].terrain))


_EXPLORER_MARSH = {(0, -1), (0, 0), (0, 1), (-1, 0)}
_EXPLORER_FOREST = {(-1, -1), (1, 1), (-2, 2)}
ENCOUNTERS['explorer_north'] = EncounterSpec(
    'Stranded Explorer',
    tuple(((q, r), 'marsh' if (q, r) in _EXPLORER_MARSH else 'forest' if (q, r) in _EXPLORER_FOREST else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((3, -1), (-3, 0), (-3, 1), (-2, -1), (-2, 0), (2, -1), (-2, 1)),
    ((1, 0), (1, -2), (0, 2), (-1, 2), (2, 0), (2, 1), (3, -3)),
    exits=((-3, 1),), deadline=6, objective='extract',
)
ENCOUNTERS['explorer_south'] = replace(ENCOUNTERS['explorer_north'],
    player_positions=((3, -1), (-2, 3), (-1, 3), (-2, 2), (-2, 1), (2, -1), (-3, 3)))


_SCREEN_FOREST = {(-1, -1), (0, 1), (1, -2)}
_SCREEN_HILLS = {(1, 0), (2, -1)}
ENCOUNTERS['screen_western'] = EncounterSpec(
    'Smuggler Screen',
    tuple(((q, r), 'forest' if (q, r) in _SCREEN_FOREST else 'hills' if (q, r) in _SCREEN_HILLS else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-2, 0), (-3, 1), (-2, -1), (-3, 2), (-2, 1), (-3, 3)),
    ((1, 0), (2, -1), (1, -1), (2, 0), (1, 1), (2, -2), (3, -1)),
)
ENCOUNTERS['screen_northern'] = replace(ENCOUNTERS['screen_western'],
    player_positions=((-3, 0), (-2, -1), (-2, 0), (-1, -2), (-3, 1), (0, -3), (-3, 2)))


# Flyers cross the marsh and occupied approach; their exposed landing remains a
# melee commitment. Both assemblies face the same finite eastern defenders.
ENCOUNTERS['aerie_western'] = EncounterSpec(
    'Aerie Raid',
    tuple(((q, r), 'marsh' if (q in (-1, 0) and (q, r) != (-1, 0)) or (q, r) in {(1, 0), (1, 1)} else
           'hills' if (q, r) in {(1, -1), (2, -1)} else 'plains')
          for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3),
    ((-3, 0), (-1, 0), (-2, 0), (-3, 1), (-3, 2), (-2, 2), (-1, 1)),
    ((1, -2), (1, 1), (2, -1), (1, -1), (3, -1), (2, 1), (3, -3)),
)

ENCOUNTERS['aerie_northern'] = replace(ENCOUNTERS['aerie_western'],
    player_positions=((-2, -1), (-1, -1), (-2, 0), (-2, 1), (0, -2), (-1, -2), (-3, 0)))
