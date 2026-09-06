"""Purchased Pack Hunt armies and explicit routes reusable through native input."""
from tools.eador_campaign import march_to, rest
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure


def prepare_pack_hunt(hero='Commander', *, support='ranger', state=None):
    state = prepare_adventure(hero, 'elderwild', support=support, state=state)
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
