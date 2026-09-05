"""A reproducible public-command campaign policy shared by regression tests and world audits.

This is development tooling, not the game's automatic opponent or a promise
of optimal play. It explores an itinerary, invests, reacts to a visible rival
and attempts the final stronghold. Callers inspect the returned outcome.
"""
from eador.model import BUILDINGS, State


def finish_battle(state):
    """Resolve a real tactical encounter using the ordinary automatic player."""
    for _ in range(80):
        if state.battle.outcome:
            break
        state.battle.auto_turn()
    result = state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    if state.inventory and state.hero.relic is None:
        state.equip(state.inventory[0])
    return result


def provision_army(state):
    """Invest site rewards in healing, a Wizard's tower, and durable troops."""
    priorities = ['mage_tower', 'temple'] if state.hero.hero_class == 'Wizard' else ['temple']
    for building in priorities:
        spec = BUILDINGS[building]
        if building not in state.buildings and state.gold >= spec.cost and state.crystals >= spec.crystals:
            state.build(building)
    while state.gold >= state.recruit_cost('swordsman') and len(state.hero.army) < state.hero.max_army:
        state.recruit('swordsman')


def march_to(state, destination):
    """Follow a route, resolving real encounters and refilling actions when needed."""
    for _ in range(24):
        if state.hero.pos == destination or state.status != 'playing':
            return
        if not state.actions_left:
            rest(state, defend=False)
        state.travel(state.grid.path(state.hero.pos, destination)[1])
        if state.battle:
            finish_battle(state)
    raise AssertionError('The army could not reach its destination.')


def rest(state, defend=True):
    """A visible approaching army calls for interception before another leisurely rest."""
    if defend and state.rival.army and state.grid.distance(state.rival.pos, (-2, 0)) <= 2:
        march_to(state, state.rival.pos)
    if state.status == 'playing':
        state.end_turn()
        if state.battle:
            finish_battle(state)


def play_campaign(state, route=None):
    """Explore and invest along a route that includes both capitals, then try to win."""
    state.build('barracks')
    state.recruit('swordsman')
    for province in (route or state.grid.path(state.hero.pos, (2, 0)))[:-1]:
        if state.status != 'playing':
            return state
        if province != state.hero.pos:
            march_to(state, province)
            if state.status != 'playing':
                return state
            rest(state)
            provision_army(state)
        march_to(state, province)
        if state.status != 'playing':
            return state
        if not state.provinces[province].explored:
            if not state.actions_left:
                rest(state)
                march_to(state, province)
            state.explore()
            finish_battle(state)
        rest(state)
        provision_army(state)
    for _ in range(24):
        if state.status != 'playing':
            break
        provision_army(state)
        missing_health = max([state.hero.max_hp - state.hero.hp] +
                             [troop.max_hp - troop.hp for troop in state.hero.army])
        if missing_health > 6 or state.hero.mana < state.hero.max_mana - 4:
            rest(state)
            continue
        state.travel(state.grid.path(state.hero.pos, (2, 0))[1])
        if state.battle:
            finish_battle(state)
        assert len({t.id for t in state.hero.army}) == len(state.hero.army)
        assert all(0 < t.hp <= t.max_hp for t in state.hero.army)
        assert 0 < state.hero.hp <= state.hero.max_hp
        assert 0 <= state.hero.mana <= state.hero.max_mana
        state = State.from_json(state.to_json())
        if state.status == 'playing':
            rest(state)
    return state
