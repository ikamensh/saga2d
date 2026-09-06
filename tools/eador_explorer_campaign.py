"""Purchased split-party preparations and public orders for native input adapters."""
from eador.model import BUILDINGS, State, UNITS
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders


def prepare_explorer(hero_class='Commander', *, support='ranger', collect_boots=False, state=None):
    state = State.new(7, hero_class) if state is None else state
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
    if support is not None:
        building_id = UNITS[support].building
        building = BUILDINGS[building_id]
        for _ in range(48):
            assert state.status == 'playing'
            if building_id not in state.buildings and state.gold >= building.cost and state.crystals >= building.crystals:
                state.build(building_id)
            if building_id in state.buildings and state.gold >= state.recruit_cost(support) and state.crystals >= state.recruit_crystal_cost(support):
                state.recruit(support)
                break
            rest(state)
        else:
            raise AssertionError('Could not fund the explorer escort')
    # Develop the western road before crossing into the optional northern site.
    for pos in ((-1, 1), (-1, 2), (0, -1)):
        march_to(state, pos)
        if pos == (-1, 2) and collect_boots:
            if not state.actions_left:
                rest(state); march_to(state, pos)
            state.explore(); finish_battle(state)
    for _ in range(48):
        march_to(state, (0, -1))
        if state.actions_left and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army) and (support != 'healer' or state.hero.mana >= 4):
            return state
        rest(state)
    raise AssertionError('Could not reach the Explorer with the purchased party recovered')


def explorer_route(state, approach='north', *, orders_type=AdventureOrders):
    """Commander and Ranger clear their road while the western troops screen the exit."""
    state.explore(approach=approach)
    play = orders_type(state)
    enemies = {u.kind: u.id for u in play.battle.units if u.team == 'enemy'}
    play.do('attack', 5, enemies['archer'])
    play.do('move', 0, (2, -2)); play.do('attack', 0, enemies['archer'])
    play.do('move', 5, (0, -2))
    if approach == 'north':
        play.do('move', 3, (-1, -1)); play.do('attack', 3, enemies['pikeman'])
        for uid, pos in ((4, (-1, 0)), (1, (-1, 1)), (2, (-2, 2))):
            play.do('move', uid, pos)
    else:
        for uid, pos in ((4, (-3, 1)), (3, (-2, 1)), (1, (-3, 2)), (2, (-2, 2))):
            play.do('move', uid, pos)
        play.do('attack', 3, enemies['guard'])
    play.guard_remaining(); play.do('end_turn')
    play.do('move', 5, (-2, -1)); play.do('move', 0, (-1, -2))
    if approach == 'north':
        play.do('move', 1, (-3, 2)); play.do('move', 3, (-2, 1))
    play.do('attack', 3, enemies['guard'])
    if approach == 'north':
        play.do('move', 4, (-3, 1))
    else:
        play.do('swap', 4, 3)  # Extract the exposed Archer before the next enemy phase.
    play.guard_remaining(); play.do('end_turn')
    play.do('attack', 5, enemies['pikeman']); play.do('move', 5, (0, -2))
    if approach == 'south':
        play.do('move', 3, (-2, 0)); play.do('move', 4, (-3, 1))
    play.do('move', 0, (-3, 0)); play.do('swap', 4, 0); play.do('evacuate')
    return play


def explorer_healer_route(state, *, orders_type=AdventureOrders):
    """A Warrior clears the bowman without mobile fire; its Acolyte sustains the screen."""
    state.explore(approach='north')
    play = orders_type(state)
    enemies = {u.kind: u.id for u in play.battle.units if u.team == 'enemy'}
    play.do('move', 0, (2, -2)); play.do('attack', 0, enemies['archer'])
    play.do('move', 5, (0, -2))
    play.do('move', 3, (-1, -1)); play.do('attack', 3, enemies['pikeman'])
    for uid, pos in ((4, (-1, 0)), (1, (-1, 1)), (2, (-2, 2))):
        play.do('move', uid, pos)
    play.guard_remaining(); play.do('end_turn')
    play.do('move', 5, (-2, -1)); play.do('cast', 'heal', 2, caster_id=5)
    play.do('move', 0, (-1, -2)); play.do('move', 1, (-3, 2)); play.do('move', 3, (-2, 1))
    play.do('attack', 3, enemies['guard']); play.do('move', 4, (-3, 1))
    play.guard_remaining(); play.do('end_turn')
    play.do('move', 5, (0, -2)); play.do('move', 0, (-3, 0))
    play.do('swap', 4, 0); play.do('evacuate')
    return play


def explorer_scout_route(state, *, orders_type=AdventureOrders):
    """Five bodies: the isolated Scout has no escort and uses earned Pathfinder."""
    state.explore(approach='north')
    play = orders_type(state)
    bowman = play.enemy('archer')
    play.do('move', 3, (0, -3)); play.do('attack', 3, bowman)
    play.do('move', 0, (-1, -2)); play.do('attack', 0, bowman)
    for uid, pos in ((2, (-2, 1)), (1, (-3, 2)), (4, (-3, 1))):
        play.do('move', uid, pos)
    play.guard_remaining(); play.do('end_turn')
    play.do('move', 0, (-3, 0)); play.do('swap', 4, 0); play.do('evacuate')
    return play
