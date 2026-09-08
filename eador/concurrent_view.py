"""The authenticated realm and public map, expressed from the local player's seat.

This detached view supports the same army/catalog readers as solo play. Orders
always go to the authority; it contains no opposing treasury, choices or PvE.
"""
from dataclasses import dataclass

from saga2d import HexGrid
from eador.battle import Battle
from eador.concurrent_campaign import PlayerRealm, _restore_realm
from eador.content import SITES
from eador.economy import income_preview, recovery_preview
from eador.entities import Province, RuleError


@dataclass(kw_only=True)
class ConcurrentView(PlayerRealm):
    provinces: dict
    day: int
    seed: int
    theme: str
    opponent: dict
    claims: dict
    encounter: dict | None
    winner: int | None

    # Linked three-shard progression belongs to the solo campaign.
    campaign = None

    @classmethod
    def from_snapshot(cls, snapshot):
        realm = _restore_realm(snapshot['realm'])
        owners = {realm.owner: 'player', f'realm:{1 - realm.seat}': 'rival', 'neutral': 'neutral'}
        provinces = {tuple(p['pos']): Province(**{**p, 'pos': tuple(p['pos']), 'owner': owners[p['owner']]})
                     for p in snapshot['provinces']}
        view = cls(**vars(realm), provinces=provinces, day=snapshot['day'], seed=snapshot['seed'], theme=snapshot['theme'],
                   opponent=snapshot['opponent'], encounter=snapshot['encounter'], winner=snapshot['winner'],
                   claims={tuple(claim['pos']): claim['seat'] for claim in snapshot['claims']})
        if view.encounter and view.encounter['battle'] is not None:
            view.battle = Battle.from_dict(view.encounter['battle'])
            view.battle_kind = 'army'
            view.battle_province = tuple(view.encounter['destination'])
        return view

    @property
    def battle_team(self):
        return 'enemy' if self.battle_kind == 'army' and self.encounter['attacker'] != self.seat else 'player'

    @property
    def waiting(self):
        return bool(self.encounter and self.encounter['battle'] is None and self.encounter['attacker'] == self.seat)

    def _ready(self, action=False):
        super()._ready(action=action)
        if self.ready or self.waiting:
            raise RuleError('Waiting for the other realm.')

    @property
    def grid(self):
        return HexGrid(self.provinces)

    @property
    def production(self):
        return income_preview(self.provinces, owner='player', capital=self.capital,
                              buildings=self.buildings, rules=self.rules)

    def recovery_preview(self):
        return recovery_preview(self.hero, buildings=self.buildings, rules=self.rules,
                                available_gold=self.gold + self.production.gold,
                                blocked_reason='Capital is encircled.' if self.production.encircled
                                and self.hero.pos == self.capital else None)

    def infusion_preview(self):
        return self.quote_infusion(province=self.provinces[self.hero.pos], owner='player',
                                   encircled=self.production.encircled and self.hero.pos == self.capital)

    def replacement_preview(self, outgoing_id, kind):
        return self.quote_replacement(outgoing_id, kind, province=self.provinces[self.hero.pos], owner='player')

    def encounter_at(self, destination, *, kind='conquest'):
        site = self.provinces[destination].site_kind
        return SITES[site].encounter if kind == 'site' and site else None

    def adventure_approaches(self, destination=None):
        site = self.provinces[destination or self.hero.pos].site_kind
        return SITES[site].approaches if site else ()
