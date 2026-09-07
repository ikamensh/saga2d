"""Paid Aerie preparations and manual landing-control plans for input adapters."""
from eador.model import BUILDINGS, State, UNITS
from tools.eador_campaign import finish_battle, march_to, rest, site_position
from tools.eador_extraction_campaign import AdventureOrders


def prepare_aerie(hero_class='Commander', *, party='flight', state=None, budget=None):
    if party not in ('flight', 'ground'):
        raise ValueError('Choose the flight or ground preparation.')
    state = State.new(7, hero_class, theme='ruins') if state is None else state
    state.explore(); finish_battle(state, budget=budget)
    state.build('market')
    for destination in ((-1, -1), (-1, 0)):
        march_to(state, destination, budget=budget); rest(state, budget=budget)
    kinds = ('pikeman', 'adept', 'skyrider') if party == 'flight' else (
        ('pikeman', 'warden', 'archer') if state.hero.hero_class == 'Commander' else ('pikeman', 'warden'))
    for kind in kinds:
        spec = UNITS[kind]
        for _ in range(48):
            assert state.status == 'playing', 'The Aerie economy lost its capital.'
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
    destination = site_position(state, 'aerie_raid')
    for _ in range(48):
        assert state.status == 'playing', 'The Aerie preparation lost its capital.'
        ready = (state.actions_left and state.hero.hp == state.hero.max_hp
                 and all(t.hp == t.max_hp for t in state.hero.army))
        if state.hero.pos == destination and ready:
            return state
        threat = state.rival.army and state.grid.distance(state.rival.pos, (-2, 0)) <= 2
        if threat or not ready:
            rest(state, budget=budget)
            continue
        # Recover between conquests instead of carrying the previous fight's wounds forward.
        march_to(state, state.grid.path(state.hero.pos, destination)[1], budget=budget)
    raise AssertionError('Could not reach the Aerie recovered.')


def aerie_western_route(state, *, heal=False, orders_type=AdventureOrders):
    state.explore(approach='western')
    p = orders_type(state)
    north, rear = [u.id for u in p.battle.units if u.team == 'enemy' and u.kind == 'skyrider']
    bow, pike = p.enemy('archer'), p.enemy('pikeman')
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 3, rear)
    p.do('move', 5, (-3, 3)); p.do('repulse', 5, rear)
    p.do('move', 4, (-2, 3)); p.do('guard', 4)
    p.do('move', 2, (-2, 2))
    p.do('move', 6, (2, 0)); p.do('attack', 6, bow)
    if heal:
        p.do('cast', 'heal', 1)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 5, rear)
    p.do('attack', 3, north)
    p.do('move', 6, (1, -1)); p.do('attack', 6, north)
    p.do('move', 1, (0, -1)); p.do('guard', 1)
    p.do('move', 2, (-1, 1)); p.do('attack', 2, pike)
    p.do('move', 0, (-1, 0)); p.do('cast', 'bolt', bow)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 3, pike); p.do('attack', 0, pike)
    return p


def aerie_northern_route(state, *, orders_type=AdventureOrders):
    """Kill the nearby flyer before it acts, then open a corridor for the rear rescue."""
    state.explore(approach='northern')
    p = orders_type(state)
    north, rear = [u.id for u in p.battle.units if u.team == 'enemy' and u.kind == 'skyrider']
    bow, pike = p.enemy('archer'), p.enemy('pikeman')
    for uid in (4, 3, 5):
        p.do('attack', uid, north)
    p.do('cast', 'bolt', north)
    p.guard_remaining(); p.do('end_turn')
    p.do('move', 2, (-3, 1)); p.do('attack', 2, rear)
    p.do('attack', 3, rear)
    p.do('move', 6, (1, -1)); p.do('attack', 6, bow)
    # The flyer vacates the rear, letting the hero open the Adept's ground path.
    p.do('move', 0, (-3, 0)); p.do('cast', 'heal', 4)
    p.do('move', 5, (-2, 0)); p.do('attack', 5, rear)
    p.do('attack', 1, pike)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 6, bow); p.do('attack', 3, pike)
    if p.battle.unit(pike).alive:
        p.do('attack', 5, pike)
    if p.battle.unit(bow).alive:
        # A tougher earned flyer can divert enemy fire, leaving this bow unwounded
        # by retaliation. The ready Pikeman crosses the cleared northern lane.
        p.do('move', 4, (2, -2)); p.do('attack', 4, bow)
    return p


def aerie_scout_route(state, *, orders_type=AdventureOrders):
    """A smaller ground party focuses the two landings, then swaps out its wounded front."""
    state.explore(approach='western')
    p = orders_type(state)
    north, rear = [u.id for u in p.battle.units if u.team == 'enemy' and u.kind == 'skyrider']
    bow, pike = p.enemy('archer'), p.enemy('pikeman')
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 5, rear); p.do('attack', 3, rear)
    p.do('move', 2, (-2, 1)); p.do('move', 0, (-2, 0)); p.do('attack', 0, rear)
    p.do('move', 4, (-3, 3)); p.do('attack', 4, rear)
    p.guard_remaining(); p.do('end_turn')
    p.do('attack', 3, north); p.do('attack', 0, north)
    p.do('move', 5, (-1, 1)); p.do('swap', 5, 1)
    p.do('move', 4, (-2, 2))
    p.guard_remaining(); p.do('end_turn')
    p.do('move', 3, (-2, -1)); p.do('attack', 3, pike); p.do('attack', 5, pike)
    p.do('cast', 'heal', 1); p.do('move', 1, (0, 0))
    p.guard_remaining(); p.do('end_turn')
    p.do('move', 5, (0, -1)); p.do('move', 0, (-1, -1)); p.do('attack', 0, bow)
    p.do('move', 3, (-1, 0)); p.do('attack', 3, bow)
    p.do('move', 1, (1, 0)); p.do('attack', 1, bow)
    return p


def aerie_failed_sortie(state, *, orders_type=AdventureOrders):
    """Expose the flyer, then record the consequences of refusing to advance against the bow."""
    state.explore(approach='western')
    p = orders_type(state)
    p.do('move', 6, (2, 0)); p.do('attack', 6, p.enemy('archer'))
    p.guard_remaining(); p.do('end_turn')
    for _ in range(80):
        if p.battle.outcome:
            return p
        p.guard_remaining(); p.do('end_turn')
    raise AssertionError('The passive defense did not end.')


def aerie_retry_route(state, *, orders_type=AdventureOrders):
    """The saved retreat roster contains only the wounded bow; it is not regenerated."""
    state.explore(approach='northern')
    p = orders_type(state)
    bow, = [u for u in p.battle.units if u.team == 'enemy']
    assert bow.kind == 'archer' and 0 < bow.hp < bow.max_hp
    p.do('cast', 'bolt', bow.id)
    return p
