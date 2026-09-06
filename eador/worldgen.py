"""Seeded shard generation belongs to Shardbound, separate from campaign commands."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from eador.content import SITES

if TYPE_CHECKING:
    from eador.model import Pos, Province

# Adding authored encounters must not change every subsequent default RNG draw.
FRONTIER_SITES = ('shrine', 'tower', 'barrow', 'den', 'caravan', 'grove')


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    description: str


THEMES = {
    'frontier': ThemeSpec('Frontier', 'Open borders, mixed guardians, and a familiar route to Duskspire.'),
    'elderwild': ThemeSpec('Elderwild', 'Wolf packs stalk the wet interior. A longer dry road offers gold and merchant relics.'),
    'ruins': ThemeSpec('Ruins', 'Pikemen hold valuable checkpoints. A poorer flank avoids the strongest formations.'),
}

NORTH_ROAD = ((-2, 0), (-1, -1), (0, -1), (1, -1), (2, -1), (2, 0))
SOUTH_ROAD = ((-2, 0), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 0))


def generate(seed: int, theme: str = 'frontier') -> dict[Pos, Province]:
    """Return a fresh shard whose full generated contents are stored in campaign saves."""
    from eador.model import Province, RuleError, UNITS

    if not isinstance(theme, str) or theme not in THEMES:
        raise RuleError('Choose Frontier, Elderwild or Ruins.')
    rng = random.Random(seed)
    cells = [(q, r) for q in range(-2, 3) for r in range(-2, 3)
             if abs(q + r) <= 2]
    names = ['Westwatch', 'Amber Fields', 'Old Hollow', 'Briarwood',
             'Silverford', 'Winding Vale', 'Mossfell', 'Raven Hill',
             'Greenwater', 'Heartwood', 'Stonecross', 'Sunken Road',
             'Ashen Marsh', 'Frostmere', 'Cinderwood', 'High Pass',
             'Lost Reach', 'Blackfen', 'Duskspire']
    provinces = {}
    for pos, name in zip(cells, names):
        terrain = rng.choice(('plains', 'forest', 'hills', 'marsh'))
        guards = [rng.choice(('brigand', 'goblin', 'wolf'))
                  for _ in range(1 if pos[0] < 0 else 2)]
        if pos[0] == 0:
            guards = ['brigand', 'goblin', 'wolf']
        elif pos[0] == 1:
            guards = ['guard', 'guard', 'brigand', 'goblin']
        elif pos[0] == 2:
            guards = ['guard', 'guard', 'archer']
        owner = 'rival' if pos[0] == 2 else 'neutral'
        provinces[pos] = Province(pos, name, terrain, owner,
                                  rng.randint(5, 9), int(terrain == 'hills'),
                                  guards, None)
        kind = rng.choice(FRONTIER_SITES)
        spec = SITES[kind]
        province = provinces[pos]
        province.site, province.site_kind = spec.name, kind
        province.site_guards = list(spec.guards) + (['guard'] if pos[0] >= 1 else [])
        province.site_relic = spec.relic
        province.site_gold, province.site_crystals = spec.gold, spec.crystals
    home, rival = provinces[(-2, 0)], provinces[(2, 0)]
    home.name, home.owner, home.capital, home.income = 'Westwatch', 'player', True, 16
    home.guards, home.site = [], 'Buried Shrine'
    home.site_kind, home.site_guards, home.site_relic = 'shrine', list(SITES['shrine'].guards), 'moonstone'
    home.site_gold, home.site_crystals = SITES['shrine'].gold, SITES['shrine'].crystals
    rival.name, rival.owner, rival.capital, rival.income = 'Duskspire', 'rival', True, 16
    watch, spec = provinces[(0, -2)], SITES['border_watch']
    watch.site, watch.site_kind = spec.name, 'border_watch'
    watch.site_guards, watch.site_relic = list(spec.guards), spec.relic
    watch.site_gold, watch.site_crystals = spec.gold, spec.crystals
    rival.guards, rival.site = ['guard'] * 5 + ['archer'] * 2, None
    rival.site_kind, rival.site_guards, rival.site_relic = None, [], None
    rival.site_gold = rival.site_crystals = 0
    if theme == 'elderwild':
        _elderwild(provinces, seed)
    elif theme == 'ruins':
        _ruins(provinces, seed)
    if theme == 'frontier':
        _site(provinces[(0, 2)], 'courier_crossing')
        _site(provinces[(-1, 1)], 'muster_yard')
        _site(provinces[(0, -1)], 'stranded_explorer')
    elif theme == 'elderwild':
        _site(provinces[(-1, -1)], 'supply_cache')
        _site(provinces[(-1, 1)], 'pack_hunt')
        _site(provinces[(0, -1)], 'smuggler_screen')
    elif theme == 'ruins':
        _site(provinces[(-1, 1)], 'sealed_vault')
        _site(provinces[(-1, 0)], 'broken_observatory')
        _site(provinces[(0, 0)], 'aerie_raid')
    _site(provinces[(-2, 2)], 'den')
    _site(provinces[(-1, 2)], 'explorer_camp')
    # Preserve the former duplicate reward's discoverability without rerolling the map.
    # (-2, 1) is a procedural western site, clear of every fixed authored source.
    fallback = 'caravan' if theme == 'frontier' else 'grove' if theme == 'elderwild' else None
    if fallback and not any(province.site_relic == SITES[fallback].relic for province in provinces.values()):
        _site(provinces[(-2, 1)], fallback)
    for province in provinces.values():
        province.guard_hp = [UNITS[kind].hp for kind in province.guards]
        province.site_guard_hp = [UNITS[kind].hp for kind in province.site_guards]
    return provinces


def _site(province: Province, kind: str) -> None:
    spec = SITES[kind]
    province.site, province.site_kind = spec.name, kind
    province.site_guards = list(spec.guards) + (['guard'] if province.pos[0] >= 1 else [])
    province.site_relic = spec.relic
    province.site_gold, province.site_crystals = spec.gold, spec.crystals


def _elderwild(provinces: dict[Pos, Province], seed: int) -> None:
    rng = random.Random(seed ^ 0xE1DE)
    road = set(rng.choice((NORTH_ROAD, SOUTH_ROAD)))
    for pos, province in provinces.items():
        if pos == (-2, 0):
            continue
        on_road = pos in road
        province.terrain = 'plains' if on_road else rng.choice(('forest', 'forest', 'forest', 'marsh'))
        if province.capital:
            province.terrain = 'forest'
            province.guards = ['guard'] * 4 + ['wolf', 'wolf', 'archer']
            continue
        province.income = rng.randint(10, 12) if on_road else rng.randint(4, 6)
        province.crystals = int(not on_road and province.terrain == 'forest')
        q = pos[0]
        if q < 0:
            province.guards = ['brigand'] if on_road else [rng.choice(('wolf', 'goblin'))]
        elif q == 0:
            province.guards = ['brigand', 'archer'] if on_road else ['wolf', 'wolf', 'wolf', 'goblin']
        else:
            province.guards = ['guard', 'wolf', 'archer'] if on_road else ['guard', 'guard', 'wolf', 'goblin']
        _site(province, 'caravan' if on_road else rng.choice(('grove', 'den', 'shrine', 'tower')))
    _site(provinces[(0, 2 if (0, -1) in road else -2)], 'border_watch')
    provinces[(0, 0)].name = 'Mire Crossing'
    for pos in road:
        if pos[0] == 0:
            provinces[pos].name = 'Old Causeway'


def _ruins(provinces: dict[Pos, Province], seed: int) -> None:
    rng = random.Random(seed ^ 0xA5C1)
    flank = set(rng.choice((NORTH_ROAD, SOUTH_ROAD)))
    direct = {(-1, 0), (0, 0), (1, 0)}
    for pos, province in provinces.items():
        if pos == (-2, 0):
            continue
        province.terrain = 'plains' if pos in direct else rng.choice(('hills', 'hills', 'hills', 'plains'))
        if province.capital:
            province.terrain = 'hills'
            province.guards = ['guard'] * 4 + ['pikeman', 'archer', 'archer']
            continue
        q = pos[0]
        if pos in direct:
            province.income, province.crystals = 12, 2
            province.guards = (['pikeman'] if q < 0 else ['pikeman', 'archer', 'goblin'] if q == 0
                               else ['guard', 'pikeman', 'pikeman', 'archer'])
            _site(province, 'barrow')
        elif pos in flank:
            province.income, province.crystals = rng.randint(7, 9), 0
            province.guards = (['brigand'] if q < 0 else ['brigand', 'goblin'] if q == 0
                               else ['brigand', 'goblin', 'archer'])
            _site(province, 'caravan' if q < 0 else 'tower' if q == 0 else 'barrow')
        else:
            province.income, province.crystals = rng.randint(4, 6), 1
            province.guards = (['goblin'] if q < 0 else ['pikeman', 'pikeman', 'archer'] if q == 0
                               else ['guard', 'guard', 'pikeman', 'archer'])
            _site(province, rng.choice(('tower', 'barrow', 'shrine')))
    _site(provinces[(0, 2 if (0, -1) in flank else -2)], 'border_watch')
    provinces[(0, 0)].name = 'Broken Checkpoint'
    for pos in flank:
        if pos[0] == 0:
            provinces[pos].name = 'Salvager’s Track'
