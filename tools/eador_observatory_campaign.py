"""Purchased Observatory formations and explicit orders, reusable by input adapters."""
from eador.model import BUILDINGS, State, UNITS
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders


def prepare_observatory(state=None):
    state = State.new(7, 'Commander', theme='ruins') if state is None else state
    state.build('barracks'); state.recruit('warden')
    state.explore(); finish_battle(state)
    for destination in ((-1, -1), (-1, 0)):
        march_to(state, destination); rest(state)
    for kind in ('sapper', 'healer'):
        spec = UNITS[kind]
        for _ in range(48):
            assert state.status == 'playing'
            building = BUILDINGS[spec.building]
            if spec.building not in state.buildings and state.gold >= building.cost and state.crystals >= building.crystals:
                state.build(spec.building)
            if spec.building in state.buildings and state.gold >= state.recruit_cost(kind) and state.crystals >= state.recruit_crystal_cost(kind):
                state.recruit(kind)
                break
            rest(state)
        else:
            raise AssertionError(f'Could not fund {spec.name}')
    for _ in range(48):
        march_to(state, (-1, 0))
        if state.actions_left and state.crystals >= 2 and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            return state
        rest(state)
    raise AssertionError('Could not reach the Observatory recovered')


def observatory_route(state, approach, *, orders_type=AdventureOrders):
    state.explore(approach=approach)
    play = orders_type(state)
    defenders = {u.pos: u.id for u in play.battle.units if u.team == 'enemy'}
    guard, east, north, south = (defenders[pos] for pos in ((1, 0), (3, -1), (1, -3), (0, 3)))
    # The paid lane lets the hero reach the hill immediately; Smoke protects
    # the exposed Militia while the hero absorbs the guard's first reaction.
    for uid, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
        play.do('move', uid, pos)
    for uid in (0, 1, 3):
        play.do('attack', uid, guard)
    for uid, pos in ((4, (-1, 0)), (5, (-1, 1)), (6, (-2, 1)), (2, (-1, -1))):
        play.do('move', uid, pos)
    play.do('smoke', 5, (1, -1))
    play.guard_remaining(); play.do('end_turn')
    # Sustain the holder and remove the southern contester; the eastern
    # marksman then advances into that vacated position.
    play.do('cast', 'heal', 0, caster_id=6)
    play.do('move', 5, (-1, 2)); play.do('move', 4, (-1, 1))
    for uid in (5, 4, 0):
        play.do('attack', uid, south)
    for uid in (1, 3):
        play.do('attack', uid, guard)
    play.guard_remaining(); play.do('end_turn')
    # Move through the lane before the healer occupies it. Finish the anchor
    # and second contester, then Pin the surviving northern bowman off the seal.
    for uid, pos in ((5, (1, 1)), (4, (-1, 2)), (2, (-1, 1))):
        play.do('move', uid, pos)
    play.do('attack', 1, guard); play.do('move', 6, (-1, 0))
    play.do('attack', 6, guard); play.do('attack', 5, guard)
    for uid in (0, 4, 2):
        play.do('attack', uid, east)
    play.do('pin', 3, north)
    play.guard_remaining(); play.do('end_turn')
    # Once Pin expires, a body closes the northern bowman's longer route.
    play.do('move', 5, (1, 0))
    play.do('cast', 'heal', 1); play.do('cast', 'heal', 3, caster_id=6)
    play.guard_remaining(); play.do('end_turn')
    return play
