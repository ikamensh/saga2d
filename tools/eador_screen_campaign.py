"""Purchased Smuggler Screen parties and manual orders for input adapters."""
from eador.model import BUILDINGS, State
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders


def prepare_screen(hero_class='Commander', *, state=None):
    state = State.new(7, hero_class, theme='elderwild') if state is None else state
    state.build('barracks')
    for _ in range(8):
        if state.gold >= state.recruit_cost('warden'):
            state.recruit('warden')
            break
        rest(state)
    else:
        raise AssertionError('Could not fund the Warden')
    state.explore(); finish_battle(state)
    for pos in ((-1, -1), (-1, 0)):
        march_to(state, pos); rest(state)
    for _ in range(48):
        assert state.status == 'playing'
        if 'archery' not in state.buildings and state.gold >= BUILDINGS['archery'].cost:
            state.build('archery')
        if 'archery' in state.buildings and state.gold >= state.recruit_cost('ranger'):
            state.recruit('ranger')
            break
        rest(state)
    else:
        raise AssertionError('Could not fund the Ranger')
    for pos in ((-1, 1), (-1, 2), (0, -1)):
        march_to(state, pos)
    for _ in range(48):
        march_to(state, (0, -1))
        if state.actions_left and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            return state
        rest(state)
    raise AssertionError('Could not reach the Screen with the purchased party recovered')


def screen_western_route(state, *, heal=False, orders_type=AdventureOrders):
    state.explore(approach='western')
    p = orders_type(state)
    sapper, warden, guard = (p.enemy(kind) for kind in ('sapper', 'warden', 'guard'))
    bows = [u.id for u in p.battle.units if u.team == 'enemy' and u.kind == 'archer']
    north, middle = bows
    p.guard_remaining(); p.do('end_turn')
    p.do('move', 4, (-3, 3)); p.do('attack', 4, guard)
    p.do('move', 2, (-3, 2)); p.do('attack', 2, guard)
    p.do('move', 5, (-1, 3)); p.do('attack', 5, guard)
    p.do('move', 0, (-2, 1)); p.do('attack', 0, guard)
    p.do('attack', 3, north)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 3, north); p.do('attack', 5, sapper); p.do('attack', 0, sapper)
    p.do('attack', 4, guard)
    p.do('move', 1, (-1, 0)); p.do('attack', 1, warden)
    p.do('move', 2, (-1, 1)); p.do('attack', 2, warden)
    p.do('move', 5, (0, 2))
    p.guard_remaining(); p.do('end_turn')
    if heal:
        p.do('cast', 'heal', 1)
    p.do('move', 3, (0, -2)); p.do('attack', 3, warden)
    p.do('move', 5, (1, 1)); p.do('attack', 5, warden)
    p.do('attack', 2, warden)
    p.do('move', 1, (0, 0)); p.do('attack', 1, middle)
    if heal:
        p.guard_remaining(); p.do('end_turn'); p.do('attack', 1, middle)
    else:
        p.do('move', 0, (0, -1)); p.do('attack', 0, middle)
    return p


def screen_northern_route(state, *, orders_type=AdventureOrders):
    """Rally restores a pinned Ranger's unused move; two heals sustain both fronts."""
    state.explore(approach='northern')
    p = orders_type(state)
    sapper, warden, guard = (p.enemy(kind) for kind in ('sapper', 'warden', 'guard'))
    north, middle = [u.id for u in p.battle.units if u.team == 'enemy' and u.kind == 'archer']
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 5, north)
    p.do('move', 1, (0, -2)); p.do('rally', 1, 5); p.do('move', 5, (2, -3))
    p.do('move', 3, (1, -3)); p.do('attack', 3, north)
    p.do('move', 4, (-1, 1)); p.do('attack', 4, guard)
    p.do('move', 2, (-1, 0)); p.do('move', 0, (-1, -1))
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 5, middle); p.do('move', 5, (0, -1)); p.do('cast', 'heal', 5)
    p.do('attack', 3, warden); p.do('move', 1, (1, -2)); p.do('attack', 1, warden)
    p.do('attack', 4, sapper); p.do('move', 2, (0, 0)); p.do('attack', 2, sapper)
    p.guard_remaining(); p.do('end_turn')
    p.do('cast', 'heal', 4)
    p.do('attack', 3, warden); p.do('attack', 5, warden)
    p.do('attack', 1, middle); p.do('attack', 2, middle)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 4, guard); p.do('attack', 5, guard)
    p.do('move', 2, (-1, 2)); p.do('attack', 2, guard)
    p.do('move', 0, (-2, 1)); p.do('attack', 0, guard)
    return p


def screen_scout_route(state, *, orders_type=AdventureOrders):
    """Five bodies concentrate ranged fire before Smoke, then rotate the Ranger back."""
    state.explore(approach='northern')
    p = orders_type(state)
    sapper, warden, guard = (p.enemy(kind) for kind in ('sapper', 'warden', 'guard'))
    north, middle = [u.id for u in p.battle.units if u.team == 'enemy' and u.kind == 'archer']
    p.do('move', 2, (0, 0)); p.do('attack', 2, sapper)
    p.do('move', 5, (0, -1)); p.do('attack', 5, sapper)
    p.do('attack', 3, sapper); p.do('move', 0, (-1, 0)); p.do('attack', 0, sapper)
    p.do('move', 4, (1, -2)); p.do('attack', 4, middle)
    p.guard_remaining(); p.do('end_turn')
    p.do('move', 0, (-1, -1)); p.do('cast', 'heal', 2)
    p.do('attack', 5, middle); p.do('move', 5, (-2, 1))
    p.do('move', 4, (1, -1)); p.do('attack', 4, north)
    p.do('move', 3, (-1, 0)); p.do('attack', 3, north)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 0, warden); p.do('attack', 4, warden)
    p.do('attack', 3, north); p.do('attack', 5, warden)
    p.guard_remaining(); p.do('end_turn')
    p.do('cast', 'heal', 2)
    p.do('attack', 4, warden); p.do('attack', 5, warden)
    p.do('attack', 3, warden); p.do('attack', 2, warden)
    p.guard_remaining(); p.do('end_turn')
    p.do('move', 4, (1, 1)); p.do('attack', 4, guard)
    for uid in (0, 2, 3, 5):
        p.do('attack', uid, guard)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 0, guard); p.do('attack', 3, guard)
    return p
