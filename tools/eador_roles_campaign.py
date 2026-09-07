"""Public paid preparation for a sustain, mobile-fire and rescue formation."""
from eador.model import BUILDINGS, State
from tools.eador_campaign import finish_battle, march_to, rest, site_position


def prepare_support_watch(state=None, *, budget=None):
    """Buy all three roles and reach the Watch; accepts a model or the real-input adapter."""
    state = State.new(7) if state is None else state
    watch = site_position(state, 'border_watch')
    state.build('barracks')
    state.recruit('warden')
    state.explore()
    finish_battle(state, budget=budget)
    for destination in ((-1, -1), watch):
        march_to(state, destination, budget=budget)
        rest(state, budget=budget)
    for building, kind in (('temple', 'healer'), ('archery', 'ranger')):
        while state.gold < BUILDINGS[building].cost:
            rest(state, budget=budget)
        state.build(building)
        while state.gold < state.recruit_cost(kind):
            rest(state, budget=budget)
        state.recruit(kind)
    while max([state.hero.max_hp - state.hero.hp] + [t.max_hp - t.hp for t in state.hero.army]):
        rest(state, budget=budget)
    march_to(state, watch, budget=budget)
    if not state.actions_left:
        rest(state, defend=False, budget=budget)
    state.explore()
    assert state.battle_encounter == 'border_watch'
    return state
