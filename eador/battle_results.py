"""Earned army progression and surviving defenders, separate from world ownership."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from eador.entities import Hero, Province, RuleError, UNITS

if TYPE_CHECKING:
    from eador.battle import Battle


@dataclass(frozen=True)
class ArmyResult:
    casualties: tuple[str, ...]
    hero_levels: tuple[int, ...]


def persist_province_defenders(province: Province, battle: Battle, *, kind: str) -> None:
    """Retain actual enemy survivors after a completed conquest or site attempt.

    Victory by holding or escaping can leave living defenders. Site completion
    and ownership belong to the caller; neither this battle nor its outcome changes.
    """
    if battle.outcome is None:
        raise RuleError('The battle is not finished.')
    if kind not in ('conquest', 'site'):
        raise RuleError('Choose a conquest or site encounter.')
    survivors = [unit for unit in battle.units if unit.team == 'enemy' and unit.hp > 0]
    kinds, health = [unit.kind for unit in survivors], [unit.hp for unit in survivors]
    if kind == 'site':
        province.site_guards, province.site_guard_hp = kinds, health
    else:
        province.guards, province.guard_hp = kinds, health


def apply_army_result(hero: Hero, battle: Battle, *, hero_level_cap: int | None = None,
                      troop_level_cap: int | None = None, team: str = 'player') -> ArmyResult:
    """Mutate the supplied hero/army once from its completed battle on the given side.

    The battle is read-only. The caller owns claims, rewards, choice creation and
    recording/clearing the encounter so its result cannot be applied twice.
    Returned level numbers preserve the caller's ordered advancement messages.
    """
    if battle.outcome is None:
        raise RuleError('The battle is not finished.')
    magic = battle._magic(team)
    hero.hp = battle.unit(magic.hero_id).hp
    hero.mana = magic.mana
    combatants = {unit.source_id if battle.enemy_magic is not None else unit.id: unit
                  for unit in battle.units if unit.team == team}
    casualties, survivors, levels = [], [], []
    for troop in hero.army:
        troop.hp = combatants[troop.id].hp
        if troop.hp <= 0:
            casualties.append(UNITS[troop.kind].name)
        else:
            survivors.append(troop)
    hero.army = survivors
    if battle.outcome == team:
        if hero_level_cap is None or hero.level < hero_level_cap:
            hero.xp += 8
        while hero.xp >= hero.level * 12 and (hero_level_cap is None or hero.level < hero_level_cap):
            hero.xp -= hero.level * 12
            hero.level += 1
            hero.max_hp += 4
            hero.hp += 4
            hero.max_mana += 2
            hero.mana += 2
            levels.append(hero.level)
        for troop in survivors:
            if troop_level_cap is None or troop.level < troop_level_cap:
                troop.xp += 3
            while troop.xp >= troop.level * 6 and (troop_level_cap is None or troop.level < troop_level_cap):
                troop.xp -= troop.level * 6
                troop.level += 1
                troop.max_hp += 4
                troop.hp += 4
        hero.hp = min(hero.max_hp, hero.hp + 6 * hero.skill_ranks.get('vigor', 0))
    else:
        hero.hp = max(hero.hp, hero.max_hp // 3)
    return ArmyResult(tuple(casualties), tuple(levels))
