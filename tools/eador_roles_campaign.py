"""Public paid preparation for a sustain, mobile-fire and rescue formation."""
from eador.model import BUILDINGS, State
from tools.eador_campaign import finish_battle, march_to, rest


def prepare_support_watch(state=None):
    """Buy all three roles and reach the Watch; accepts a model or the real-input adapter."""
    state = State.new(7) if state is None else state
    state.build('barracks')
    state.recruit('warden')
    state.explore()
    finish_battle(state)
    for destination in ((-1, -1), (0, -2)):
        march_to(state, destination)
        rest(state)
    for building, kind in (('temple', 'healer'), ('archery', 'ranger')):
        while state.gold < BUILDINGS[building].cost:
            rest(state)
        state.build(building)
        while state.gold < state.recruit_cost(kind):
            rest(state)
        state.recruit(kind)
    while max([state.hero.max_hp - state.hero.hp] + [t.max_hp - t.hp for t in state.hero.army]):
        rest(state)
    march_to(state, (0, -2))
    if not state.actions_left:
        rest(state, defend=False)
    state.explore()
    assert state.battle_encounter == 'border_watch'
    return state
