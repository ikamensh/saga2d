"""Earn active relics through public campaign commands and enter their later demonstrations."""
from eador.model import BUILDINGS
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


def prepare_censer_watch(state=None, *, orders_type=AdventureOrders, ranger=False):
    """Equip the earned Censer in camp, recover and enter the unclaimed Watch."""
    state = earn_censer(state, orders_type=orders_type)
    if ranger:
        for _ in range(32):
            if 'archery' not in state.buildings and state.gold >= BUILDINGS['archery'].cost:
                state.build('archery')
            if 'archery' in state.buildings and state.gold >= state.recruit_cost('ranger'):
                state.recruit('ranger')
                break
            rest(state)
        else:
            raise AssertionError('Could not fund the Censer formation’s Ranger')
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


def censer_watch_route(state=None, *, smoke=True, orders_type=AdventureOrders):
    """Screen the Archer's approach, then seal the ring with an earned support retinue."""
    play = orders_type(prepare_censer_watch(ranger=True) if state is None else state)
    for uid, pos in ((1, (1, 0)), (3, (0, -1)), (2, (0, 0)), (6, (0, 1)),
                     (4, (-1, 0)), (0, (-1, 1)), (5, (-2, 0))):
        play.do('move', uid, pos)
    for uid in (1, 3):
        play.do('attack', uid, play.enemy('pikeman'))
    if smoke:
        play.do('smoke', 0, (0, 2))
    play.guard_remaining(); play.do('end_turn')
    play.after_screen_hp = sum(u.hp for u in play.battle.units if u.team == 'player')
    play.do('attack', 6, play.enemy('pikeman'))
    play.do('move', 1, (1, -1)); play.do('move', 6, (1, 0))
    play.do('swap', 4, 2); play.do('move', 0, (0, 1)); play.do('move', 5, (-1, 1))
    play.guard_remaining(); play.do('end_turn')
    play.do('cast', 'heal', 2, caster_id=5)
    play.guard_remaining(); play.do('end_turn')
    return play
