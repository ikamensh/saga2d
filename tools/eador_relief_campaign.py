"""Paid Relief journeys, reusable through ordinary model or native input commands."""
from eador.model import BUILDINGS, State, UNITS
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders


def prepare_relief(hero_class='Commander', *, seed=7, difficulty='standard', state=None, budget=None):
    state = State.new(seed, hero_class, difficulty=difficulty) if state is None else state
    target = next(p.pos for p in state.provinces.values() if p.site_kind == 'relief_column')
    state.explore(); finish_battle(state, budget=budget)
    state.build('market')
    for destination in ((-1, -1), (-1, 0)):
        march_to(state, destination, budget=budget); rest(state, budget=budget)
    kinds = ('pikeman', 'warden', 'adept') if state.hero.hero_class == 'Commander' else ('pikeman', 'archer')
    for kind in kinds:
        spec = UNITS[kind]
        for _ in range(48):
            assert state.status == 'playing', 'The Relief preparation lost its capital.'
            if spec.building not in state.buildings:
                building = BUILDINGS[spec.building]
                if state.gold >= building.cost and state.crystals >= building.crystals:
                    state.build(spec.building)
            if spec.building in state.buildings and state.gold >= state.recruit_cost(kind) and state.crystals >= state.recruit_crystal_cost(kind):
                state.recruit(kind)
                break
            rest(state, budget=budget)
        else:
            raise AssertionError(f'Could not fund {spec.name}.')
    for _ in range(48):
        assert state.status == 'playing', 'The Relief preparation lost its capital.'
        threat = state.rival.army and state.grid.distance(state.rival.pos, (-2, 0)) <= 2
        if (threat or not state.actions_left or state.hero.hp < state.hero.max_hp
                or state.hero.mana < state.hero.max_mana or any(t.hp < t.max_hp for t in state.hero.army)):
            rest(state, budget=budget)
            continue
        if state.hero.pos == target:
            return state
        # One action at a time: a distant optional signal cannot skip a capital defense.
        march_to(state, state.grid.path(state.hero.pos, target)[1], budget=budget)
    raise AssertionError('Could not reach the Relief signal recovered.')


def _end(play):
    play.guard_remaining(); play.do('end_turn')


def _strike(play, unit, target):
    """Focus fire stops when the actual earned party has already killed its target."""
    if play.battle.unit(target).alive:
        play.do('attack', unit, target)


def relief_forward_opening(play, *, finish_support=True):
    for uid, pos in ((1, (3, -2)), (0, (0, -1)), (3, (1, -1)), (4, (0, -2)),
                     (6, (1, 0)), (2, (-1, -2))):
        play.do('move', uid, pos)
    play.do('pin', 3, play.enemy('skyrider'))
    play.do('cast', 'bolt', play.enemy('militia'))
    _strike(play, 1, play.enemy('militia'))
    if finish_support:
        _strike(play, 6, play.enemy('militia'))
    _end(play)


def relief_forward_route(state, *, heal=True, orders_type=AdventureOrders):
    state.explore(approach='forward')
    play = orders_type(state)
    relief_forward_opening(play)
    for uid in (1, 3):
        _strike(play, uid, play.enemy('skyrider'))
    if heal:
        play.do('cast', 'heal', 1)
    _end(play)
    return play


def relief_western_route(state, *, heal=True, repulse=True, orders_type=AdventureOrders):
    state.explore(approach='western')
    play = orders_type(state)
    for uid, pos in ((1, (0, -1)), (0, (-1, 0)), (2, (-2, 0)), (3, (-1, -1)),
                     (4, (0, -2)), (5, (-1, 1)), (6, (-2, 1))):
        play.do('move', uid, pos)
    _end(play)
    play.do('move', 3, (-1, -2)); play.do('move', 0, (-1, -1))
    play.do('cast', 'bolt', play.enemy('skyrider'))
    _strike(play, 4, play.enemy('skyrider'))
    _strike(play, 1, play.enemy('militia'))
    play.do('move', 5, (0, 1)); _strike(play, 5, play.enemy('militia'))
    play.do('move', 6, (-1, 0)); _strike(play, 6, play.enemy('militia'))
    _strike(play, 3, play.enemy('guard'))
    _end(play)
    play.do('move', 0, (-2, -1)); play.do('cast', 'bolt', play.enemy('archer'))
    play.do('move', 3, (1, -3)); play.do('move', 4, (0, -3)); play.do('move', 6, (0, -2))
    if repulse:
        play.do('repulse', 6, play.enemy('guard'))
        play.do('move', 1, (1, -2)); play.do('move', 5, (0, -1))
    _end(play)
    if heal:
        play.do('cast', 'heal', 4)
    _end(play)
    return play


def relief_scout_route(state, *, veteran_pin=False, orders_type=AdventureOrders):
    state.explore(approach='forward')
    play = orders_type(state)
    for uid, pos in ((1, (3, -2)), (0, (0, -1)), (3, (1, 0)), (4, (0, -2)),
                     (5, (1, -1)), (2, (-1, -2))):
        play.do('move', uid, pos)
    play.do('pin', 3 if veteran_pin else 5, play.enemy('skyrider'))
    for uid in (0, 1, 5 if veteran_pin else 3):
        _strike(play, uid, play.enemy('militia'))
    _end(play)
    if veteran_pin:
        return play
    play.do('move', 5, (1, -3)); play.do('move', 1, (1, -2))
    for uid in (0, 5, 3):
        _strike(play, uid, play.enemy('skyrider'))
    _end(play)
    return play


def relief_passive_route(state, *, orders_type=AdventureOrders):
    """A purchased seven-body enclosure remains a valid no-mana alternative."""
    state.explore(approach='forward')
    play = orders_type(state)
    for uid, pos in ((3, (1, -3)), (1, (1, -2)), (4, (0, -3)), (6, (0, -1)),
                     (2, (0, -2)), (0, (-1, -2)), (5, (-1, -1))):
        play.do('move', uid, pos)
    while not play.battle.outcome:
        _end(play)
    return play


def relief_failed_support(state, *, orders_type=AdventureOrders):
    """Leaving the wounded support alive restores flight; inaction then loses the Pike and clock."""
    state.explore(approach='forward')
    play = orders_type(state)
    relief_forward_opening(play, finish_support=False)
    while not play.battle.outcome:
        _end(play)
    return play


def relief_retry_route(state, *, orders_type=AdventureOrders):
    """Explicit automatic rounds finish the finite wounded roster after buying a replacement."""
    state.explore(approach='western')
    play = orders_type(state)
    while not play.battle.outcome:
        play.do('auto_turn')
    return play
