"""Earn active relics through public campaign commands and enter their later demonstrations."""
from eador.model import BUILDINGS
from tools.eador_campaign import finish_battle, march_to, rest
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure, crossing_route


def earn_censer(state=None, *, orders_type=AdventureOrders, budget=None):
    """Recover the Censer with a paid Warden/Acolyte army and a real guided escape."""
    state = prepare_adventure(state=state, budget=budget)
    play = crossing_route(state, 'guided', orders_type=orders_type)
    assert play.battle.outcome_reason == 'escape'
    state = play.state
    finish_battle(state, budget=budget)
    assert 'veil_censer' in state.inventory
    return state


def prepare_censer_watch(state=None, *, orders_type=AdventureOrders, ranger=False, budget=None):
    """Equip the earned Censer in camp, recover and enter the unclaimed Watch."""
    state = earn_censer(state, orders_type=orders_type, budget=budget)
    if ranger:
        for _ in range(32):
            if 'archery' not in state.buildings and state.gold >= BUILDINGS['archery'].cost:
                state.build('archery')
            if 'archery' in state.buildings and state.gold >= state.recruit_cost('ranger'):
                state.recruit('ranger')
                break
            rest(state, budget=budget)
        else:
            raise AssertionError('Could not fund the Censer formation’s Ranger')
    state.equip('veil_censer')
    _recover_at(state, (0, -2), budget=budget)
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


def _recover_at(state, destination, *, budget=None):
    for _ in range(32):
        march_to(state, destination, budget=budget)
        if state.hero.pos == destination and state.actions_left and state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            return
        rest(state, budget=budget)
    raise AssertionError('The earned retinue could not recover at its destination')


def prepare_drum_watch(state=None, *, budget=None):
    """Buy a Warden/Ranger army, recover the Drum, and approach the unclaimed Watch."""
    state = prepare_adventure(state=state, support='ranger', budget=budget)
    _recover_at(state, (-1, 1), budget=budget)
    state.explore(); finish_battle(state, budget=budget)
    assert 'vanguard_drum' in state.inventory
    _recover_at(state, (0, -2), budget=budget)
    state.equip('vanguard_drum'); state.explore()
    assert state.battle_encounter == 'border_watch'
    return state


def drum_watch_route(state=None, *, orders_type=AdventureOrders, budget=None):
    """Let the real Watch Archer Pin the flank, then restore its forest approach."""
    play = orders_type(prepare_drum_watch(budget=budget) if state is None else state)
    for uid, pos in ((2, (-3, 3)), (3, (-3, 2)), (1, (-2, 1)), (5, (-1, -1)), (0, (-2, 0))):
        play.do('move', uid, pos)
    play.guard_remaining(); play.do('end_turn')
    assert play.battle.unit(5).pinned and (0, -1) not in play.battle.reachable(5)
    play.do('rally', 0, 5)
    play.do('move', 5, (0, -1))
    play.do('attack', 5, play.enemy('archer'))
    return play


