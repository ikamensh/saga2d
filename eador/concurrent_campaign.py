"""Concurrent campaign authority: one map, separate realms and one shared day.

This model is under development, not a selectable PvP mode. Battles against
the environment retain their ordinary turns. Human army encounters and their
presentation must be integrated before offering the mode to players.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields
import json

from saga2d import CommandError, HexGrid
from eador.content import AdventureAttempt, Choice, ChoiceOption, SITES
from eador.difficulty import DIFFICULTIES
from eador.economy import income_preview, recovery_preview, settle_realm
from eador.entities import Hero, Pos, Province, RuleError, SaveFormatError, Troop
from eador.realm import Realm


@dataclass(kw_only=True)
class PlayerRealm(Realm):
    seat: int
    capital: Pos
    ready: bool = False
    revision: int = 0

    @property
    def owner(self) -> str:
        return f'realm:{self.seat}'


def _realm_data(realm: PlayerRealm) -> dict:
    data = asdict(realm)
    data['buildings'] = sorted(realm.buildings)
    data['choices'] = data.pop('_choices')
    data['battle'] = realm.battle.to_dict() if realm.battle else None
    return data


def _restore_realm(data: dict) -> PlayerRealm:
    from eador.battle import Battle

    data = deepcopy(data)
    expected = {f.name for f in fields(PlayerRealm)} - {'_choices'} | {'choices'}
    if data.keys() != expected:
        raise SaveFormatError('Realm checkpoint has missing or unsupported fields.')
    hero = data['hero']
    data['hero'] = Hero(**{**hero, 'pos': tuple(hero['pos']),
                          'army': [Troop(**troop) for troop in hero['army']]})
    data['capital'] = tuple(data['capital'])
    data['buildings'] = set(data['buildings'])
    data['_choices'] = [Choice(**{**choice, 'options': tuple(ChoiceOption(**item)
                       for item in choice['options'])}) for choice in data.pop('choices')]
    data['battle'] = Battle.from_dict(data['battle']) if data['battle'] is not None else None
    if data['battle_province'] is not None:
        data['battle_province'] = tuple(data['battle_province'])
    if data['battle_adventure'] is not None:
        data['battle_adventure'] = AdventureAttempt(**data['battle_adventure'])
    return PlayerRealm(**data)


@dataclass
class ConcurrentCampaign:
    seed: int
    theme: str
    provinces: dict[Pos, Province]
    realms: list[PlayerRealm]
    day: int = 1
    claims: dict[Pos, int] = field(default_factory=dict)
    winner: int | None = None

    @classmethod
    def new(cls, seed=7, *, heroes=('Commander', 'Commander'), theme='frontier',
            difficulty='standard') -> ConcurrentCampaign:
        from eador.entities import HERO_CLASSES, starting_hero
        from eador.worldgen import generate

        if type(seed) is not int:
            raise RuleError('The shard seed must be an integer.')
        if (not isinstance(heroes, (tuple, list)) or len(heroes) != 2
                or any(not isinstance(hero, str) or hero not in HERO_CLASSES for hero in heroes)):
            raise RuleError('Choose two supported heroes.')
        if not isinstance(difficulty, str) or difficulty not in DIFFICULTIES:
            raise RuleError('Choose Accessible, Standard or Challenge.')
        provinces = generate(seed, theme)
        # Both ends receive the same opening opportunities. The map is stored
        # once; mirrored provinces are distinct objects, not alternate worlds.
        for pos in sorted(provinces):
            if pos[0] < 0:
                reflected = (-pos[0], -pos[1])
                name = provinces[reflected].name
                province = deepcopy(provinces[pos])
                province.pos, province.name = reflected, name
                provinces[reflected] = province
        for province in provinces.values():
            province.owner = 'neutral'
        rules = DIFFICULTIES[difficulty]
        realms = []
        for seat, capital in enumerate(((-2, 0), (2, 0))):
            realm = PlayerRealm(seat=seat, capital=capital,
                                hero=starting_hero(heroes[seat], capital,
                                                   name='Alden' if seat == 0 else 'Mira'),
                                gold=rules.starting_gold, crystals=rules.starting_crystals,
                                rules_id=rules.id, actions_left=3 if heroes[seat] == 'Scout' else 2)
            provinces[capital].owner = realm.owner
            realm.log.append('Develop your realm. Ready together to advance the campaign day.')
            realms.append(realm)
        return cls(seed, theme, provinces, realms)

    def income(self, seat: int):
        realm = self.realms[seat]
        return income_preview(self.provinces, owner=realm.owner, capital=realm.capital,
                              buildings=realm.buildings, rules=realm.rules)

    def apply(self, seat: int, command: dict) -> None:
        """Commit one authenticated realm order atomically, without a global revision lock."""
        if type(seat) is not int or seat not in (0, 1):
            raise CommandError('Unknown realm.')
        if not isinstance(command, dict) or set(command) != {
                'day', 'realm_revision', 'action', 'args', 'kwargs'}:
            raise CommandError('Invalid campaign order.')
        realm = self.realms[seat]
        if type(command['day']) is not int or command['day'] != self.day:
            raise CommandError('The campaign day changed. Refresh this order.')
        if type(command['realm_revision']) is not int or command['realm_revision'] != realm.revision:
            raise CommandError('Your realm changed. Refresh this order.')
        if self.winner is not None:
            raise CommandError('This campaign has ended.')
        if realm.ready:
            raise CommandError('Your realm is ready for the next day.')
        if (not isinstance(command['action'], str) or not isinstance(command['args'], list)
                or not isinstance(command['kwargs'], dict)):
            raise CommandError('Invalid campaign order arguments.')
        trial = deepcopy(self)
        try:
            changed = trial._dispatch(seat, command['action'], command['args'], command['kwargs'])
        except RuleError as error:
            raise CommandError(str(error)) from error
        for changed_seat in changed:
            trial.realms[changed_seat].revision += 1
        self.__dict__.update(trial.__dict__)

    def _dispatch(self, seat, action, args, kwargs):
        realm = self.realms[seat]
        if action.startswith('battle.'):
            from eador.orders import BATTLE_ORDERS, invoke_order

            action = action.removeprefix('battle.')
            if action not in BATTLE_ORDERS:
                raise RuleError('Unknown battle order.')
            if realm.battle is None:
                raise RuleError('There is no active battle.')
            invoke_order(realm.battle, action, args, kwargs)
            return {seat}
        if action == 'explore':
            if args or set(kwargs) - {'approach'}:
                raise RuleError('Choose an offered adventure approach.')
            approach = kwargs.get('approach')
            if approach is not None and not isinstance(approach, str):
                raise RuleError('Choose an offered adventure approach.')
            self._explore(seat, approach)
            return {seat}
        if kwargs:
            raise RuleError('Unknown campaign order option.')
        if action in ('build', 'recruit'):
            if len(args) != 1 or not isinstance(args[0], str):
                raise RuleError('Choose a building or troop.')
            if action == 'build':
                realm.build(args[0])
            else:
                realm.purchase_recruit(args[0], province=self.provinces[realm.hero.pos], owner=realm.owner)
        elif action == 'travel':
            if (len(args) != 1 or not isinstance(args[0], (list, tuple)) or len(args[0]) != 2
                    or any(type(n) is not int for n in args[0])):
                raise RuleError('Choose a province on this shard.')
            self._travel(seat, tuple(args[0]))
        elif action in ('retreat', 'resolve_battle'):
            if args:
                raise RuleError('Battle results take no arguments.')
            if action == 'retreat':
                if realm.battle is None:
                    raise RuleError('There is no battle to retreat from.')
                if realm.battle.outcome is not None:
                    raise RuleError('The battle is over; accept its result.')
                realm.battle.outcome = 'enemy'
            self._resolve_battle(seat)
        elif action in ('choose', 'equip'):
            if len(args) != 1 or not (isinstance(args[0], str) or action == 'equip' and args[0] is None):
                raise RuleError('Choose a skill or relic.')
            getattr(realm, action)(args[0])
        elif action == 'ready':
            if args:
                raise RuleError('Ready takes no arguments.')
            realm._ready()
            realm.ready = True
            if all(player.ready for player in self.realms):
                self._advance_day()
                return {0, 1}
        else:
            raise RuleError('Unknown campaign order.')
        return {seat}

    def _available(self, seat: int, position: Pos) -> None:
        if position in self.claims:
            raise RuleError('That province is claimed by an active encounter. No action was spent.')
        opponent = self.realms[1 - seat]
        if position == opponent.hero.pos or self.provinces[position].owner == opponent.owner:
            raise RuleError('Human army conflicts are not available in this development mode yet.')

    def _travel(self, seat: int, destination: Pos) -> None:
        realm = self.realms[seat]
        realm._ready(action=True)
        if destination not in HexGrid(self.provinces).neighbors(realm.hero.pos):
            raise RuleError('Travel to an adjacent province.')
        self._available(seat, destination)
        province = self.provinces[destination]
        realm.actions_left -= 1
        if province.owner == realm.owner:
            realm.hero.pos = destination
            realm.log.append(f'Travelled to {province.name}.')
        elif province.guards:
            self._start_battle(seat, province, 'conquest')
        else:
            province.owner = realm.owner
            realm.hero.pos = destination
            realm.log.append(f'Claimed unguarded {province.name}.')

    def _explore(self, seat: int, approach: str | None) -> None:
        from eador.adventures import quote_adventure

        realm = self.realms[seat]
        realm._ready(action=True)
        province = self.provinces[realm.hero.pos]
        if province.owner != realm.owner:
            raise RuleError('Explore a province you control.')
        if province.explored or province.site is None:
            raise RuleError('This province has no unexplored site.')
        self._available(seat, province.pos)
        quote = quote_adventure(province, gold=realm.gold, crystals=realm.crystals, approach=approach)
        realm.battle_adventure = quote.attempt
        self._start_battle(seat, province, 'site')
        realm.actions_left -= 1
        realm.gold -= quote.gold
        realm.crystals -= quote.crystals

    def _start_battle(self, seat: int, province: Province, kind: str) -> None:
        from eador.battle import Battle

        realm = self.realms[seat]
        site = kind == 'site'
        attempt = realm.battle_adventure
        encounter = SITES[province.site_kind].encounter if site and province.site_kind else None
        if attempt:
            encounter = attempt.encounter
        realm.battle = Battle.create(realm.hero, province.site_guards if site else province.guards,
                                    province.terrain, realm.spells,
                                    seed=self.seed + self.day * 37 + province.pos[0] * 7 + province.pos[1],
                                    enemy_hp=province.site_guard_hp if site else province.guard_hp,
                                    encounter=encounter, cargo_penalty=attempt.cargo_penalty if attempt else 0)
        realm.battle_kind, realm.battle_province = kind, province.pos
        self.claims[province.pos] = seat
        realm.log.append(f'Battle at {province.site if site else province.name}.')

    def _resolve_battle(self, seat: int) -> None:
        from eador.battle_results import persist_province_defenders

        realm = self.realms[seat]
        battle = realm.battle
        if battle is None or battle.outcome is None:
            raise RuleError('The battle is not finished.')
        if self.claims.get(realm.battle_province) != seat:
            raise RuleError('This realm does not own the encounter claim.')
        province = self.provinces[realm.battle_province]
        persist_province_defenders(province, battle, kind=realm.battle_kind)
        result = realm.apply_battle_progression(battle)
        if battle.outcome == 'player':
            if realm.battle_kind == 'site':
                message = realm.reward_site(province)
            else:
                province.owner = realm.owner
                province.guards, province.guard_hp = [], []
                realm.hero.pos = province.pos
                realm.gold += 25
                message = f'Claimed {province.name}: +25 gold.'
        else:
            lost_gold = min(max(0, realm.gold), 20)
            realm.gold -= lost_gold
            message = f'Retreated. Lost {lost_gold} gold; the survivors keep their wounds.'
        if result.casualties:
            realm.log.append('Fallen: ' + ', '.join(result.casualties) + '.')
        realm.log.append(message)
        del self.claims[province.pos]
        realm.battle = realm.battle_kind = realm.battle_province = realm.battle_adventure = None

    def _advance_day(self):
        quotes = [self.income(seat) for seat in (0, 1)]
        for realm, quote in zip(self.realms, quotes):
            blocked = quote.encircled and realm.hero.pos == realm.capital
            rest = recovery_preview(realm.hero, buildings=realm.buildings, rules=realm.rules,
                                    available_gold=realm.gold + quote.gold,
                                    blocked_reason='Capital is encircled.' if blocked else None)
            result = settle_realm(realm.hero, gold=realm.gold, crystals=realm.crystals,
                                  income=quote.gold, crystal_income=quote.crystals,
                                  recovery=rest, turn=self.day + 1)
            realm.gold, realm.crystals, realm.actions_left = result.gold, result.crystals, result.actions_left
            realm.log.extend(result.log)
            realm.ready = False
        self.day += 1

    def checkpoint(self) -> dict:
        """Complete trusted state; never send this as a player's network view."""
        return json.loads(json.dumps({
            'schema_version': 1, 'seed': self.seed, 'theme': self.theme, 'day': self.day,
            'provinces': [asdict(self.provinces[pos]) for pos in sorted(self.provinces)],
            'realms': [_realm_data(realm) for realm in self.realms],
            'claims': [{'pos': pos, 'seat': seat} for pos, seat in sorted(self.claims.items())],
            'winner': self.winner,
        }))

    @classmethod
    def restore(cls, data: dict) -> ConcurrentCampaign:
        """Restore a trusted checkpoint without regenerating either side of the map."""
        if not isinstance(data, dict) or data.get('schema_version') != 1:
            raise SaveFormatError('Unsupported concurrent campaign checkpoint.')
        if set(data) != {'schema_version', 'seed', 'theme', 'day', 'provinces', 'realms', 'claims', 'winner'}:
            raise SaveFormatError('Campaign checkpoint has missing or unsupported fields.')
        provinces = {tuple(p['pos']): Province(**{**deepcopy(p), 'pos': tuple(p['pos'])})
                     for p in data['provinces']}
        realms = [_restore_realm(realm) for realm in data['realms']]
        claims = {tuple(claim['pos']): claim['seat'] for claim in data['claims']}
        if ([realm.seat for realm in realms] != [0, 1]
                or len(provinces) != len(data['provinces']) or len(claims) != len(data['claims'])
                or type(data['day']) is not int or data['day'] < 1
                or data['winner'] is not None and (type(data['winner']) is not int or data['winner'] not in (0, 1))):
            raise SaveFormatError('Invalid campaign realms, provinces or day.')
        for realm in realms:
            if realm.capital not in provinces or realm.hero.pos not in provinces:
                raise SaveFormatError('A realm lies outside the campaign map.')
            if type(realm.ready) is not bool or type(realm.revision) is not int or realm.revision < 0:
                raise SaveFormatError('Invalid realm readiness or revision.')
        if any(type(seat) is not int or seat not in (0, 1) or pos not in provinces
               for pos, seat in claims.items()):
            raise SaveFormatError('Invalid encounter claim.')
        active = {}
        for realm in realms:
            if realm.battle is None:
                if any(value is not None for value in (realm.battle_kind, realm.battle_province, realm.battle_adventure)):
                    raise SaveFormatError('Saved encounter context has no active battle.')
                continue
            position = realm.battle_province
            if (realm.ready or realm.battle_kind not in ('site', 'conquest')
                    or position not in provinces or position in active):
                raise SaveFormatError('Invalid saved encounter context.')
            if realm.battle_kind == 'site':
                if realm.hero.pos != position or provinces[position].owner != realm.owner:
                    raise SaveFormatError('Saved site encounter does not belong to its realm.')
            elif position not in HexGrid(provinces).neighbors(realm.hero.pos):
                raise SaveFormatError('Saved conquest encounter is not adjacent to its army.')
            active[position] = realm.seat
        if claims != active:
            raise SaveFormatError('Saved encounter claims do not match the active battles.')
        return cls(data['seed'], data['theme'], provinces, realms, data['day'], claims, data['winner'])

    def snapshot(self, seat: int) -> dict:
        """Public province information and only the authenticated player's private realm."""
        if type(seat) is not int or seat not in (0, 1):
            raise CommandError('Unknown realm.')
        other = self.realms[1 - seat]
        return json.loads(json.dumps({
            'day': self.day, 'seat': seat, 'winner': self.winner,
            'realm': _realm_data(self.realms[seat]),
            'provinces': [asdict(self.provinces[pos]) for pos in sorted(self.provinces)],
            'opponent': {'seat': other.seat, 'capital': other.capital, 'hero_pos': other.hero.pos,
                         'ready': other.ready, 'in_battle': other.battle is not None},
            'claims': [{'pos': pos, 'seat': player} for pos, player in sorted(self.claims.items())],
        }))
