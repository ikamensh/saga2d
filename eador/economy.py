"""One realm's upkeep and recovery, independent of the world's turn or opponents."""
from dataclasses import dataclass
from collections.abc import Collection, Mapping

from saga2d import HexGrid

from eador.difficulty import DifficultySpec, RecoveryPreview
from eador.entities import Hero, Pos, Province, Troop, UNITS


@dataclass(frozen=True)
class IncomePreview:
    gold: int
    crystals: int
    encircled: bool


def income_preview(provinces: Mapping[Pos, Province], *, owner: str, capital: Pos,
                   buildings: Collection[str], rules: DifficultySpec) -> IncomePreview:
    """Quote one owner's production on the shared map; neutral neighbors do not besiege."""
    home = provinces[capital]
    encircled = home.owner == owner and all(
        provinces[pos].owner not in (owner, 'neutral') for pos in HexGrid(provinces).neighbors(capital))
    owned = [province for province in provinces.values() if province.owner == owner]
    production = sum(province.income for province in owned) - (home.income if encircled else 0)
    if 'market' in buildings and not encircled:
        production += 8
    crystals = sum(province.crystals for province in owned) - (home.crystals if encircled else 0)
    return IncomePreview(production * rules.gold_percent // 100, crystals, encircled)


def recovery_preview(hero: Hero, *, buildings: Collection[str], rules: DifficultySpec,
                     available_gold: int, blocked_reason: str | None = None) -> RecoveryPreview:
    """Quote recovery before payment, counting only support troops who can be paid."""
    if blocked_reason is not None:
        return RecoveryPreview(0, 0, 0, blocked_reason)
    departing = {troop.id for troop in unpaid_troops(hero.army, available_gold)}
    recovery = (rules.army_recovery + (3 if 'temple' in buildings else 0)
                + hero.skill_ranks.get('quartermaster', 0)
                + (3 if hero.relic == 'oak_standard' else 0)
                + (2 if any(t.kind == 'healer' and t.id not in departing for t in hero.army) else 0))
    hero_recovery = recovery + 2 + 2 * hero.skill_ranks.get('vigor', 0)
    return RecoveryPreview(min(hero.max_hp - hero.hp, hero_recovery), recovery,
                           min(hero.max_mana - hero.mana, rules.mana_recovery))


@dataclass(frozen=True)
class Settlement:
    gold: int
    crystals: int
    actions_left: int
    log: tuple[str, ...]


def unpaid_troops(army: list[Troop], available_gold: int) -> list[Troop]:
    """Choose actual deserters, preserving experienced troops before fresh recruits."""
    shortfall = sum(UNITS[troop.kind].upkeep for troop in army) - available_gold
    departing = []
    for troop in sorted(army, key=lambda t: (t.level, t.xp, -UNITS[t.kind].upkeep, -t.id)):
        if shortfall <= 0:
            break
        departing.append(troop)
        shortfall -= UNITS[troop.kind].upkeep
    return departing


def settle_realm(hero: Hero, *, gold: int, crystals: int, income: int,
                 crystal_income: int, recovery: RecoveryPreview, turn: int) -> Settlement:
    """Mutate this hero/army and return settled funds, actions and ordered log entries.

    Quote recovery before calling, excluding the support of ``unpaid_troops``.
    The caller owns readiness and applies this once at its world-turn barrier.
    ``turn`` labels the receipt; this function cannot advance a date, province,
    rival, campaign or battle. It does not change the caller's treasury directly.
    """
    log = []
    for deserter in unpaid_troops(hero.army, gold + income):
        hero.army.remove(deserter)
        log.append(f'Unpaid upkeep: level {deserter.level} {UNITS[deserter.kind].name} deserted.')
    earnings = income - sum(UNITS[troop.kind].upkeep for troop in hero.army)
    can_rest = recovery.blocked_reason is None
    if can_rest:
        hero.hp += recovery.hero_hp
        for troop in hero.army:
            troop.hp = min(troop.max_hp, troop.hp + recovery.army_hp)
        hero.mana += recovery.mana
    rest = 'army rests' if can_rest else 'encirclement blocks recovery'
    log.append(f'Turn {turn}: {earnings:+d} gold after upkeep; {rest}.')
    return Settlement(gold + earnings, crystals + crystal_income,
                      3 if hero.hero_class == 'Scout' else 2, tuple(log))
