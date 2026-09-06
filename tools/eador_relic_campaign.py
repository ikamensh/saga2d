"""Earn active relics through public campaign commands and enter their later demonstrations."""
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure, crossing_route


def earn_censer(state=None, *, orders_type=AdventureOrders):
    """Recover the Censer with a paid Warden/Acolyte army and a real guided escape."""
    state = prepare_adventure(state=state)
    play = crossing_route(state, 'guided', orders_type=orders_type)
    assert play.battle.outcome_reason == 'escape'
    state = play.state
    finish_battle(state)
    assert 'veil_censer' in state.inventory
    return state


def prepare_censer_watch(state=None, *, orders_type=AdventureOrders):
    """Equip the earned Censer in camp, recover and enter the unclaimed Watch."""
    state = earn_censer(state, orders_type=orders_type)
    state.equip('veil_censer')
    for _ in range(32):
        march_to(state, (0, -2))
        if state.actions_left and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            break
        rest(state)
    else:
        raise AssertionError('Could not reach the Watch recovered with the earned Censer')
    state.explore()
    assert state.battle_encounter == 'border_watch'
    return state
