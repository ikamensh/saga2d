"""Paid preparation and explicit Vault routes reusable by native input verification."""
from tools.eador_campaign import march_to, rest, site_position
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure


def prepare_vault(hero_class='Commander', *, support='ranger', state=None, budget=None):
    state = prepare_adventure(hero_class, 'ruins', support=support, state=state, budget=budget)
    destination = site_position(state, 'sealed_vault')
    for _ in range(32):
        march_to(state, destination, budget=budget)
        if (state.hero.pos == destination and state.actions_left and state.hero.hp == state.hero.max_hp
                and all(t.hp == t.max_hp for t in state.hero.army)):
            return state
        rest(state, budget=budget)
    raise AssertionError('Could not reach the Vault with a recovered purchased army')


def vault_route(state, approach, *, orders_type=AdventureOrders):
    """The seed-seven Commander uses a Warden/Ranger formation against both routes."""
    state.explore(approach=approach)
    play = orders_type(state)
    defenders = {unit.pos: unit.id for unit in play.battle.units if unit.team == 'enemy'}
    warden, rear, east, guard = (defenders[pos] for pos in ((2, -1), (-3, 3), (2, 1), (0, -1)))
    if approach == 'unseal':
        play.do('move', 2, (-3, 2)); play.do('attack', 2, rear)
        play.do('attack', 5, rear)
        play.do('move', 4, (-2, 3)); play.do('attack', 4, rear)
        play.do('move', 3, (0, 0)); play.do('pin', 3, east)
        play.do('move', 5, (-1, 0))
        play.do('move', 0, (-2, 2)); play.do('move', 1, (0, -2))
        play.guard_remaining(); play.do('end_turn')
        play.do('move', 4, (-1, 3)); play.do('move', 0, (-2, 3))
    else:
        play.do('move', 1, (1, -2))
        play.do('move', 4, (0, 0)); play.do('attack', 4, guard)
        play.do('move', 0, (0, -2)); play.do('attack', 0, guard)
        play.do('attack', 1, guard)
        play.do('move', 3, (-1, 0)); play.do('pin', 3, rear)
        play.do('attack', 5, guard); play.do('move', 5, (-1, -1))
        play.do('move', 2, (-1, 1)); play.guard_remaining(); play.do('end_turn')
        play.do('move', 1, (3, -2)); play.do('attack', 1, warden)
        play.do('move', 0, (2, -2)); play.do('attack', 0, warden)
        play.do('move', 4, (1, 0)); play.do('attack', 4, guard)
        play.do('move', 3, (1, -1)); play.do('attack', 3, guard)
        play.do('move', 5, (0, 0)); play.do('attack', 5, guard)
        play.do('move', 2, (1, 1)); play.do('attack', 2, guard)
        play.do('end_turn')
        # The defender only swaps when the actual wounds justify a rescue.
        # Attack from the current hex if it has stayed beside our Militia.
        if play.battle.unit(warden) not in play.battle.targets(1):
            play.do('move', 1, (2, -1))
        for uid in (1, 4, 5, 2):
            if play.battle.unit(warden).alive:
                if uid == 2 and play.battle.unit(warden) not in play.battle.targets(uid):
                    play.do('move', uid, (2, 0))
                play.do('attack', uid, warden)
        play.do('pin', 3, rear); play.do('cast', 'heal', 0)
        play.do('end_turn')
        if play.battle.unit(1).pos == (3, -2):
            if play.battle.unit(2).pos == (2, 0):
                play.do('move', 2, (3, 0))
            play.do('move', 1, (2, -1))  # Leave the Warden a flat lane and the carrier its approach.
        for uid in (3, 1, 5):
            if play.battle.unit(east).alive:
                play.do('attack', uid, east)
        play.do('move', 4, (3, -1)); play.do('move', 0, (3, -2))
    play.do('swap', 4, 0)
    play.do('evacuate')
    return play
