"""A finite expedition: it marches, pays to refit, and learns from defeats.

All fights use the game's Battle rules. This module chooses operations;
the campaign owns occupation, rewards and the player's encounters.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from saga2d import HexGrid

if TYPE_CHECKING:
    from eador.model import State

Pos = tuple[int, int]
STRONGHOLD = (2, 0)
RECRUIT_COSTS = {'guard': 45, 'archer': 35, 'brigand': 20}
COMPOSITION = ('guard', 'guard', 'archer', 'brigand', 'guard', 'archer')
INTENTS = ('march', 'attack', 'return', 'recruit', 'recover', 'watch', 'defeated')


@dataclass
class RivalTroop:
    id: int
    kind: str
    hp: int
    max_hp: int


@dataclass
class RivalState:
    gold: int = 60
    pos: Pos = (2, -1)
    army: list[RivalTroop] = field(default_factory=list)
    intent: str = 'march'
    target: Pos | None = None
    turns_until_action: int = 3
    next_troop_id: int = 1
    defeats: int = 0

    @classmethod
    def initial(cls) -> RivalState:
        from eador.model import UNITS
        rival = cls()
        for kind in COMPOSITION:
            spec = UNITS[kind]
            rival.army.append(RivalTroop(rival.next_troop_id, kind, spec.hp, spec.hp))
            rival.next_troop_id += 1
        return rival

    @property
    def upkeep(self) -> int:
        return len(self.army) * 2

    def income(self, state: State) -> int:
        return sum(province.income for province in state.provinces.values() if province.owner == 'rival')

    def _recruit_kind(self) -> str | None:
        counts = Counter(troop.kind for troop in self.army)
        desired = Counter()
        for kind in COMPOSITION:
            desired[kind] += 1
            if counts[kind] < desired[kind]:
                return kind
        return None

    def _can_defeat_hero(self, state: State, destination: Pos) -> bool:
        from eador.battle import Battle
        battle = Battle.create(state.hero, [troop.kind for troop in self.army],
                               state.provinces[destination].terrain, state.spells,
                               seed=state.seed + state.turn * 37 + destination[0] * 7 + destination[1],
                               enemy_hp=[troop.hp for troop in self.army])
        while battle.outcome is None:
            battle.auto_turn()
        return battle.outcome == 'enemy'

    def plan(self, state: State, *, delay: int | None = None) -> None:
        if state.status != 'playing':
            self.intent = 'defeated' if state.status == 'victory' else 'watch'
            self.target, self.turns_until_action = None, 0
            return
        if not self.army:
            self.pos = STRONGHOLD
        if self.pos == STRONGHOLD:
            missing = sum(troop.max_hp - troop.hp for troop in self.army)
            kind = self._recruit_kind()
            if missing and self.gold:
                self.intent, self.target, self.turns_until_action = 'recover', STRONGHOLD, 1
                return
            if kind is not None:
                self.intent = 'recruit' if self.gold >= RECRUIT_COSTS[kind] else 'watch'
                self.target, self.turns_until_action = STRONGHOLD, 1
                if delay is not None:
                    self.turns_until_action = delay
                return
        elif len(self.army) < 3 or sum(t.hp for t in self.army) < sum(t.max_hp for t in self.army) * 0.45:
            self.intent, self.target = 'return', state.grid.path(self.pos, STRONGHOLD, cost=lambda pos: 1 if state.provinces[pos].owner == 'rival' else 8)[1]
            self.turns_until_action = 1 if delay is None else delay
            return
        if not self.army:
            self.intent, self.target, self.turns_until_action = 'watch', STRONGHOLD, 1
            return
        avoid_hero = bool(self.defeats) and not self._can_defeat_hero(state, state.hero.pos)
        blocked = (state.hero.pos,) if avoid_hero else ()
        goals = [pos for pos, province in state.provinces.items()
                 if province.owner != 'rival' and pos not in blocked]
        foundries = ((0, -1), (0, 1)) if state.campaign and state.campaign.contract == 'foundries' else ()
        goals.sort(key=lambda pos: (not (pos in foundries and state.provinces[pos].owner == 'player'),
                                   HexGrid.distance(pos, (-2, 0)), HexGrid.distance(self.pos, pos), pos))
        for goal in goals:
            path = state.grid.path(self.pos, goal, blocked=blocked,
                                   cost=lambda pos: 1 if state.provinces[pos].owner == 'rival' else 1 + len(state.provinces[pos].guards) / 2)
            if len(path) < 2:
                continue
            step = path[1]
            self.target = step
            self.intent = 'attack' if state.provinces[step].owner != 'rival' else 'march'
            self.turns_until_action = (1 if self.intent == 'march' else 2) if delay is None else delay
            return
        self.intent, self.target, self.turns_until_action = 'watch', self.pos, 2

    def advance(self, state: State) -> None:
        from eador.model import UNITS
        self.gold += self.income(state) - self.upkeep
        self.turns_until_action = max(0, self.turns_until_action - 1)
        if self.turns_until_action:
            return
        defeats_before = self.defeats
        if self.intent == 'recruit':
            kind = self._recruit_kind()
            if self.pos != STRONGHOLD:
                raise RuntimeError('A rival can only recruit at its stronghold.')
            if kind is not None and self.gold >= RECRUIT_COSTS[kind]:
                spec = UNITS[kind]
                self.gold -= RECRUIT_COSTS[kind]
                self.army.append(RivalTroop(self.next_troop_id, kind, spec.hp, spec.hp))
                self.next_troop_id += 1
                state.log.append(f'The rival paid {RECRUIT_COSTS[kind]} gold to recruit {spec.name} at Duskspire.')
        elif self.intent == 'recover':
            if self.pos != STRONGHOLD:
                raise RuntimeError('A rival can only recover at its stronghold.')
            spent = 0
            for troop in self.army:
                healed = min(troop.max_hp - troop.hp, self.gold)
                troop.hp += healed
                self.gold -= healed
                spent += healed
            state.log.append(f'The rival paid {spent} gold to heal its expedition at Duskspire.')
        elif self.intent in ('march', 'attack', 'return'):
            if self.target == state.hero.pos and self.defeats and not self._can_defeat_hero(state, self.target):
                state.log.append('The rival refused another losing assault and changed its plans.')
            else:
                state._move_rival(self.target)
        if state.battle is None and self.defeats == defeats_before:
            self.plan(state)

    def defeated(self, state: State) -> None:
        self.army.clear()
        self.defeats += 1
        self.pos = STRONGHOLD
        self.plan(state, delay=4)
