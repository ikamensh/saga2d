"""A reproducible public-command policy for regression tests and world audits.

This development tool explores an itinerary, invests, reacts to a visible rival,
then attempts Duskspire. It is neither the game's opponent nor optimal play.
"""
from dataclasses import dataclass

from eador.model import BUILDINGS, State


@dataclass
class CampaignMetrics:
    battles: int = 0
    lost_troops: int = 0
    battle_hp_attrition: int = 0
    mana_spent: int = 0
    defeats: int = 0
    end_turns: int = 0
    recovery_turns: int = 0
    hp_recovered: int = 0
    mana_recovered: int = 0
    recruitment_gold: int = 0
    building_gold: int = 0


def finish_battle(state, metrics=None):
    """Resolve real tactics; measure net battle wounds before advancement can heal."""
    metrics = metrics or CampaignMetrics()
    battle = state.battle
    before = {u.id: u.hp for u in battle.units if u.team == 'player'}
    mana = battle.mana
    for _ in range(80):
        if battle.outcome:
            break
        battle.auto_turn()
    metrics.battles += 1
    metrics.lost_troops += sum(u.id != 0 and u.hp == 0 for u in battle.units if u.team == 'player')
    metrics.battle_hp_attrition += sum(max(0, hp - battle.unit(uid).hp) for uid, hp in before.items())
    metrics.mana_spent += mana - battle.mana
    metrics.defeats += battle.outcome == 'enemy'
    result = state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    if state.inventory and state.hero.relic is None:
        state.equip(state.inventory[0])
    return result


def provision_army(state, metrics=None):
    """Invest rewards in healing and durable troops, using a recovered merchant relic."""
    metrics = metrics or CampaignMetrics()
    if state.status != 'playing':
        return
    priorities = ['mage_tower', 'temple'] if state.hero.hero_class == 'Wizard' else ['temple']
    for building in priorities:
        spec = BUILDINGS[building]
        if building not in state.buildings and state.gold >= spec.cost and state.crystals >= spec.crystals:
            before = state.gold
            state.build(building)
            metrics.building_gold += before - state.gold
    battle_relic = state.hero.relic
    if 'merchant_seal' in state.inventory and state.hero.relic != 'merchant_seal':
        state.equip('merchant_seal')
    while state.gold >= state.recruit_cost('swordsman') and len(state.hero.army) < state.hero.max_army:
        before = state.gold
        state.recruit('swordsman')
        metrics.recruitment_gold += before - state.gold
    if state.hero.relic != battle_relic:
        state.equip(battle_relic)


def march_to(state, destination, metrics=None):
    """Follow a route, resolving real encounters and refilling actions when needed."""
    metrics = metrics or CampaignMetrics()
    for _ in range(24):
        if state.hero.pos == destination or state.status != 'playing':
            return
        if not state.actions_left:
            rest(state, defend=False, metrics=metrics)
            if state.status != 'playing':
                return
        state.travel(state.grid.path(state.hero.pos, destination)[1])
        if state.battle:
            finish_battle(state, metrics)
    raise AssertionError('The army could not reach its destination.')


def rest(state, defend=True, metrics=None):
    """A visible approaching army calls for interception before another leisurely rest."""
    metrics = metrics or CampaignMetrics()
    if defend and state.rival.army and state.grid.distance(state.rival.pos, (-2, 0)) <= 2:
        march_to(state, state.rival.pos, metrics)
    if state.status == 'playing':
        before = {t.id: t.hp for t in state.hero.army}
        hero_hp, mana = state.hero.hp, state.hero.mana
        state.end_turn()
        metrics.end_turns += 1
        metrics.hp_recovered += max(0, state.hero.hp - hero_hp) + sum(
            max(0, t.hp - before[t.id]) for t in state.hero.army)
        metrics.mana_recovered += state.hero.mana - mana
        if state.battle:
            finish_battle(state, metrics)


def play_campaign(state, route=None, metrics=None):
    """Explore and invest along a route that includes both capitals, then try to win."""
    metrics = metrics or CampaignMetrics()
    if 'barracks' not in state.buildings:
        state.build('barracks')
        metrics.building_gold += BUILDINGS['barracks'].cost
    if state.gold >= state.recruit_cost('swordsman') and len(state.hero.army) < state.hero.max_army:
        before = state.gold
        state.recruit('swordsman')
        metrics.recruitment_gold += before - state.gold
    for province in (route or state.grid.path(state.hero.pos, (2, 0)))[:-1]:
        if state.status != 'playing':
            return state
        if province != state.hero.pos:
            march_to(state, province, metrics)
            if state.status != 'playing':
                return state
            rest(state, metrics=metrics)
            provision_army(state, metrics)
        march_to(state, province, metrics)
        if state.status != 'playing':
            return state
        if not state.provinces[province].explored:
            if not state.actions_left:
                rest(state, metrics=metrics)
                march_to(state, province, metrics)
            if state.status != 'playing':
                return state
            state.explore()
            finish_battle(state, metrics)
        rest(state, metrics=metrics)
        provision_army(state, metrics)
    for _ in range(24):
        if state.status != 'playing':
            break
        provision_army(state, metrics)
        missing_health = max([state.hero.max_hp - state.hero.hp] +
                             [troop.max_hp - troop.hp for troop in state.hero.army])
        if missing_health > 6 or state.hero.mana < state.hero.max_mana - 4:
            metrics.recovery_turns += 1
            rest(state, metrics=metrics)
            continue
        state.travel(state.grid.path(state.hero.pos, (2, 0))[1])
        if state.battle:
            finish_battle(state, metrics)
        assert len({t.id for t in state.hero.army}) == len(state.hero.army)
        assert all(0 < t.hp <= t.max_hp for t in state.hero.army)
        assert 0 < state.hero.hp <= state.hero.max_hp
        assert 0 <= state.hero.mana <= state.hero.max_mana
        state = State.from_json(state.to_json())
        if state.status == 'playing':
            rest(state, metrics=metrics)
    return state
