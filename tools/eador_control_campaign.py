"""Ordinary purchases and travel for the new control/flight encounter demonstrations."""
from eador.model import BUILDINGS, State, UNITS
from tools.eador_campaign import finish_battle, march_to, rest


def prepare_control_watch(state=None, *, kinds=None):
    """Fund a control retinue and reach the unexplored Watch; accepts a real-input adapter."""
    state = State.new(7) if state is None else state
    kinds = tuple(kinds) if kinds is not None else (('sapper', 'adept', 'skyrider')
                                                   if state.hero.hero_class == 'Commander' else ('sapper', 'adept'))
    state.explore(); finish_battle(state)
    state.build('market')
    for destination in ((-1, -1), (0, -2)):
        march_to(state, destination); rest(state)
    for kind in kinds:
        spec = UNITS[kind]
        for _ in range(48):
            assert state.status == 'playing', 'The control economy lost its capital.'
            if spec.building not in state.buildings:
                building = BUILDINGS[spec.building]
                if state.gold >= building.cost and state.crystals >= building.crystals:
                    state.build(spec.building)
            if spec.building in state.buildings and state.gold >= state.recruit_cost(kind) and state.crystals >= state.recruit_crystal_cost(kind):
                state.recruit(kind)
                break
            rest(state)
        else:
            raise AssertionError(f'Could not fund {spec.name}.')
    for _ in range(48):
        march_to(state, (0, -2))
        if state.actions_left and all(t.hp == t.max_hp for t in state.hero.army) and state.hero.hp == state.hero.max_hp:
            state.explore()
            assert state.battle_encounter == 'border_watch'
            return state
        rest(state)
    raise AssertionError('Could not reach the Watch recovered.')


def watch_control_route(state=None, *, smoke=True, orders_type=None):
    """A bought seven-body formation screens the seal, repulses its contester and closes the flank."""
    from tools.eador_extraction_campaign import AdventureOrders
    play = (orders_type or AdventureOrders)(prepare_control_watch() if state is None else state)
    for uid, pos in ((1, (1, 0)), (3, (0, -1)), (2, (0, 0)), (6, (2, -1)),
                     (4, (-1, 1)), (5, (-1, 0)), (0, (-1, -1))):
        play.do('move', uid, pos)
    for uid in (1, 3, 6):
        play.do('attack', uid, play.enemy('pikeman'))
    if smoke:
        # Screen the approaching Archer's contesting hex, not the army's firing lane.
        play.do('smoke', 4, (0, 1))
    play.guard_remaining(); play.do('end_turn')
    for uid in (1, 3, 6):
        play.do('attack', uid, play.enemy('brigand'))
    play.do('move', 2, (1, -1)); play.do('move', 5, (0, 0))
    play.do('repulse', 5, play.enemy('archer'))
    play.do('move', 4, (0, 1)); play.do('move', 0, (-1, 0))
    play.guard_remaining(); play.do('end_turn')
    # Flight crosses the occupied formation to close its last rough-ground flank.
    play.do('move', 6, (-1, 1))
    play.guard_remaining(); play.do('end_turn')
    return play