def prepare_relic_gate(relic, state=None, *, reload_state=None, budget=None):
    """Earn the Rune or Badge in stage two, carry two relics, and develop the final shard.

    Pass a save/reload callback for a UI adapter; the default uses actual model
    serialization. Source battles use the explicit automatic combat command.
    """
    from eador.model import State
    from tools.eador_campaign import provision_army
    from tools.eador_linked_campaign import play_stage, travel_selection
    if relic not in ('porter_rune', 'mirror_badge'):
        raise ValueError('This demonstration earns Porter’s Rune or Mirror Badge')
    reload_state = State.from_json if reload_state is None else reload_state
    state = State.new_campaign(7) if state is None else state
    state = play_stage(state, reload_state=reload_state, budget=budget)
    assert state.status == 'victory'
    state.advance('rootward' if relic == 'porter_rune' else 'foundries', **travel_selection(state))
    state = reload_state(state.to_json())
    state.build('barracks'); state.recruit('swordsman')
    source = (-1, -1) if relic == 'porter_rune' else (-1, 1)
    for _ in range(32):
        march_to(state, source, budget=budget)
        if state.actions_left and state.hero.pos == source:
            break
        rest(state, defend=False, budget=budget)
    else:
        raise AssertionError('The relic source could not be reached')
    state.explore(approach='light' if relic == 'porter_rune' else 'crossfire')
    finish_battle(state, budget=budget)
    assert relic in state.inventory
    state = play_stage(state, reload_state=reload_state, budget=budget)
    assert state.status == 'victory'
    selection = travel_selection(state)
    selection['relic_ids'] = (relic, 'moonstone')
    state.advance('gate', **selection)
    state = reload_state(state.to_json())
    assert set(state.inventory) == {relic, 'moonstone'}
    state.build('barracks')
    if relic == 'mirror_badge':
        state.build('archery')
    state.recruit('warden' if relic == 'porter_rune' else 'archer')
    for destination in ((-2, 0), (-1, 0), (0, 0), (1, 0)):
        march_to(state, destination, budget=budget)
        if not state.actions_left:
            rest(state, budget=budget); march_to(state, destination, budget=budget)
        state.explore(); finish_battle(state, budget=budget)
        rest(state, budget=budget); provision_army(state)
    for _ in range(24):
        provision_army(state); march_to(state, (1, 0), budget=budget)
        if (state.hero.hp < state.hero.max_hp or any(t.hp < t.max_hp for t in state.hero.army)
                or state.hero.mana < state.hero.max_mana):
            rest(state, budget=budget)
            continue
        if not state.actions_left:
            rest(state, defend=False, budget=budget)
            continue
        state.equip(relic); state.travel((2, 0))
        if state.battle_kind == 'conquest':
            assert state.battle_encounter == 'last_gate'
            return state
        finish_battle(state, budget=budget); rest(state, budget=budget)
    raise AssertionError('The equipped retinue could not reach the final Gate')


def mirror_gate_route(state=None, *, orders_type=AdventureOrders):
    """An earned hero Swap extracts the wounded holder without wasting its attack."""
    play = orders_type(prepare_relic_gate('mirror_badge') if state is None else state)
    ids = {unit.pos: unit.id for unit in play.battle.units if unit.team == 'player'}
    for source, destination in (((-2, -1), (-1, 0)), ((-2, 0), (0, -1)), ((-2, 1), (0, 0)),
                                ((-3, 2), (-1, 1)), ((-3, 0), (-1, -1)), ((-3, 1), (-2, 0)), ((-3, 3), (-2, 1))):
        play.do('move', ids[source], destination)
    play.guard_remaining(); play.do('end_turn')
    holder = ids[(-2, -1)]
    assert play.battle.unit(holder).kind == 'archer'
    assert play.battle.unit(holder).hp < play.battle.unit(holder).max_hp
    play.do('swap', 0, holder)
    target = next(unit.id for unit in play.battle.targets(holder) if unit.kind == 'guard')
    play.do('attack', holder, target)
    play.guard_remaining(); play.do('end_turn')
    return play


def porter_gate_route(state=None, *, orders_type=AdventureOrders):
    """Recover a delayed seal formation by delivering a new displacement angle.

    A complete opening ring is faster. This route deliberately keeps a reserve
    outside it and demonstrates recovering once a real defender contests the rear.
    """
    play = orders_type(prepare_relic_gate('porter_rune') if state is None else state)
    ids = {unit.pos: unit.id for unit in play.battle.units if unit.team == 'player'}
    for source, destination in (((-2, 0), (-1, -1)), ((-2, -1), (0, -1)), ((-2, 1), (0, 0)),
                                ((-3, 2), (-1, 1)), ((-3, 3), (-2, 2))):
        play.do('move', ids[source], destination)
    play.guard_remaining(); play.do('end_turn')
    play.do('move', 0, (-1, 0)); play.do('move', ids[(-3, 1)], (-2, 0))
    for _ in range(2):
        play.do('cast', 'heal', ids[(-2, -1)])
        play.guard_remaining(); play.do('end_turn')
    assert play.battle.objective.progress == 0
    play.do('swap', ids[(-3, 2)], 0)
    target = next(unit.id for unit in play.battle.repulse_targets(0) if unit.pos == (-2, 1))
    play.do('repulse', 0, target)
    play.do('move', ids[(-3, 3)], (-2, 1))
    play.guard_remaining(); play.do('end_turn')
    play.do('cast', 'heal', ids[(-2, -1)])
    play.guard_remaining(); play.do('end_turn')
    return play
