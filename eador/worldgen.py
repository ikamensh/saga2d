"""Seeded shard generation belongs to Shardbound, separate from campaign commands."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from eador.content import SITES

if TYPE_CHECKING:
    from eador.model import Pos, Province

# Adding authored encounters must not change every subsequent default RNG draw.
FRONTIER_SITES = ('shrine', 'tower', 'barrow', 'den', 'caravan', 'grove')


def generate(seed: int) -> dict[Pos, Province]:
    """Return a fresh shard whose full generated contents are stored in campaign saves."""
    from eador.model import Province, UNITS

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
    rival.guards, rival.site = ['guard'] * 5 + ['archer'] * 2, None
    rival.site_kind, rival.site_guards, rival.site_relic = None, [], None
    rival.site_gold = rival.site_crystals = 0
    for province in provinces.values():
        province.guard_hp = [UNITS[kind].hp for kind in province.guards]
        province.site_guard_hp = [UNITS[kind].hp for kind in province.site_guards]
    return provinces
