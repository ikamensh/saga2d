"""One realm's upkeep and recovery, independent of the world's turn or opponents."""
from dataclasses import dataclass

from eador.difficulty import RecoveryPreview
from eador.model import Hero, Troop, UNITS


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
