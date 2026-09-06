"""Purchased Pack Hunt armies and explicit routes reusable through native input."""
from eador.model import State
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure


def prepare_pack_hunt(hero='Commander', *, support='ranger', state=None):
    state = prepare_adventure(hero, 'elderwild', support=support, state=state)
    return _recover_at_hunt(state)


def prepare_hunt_spears(state=None):
    """A Warrior buys two Pikemen through western conquest, without a second building."""
    state = State.new(7, 'Warrior', theme='elderwild') if state is None else state
    state.build('barracks'); state.recruit('pikeman')
    state.explore(); finish_battle(state)
    for pos in ((-1, -1), (-1, 0)):
        march_to(state, pos); rest(state)
    state.recruit('pikeman')
    return _recover_at_hunt(state)


def _recover_at_hunt(state):
    for _ in range(32):
        march_to(state, (-1, 1))
        if state.actions_left and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            return state
        rest(state)
    raise AssertionError('Could not reach the Pack Hunt with a recovered purchased army')


def hunt_route(state, approach, *, orders_type=AdventureOrders):
    """The seed-seven Commander uses the same Warden/Ranger army for both deployments."""
    state.explore(approach=approach)
    play = orders_type(state)
    defenders = {u.pos: u.id for u in play.battle.units if u.team == 'enemy'}
    east, north, deep, rear, tail, south = (defenders[pos] for pos in (
        (1, -1), (2, -1), (2, 1), (-3, 2), (-3, 3), (1, 1)))
    if approach == 'lure':
        play.do('attack', 5, east)
        play.do('move', 2, (3, -2)); play.do('move', 0, (2, -2)); play.do('attack', 0, east)
        play.do('move', 3, (1, -3)); play.do('attack', 3, north); play.do('attack', 2, north)
        play.do('move', 5, (2, -3))
        play.guard_remaining(); play.do('end_turn')
        play.do('attack', 5, rear); play.do('attack', 3, rear)
        play.do('attack', 4, deep); play.do('attack', 0, south); play.do('attack', 1, tail)
    else:
        play.do('attack', 5, rear); play.do('move', 5, (-1, -2))
        play.do('move', 0, (-3, 1)); play.do('attack', 0, rear)
        play.do('attack', 3, tail); play.do('move', 2, (-2, 3)); play.do('attack', 2, tail)
        play.do('move', 4, (-1, 1))
        play.guard_remaining(); play.do('end_turn')
        play.do('attack', 1, east)
        play.do('move', 5, (1, -2)); play.do('attack', 5, north)
        play.do('attack', 4, north); play.do('move', 0, (-1, 0)); play.do('attack', 0, north)
        play.do('attack', 3, south); play.do('attack', 2, south)
        play.do('end_turn'); play.do('attack', 3, deep)
    return play


def spear_hunt_route(state, *, orders_type=AdventureOrders):
    """A cheaper Warrior formation clears the free approach using two spear screens."""
    state.explore(approach='compact')
    play = orders_type(state)
    defenders = {u.pos: u.id for u in play.battle.units if u.team == 'enemy'}
    east, north, deep, rear, tail, south = (defenders[pos] for pos in (
        (1, -1), (2, -1), (2, 1), (-3, 2), (-3, 3), (1, 1)))
    play.do('move', 2, (-2, 3)); play.do('move', 0, (-2, 2)); play.do('attack', 0, tail)
    play.do('move', 5, (-1, 0)); play.do('guard', 5)
    play.do('move', 4, (-3, 1)); play.do('attack', 4, rear); play.do('attack', 3, rear)
    play.guard_remaining(); play.do('end_turn')
    play.do('move', 3, (-3, 3)); play.do('attack', 3, deep); play.do('attack', 2, deep)
    play.do('move', 4, (-1, 1)); play.do('attack', 4, south); play.do('attack', 0, south)
    play.do('attack', 1, east); play.do('guard', 5)
    play.do('end_turn')
    play.do('attack', 5, north); play.do('attack', 1, north)
    play.do('move', 3, (-2, 1)); play.do('attack', 3, north)
    return play
