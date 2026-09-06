"""Paid extraction preparation and explicit routes, reusable by native input adapters.

These development policies use ordinary game commands. They are demonstrations,
not the opponent or optimal-play rules. Supply an AdventureOrders subclass whose
`do` dispatches real controls to replay the same route through the UI.
"""
from eador.model import BUILDINGS, State
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_roles_campaign import prepare_support_watch


class AdventureOrders:
    def __init__(self, state, *, budget=None):
        self.state, self.orders = state, []
        self.budget = budget

    @property
    def battle(self):
        return self.state.battle

    def do(self, command, *args, **kwargs):
        if self.budget:
            self.budget.checkpoint()
        getattr(self.battle, command)(*args, **kwargs)
        self.orders.append((command, args, kwargs))

    def guard_remaining(self):
        for unit in self.battle.units:
            if unit.alive and unit.team == 'player' and not unit.acted:
                self.do('guard', unit.id)

    def enemy(self, kind):
        return next(u.id for u in self.battle.units if u.team == 'enemy' and u.kind == kind)


def prepared_crossing(state=None, *, budget=None):
    """Buy all three supports, clear their Watch, and travel to the southern crossing."""
    state = prepare_support_watch(state, budget=budget)
    finish_battle(state, budget=budget)
    march_to(state, (0, 2), budget=budget)
    if not state.actions_left:
        rest(state, defend=False, budget=budget)
    return state


def prepare_adventure(hero_class='Commander', theme='frontier', *, support='healer', state=None, budget=None):
    """Pay for a Warden and support through western conquest, then recover at the site."""
    state = State.new(7, hero_class, theme=theme) if state is None else state
    state.build('barracks'); state.recruit('warden')
    state.explore(); finish_battle(state, budget=budget)
    for pos in ((-1, -1), (-1, 0)):
        march_to(state, pos, budget=budget); rest(state, budget=budget)
    building = 'temple' if support == 'healer' else 'archery'
    for _ in range(48):
        assert state.status == 'playing'
        if building not in state.buildings and state.gold >= BUILDINGS[building].cost:
            state.build(building)
        if building in state.buildings and state.gold >= state.recruit_cost(support):
            state.recruit(support)
            break
        rest(state, budget=budget)
    else:
        raise AssertionError('Could not fund support')
    destination = (0, 2) if theme == 'frontier' else (-1, -1)
    for _ in range(48):
        march_to(state, destination, budget=budget)
        if state.actions_left and all(t.hp == t.max_hp for t in state.hero.army) and state.hero.hp == state.hero.max_hp:
            return state
        rest(state, budget=budget)
    raise AssertionError('Could not reach the adventure recovered')


def crossing_route(state, approach, *, orders_type=AdventureOrders):
    state.explore(approach=approach)
    play = orders_type(state)
    pikeman, brigand = play.enemy('pikeman'), play.enemy('brigand')
    if approach == 'guided':
        play.do('move', 1, (2, 0)); play.do('attack', 1, brigand)
        play.do('move', 4, (2, 1)); play.do('attack', 4, brigand)
        play.do('move', 3, (0, 0)); play.do('pin', 3, pikeman)
        play.do('move', 0, (1, 2))
        if play.battle.unit(brigand).alive:
            play.do('attack', 0, brigand)
        play.do('move', 5, (0, 1))
        if len(state.hero.army) == 6:
            play.do('move', 6, (-1, 1))
        play.do('move', 2, (-1, 2))
        play.guard_remaining(); play.do('end_turn')
        play.do('cast', 'heal', 3, caster_id=5)
        if len(state.hero.army) == 6:
            play.do('attack', 6, pikeman); play.do('move', 6, (0, -1))
        play.do('move', 4, (3, 0)); play.do('move', 0, (2, 1))
    else:
        ranger = next(u.id for u in play.battle.units if u.team == 'player' and u.kind == 'ranger')
        healer = next((u.id for u in play.battle.units if u.team == 'player' and u.can_heal), None)
        play.do('move', 1, (1, 0))
        if play.battle.unit(brigand) in play.battle.targets(ranger):
            play.do('attack', ranger, brigand); play.do('move', ranger, (-1, 1))
        else:
            play.do('move', ranger, (-1, 1)); play.do('attack', ranger, brigand)
        play.do('move', 3, (0, 0)); play.do('attack', 3, brigand)
        play.do('attack', 1, brigand)
        play.do('move', 4, (0, 1)); play.do('move', 0, (-1, 0))
        play.do('move', 2, (-1, 2))
        if healer is not None:
            play.do('move', healer, (-2, 0))
        play.guard_remaining(); play.do('end_turn')
        if state.hero.hero_class in ('Commander', 'Warrior'):
            assert play.battle.unit(0).pinned
        play.do('move', 1, (3, 0)); play.do('move', 3, (0, -1)); play.do('pin', 3, pikeman)
        play.do('move', 4, (2, 1)); play.do('move', 0, (0, 0))
        if play.battle.unit(0).hp < play.battle.unit(0).max_hp:
            play.do('cast', 'heal', 0, caster_id=healer)
        play.guard_remaining(); play.do('end_turn')
        play.do('move', 1, (3, -1)); play.do('move', 4, (3, 0)); play.do('move', 0, (2, 0))
    play.do('swap', 4, 0)
    assert not play.battle.unit(0).acted and play.battle.outcome is None
    play.do('evacuate')
    return play


def cache_route(state, approach, *, orders_type=AdventureOrders):
    state.explore(approach=approach)
    play = orders_type(state)
    wolf = next(u.id for u in play.battle.units if u.team == 'enemy' and u.pos == (-3, 0))
    play.do('move', 3, (-3, 2)); play.do('attack', 3, wolf)
    play.do('move', 4, (-2, 0)); play.do('attack', 4, wolf)
    if play.battle.unit(wolf).alive:
        play.do('move', 5, (-1, -1)); play.do('attack', 5, wolf)
    if (-3, 1) in play.battle.reachable(0):
        play.do('move', 0, (-3, 1))
    else:
        play.do('move', 0, (-2, 1))
        play.guard_remaining(); play.do('end_turn')
        if play.battle.unit(0).hp < play.battle.unit(0).max_hp:
            # The forest blocks this diagonal: step into the western lane before healing.
            if play.battle.unit(0) not in play.battle.spell_targets('heal', caster_id=5):
                play.do('move', 5, (-1, 0))
            play.do('cast', 'heal', 0, caster_id=5)
        play.do('move', 4, (-3, 1)); play.do('swap', 4, 0)
    play.do('evacuate')
    return play
