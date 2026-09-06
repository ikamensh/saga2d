"""Detached visual facts from one already-resolved tactical command.

These records are ephemeral presentation data. Neither observation nor playback
participates in rules, persistence, or the decision to resolve a battle.
"""
from dataclasses import dataclass

from eador.model import Pos


@dataclass(frozen=True)
class UnitFrame:
    id: int
    pos: Pos
    hp: int
    moved: bool
    acted: bool
    retaliated: bool
    stance: str | None
    pinned: bool
    pin_cooldown: int
    safe_attacks: int
    spent_abilities: tuple[str, ...]


@dataclass(frozen=True)
class BattleFrame:
    units: tuple[UnitFrame, ...]
    mana: int
    round: int
    progress: int
    outcome: str | None
    outcome_reason: str | None
    smoke: tuple[tuple[Pos, str], ...]

    @classmethod
    def capture(cls, battle):
        return cls(tuple(UnitFrame(*(getattr(unit, name) for name in UnitFrame.__dataclass_fields__))
                         for unit in battle.units), battle.mana, battle.round, battle.objective.progress,
                   battle.outcome, battle.outcome_reason,
                   tuple((cloud.pos, cloud.expires_before_team) for cloud in battle.smoke_clouds))

    def unit(self, ident):
        return next(unit for unit in self.units if unit.id == ident)


@dataclass(frozen=True)
class BattleEvent:
    kind: str
    actor_id: int | None
    target_id: int | None
    text: str
    before: BattleFrame
    after: BattleFrame
    path: tuple[Pos, ...] = ()


@dataclass(frozen=True)
class BattleTrace:
    before: BattleFrame
    events: tuple[BattleEvent, ...]
    after: BattleFrame


class _Recorder:
    def __init__(self, battle):
        self.before = self.current = BattleFrame.capture(battle)
        self.events = []

    def emit(self, battle, kind, actor_id=None, target_id=None, *, text='', path=()):
        after = BattleFrame.capture(battle)
        if after != self.current:
            self.events.append(BattleEvent(kind, actor_id, target_id, text, self.current, after, tuple(path)))
            self.current = after

    def finish(self, battle):
        self.emit(battle, 'phase', text='Orders resolved.')
        return BattleTrace(self.before, tuple(self.events), self.current)
