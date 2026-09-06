"""Paid Causeway preparations and manual orders reusable by input adapters."""
from eador.model import BUILDINGS, State
from tools.eador_campaign import march_to, rest
from tools.eador_explorer_campaign import prepare_explorer
from tools.eador_extraction_campaign import AdventureOrders, prepare_adventure


def prepare_causeway(hero_class='Commander', *, seed=7, difficulty='standard', mana=0, state=None):
    """Reach the optional site healthy; additional requested mana costs actual recovery turns."""
    state = State.new(seed, hero_class, theme='ruins', difficulty=difficulty) if state is None else state
    destination = next(p.pos for p in state.provinces.values() if p.site_kind == 'runebound_causeway')
    if state.hero.hero_class == 'Scout':
        prepare_explorer('Scout', support=None, state=state)
    else:
        prepare_adventure(theme='ruins', state=state)
    tower = BUILDINGS['mage_tower']
    for _ in range(24):
        if state.gold >= tower.cost and state.crystals >= tower.crystals:
            break
        rest(state)
    else:
        raise AssertionError('Could not fund the Mage Tower.')
    state.build('mage_tower')
    for _ in range(48):
        march_to(state, destination)
        if (state.actions_left and state.hero.hp == state.hero.max_hp and state.hero.mana >= mana
                and all(t.hp == t.max_hp for t in state.hero.army)):
            return state
        rest(state)
    raise AssertionError('Could not reach the Causeway with the requested recovery.')


def _end(play):
    play.guard_remaining()
    play.do('end_turn')


def _commander_opening(play, *, backstop, exposed=False):
    for uid, pos in ((3, (-1, -1)), (4, (-1, 1)), (1, (-2, 2)),
                     (0, (-1, 0)), (5, (-2, 1))):
        play.do('move', uid, pos)
    play.do('attack', 3, play.enemy('adept'))
    play.do('move', 2, (-2, 0) if backstop else (-1, -2))
    if backstop or exposed:
        play.do('cast', 'bolt', play.enemy('adept'))
    _end(play)


def causeway_guard_route(state, *, backstop=False, heal=False, orders_type=AdventureOrders):
    """Guard the carrier or occupy its push landing; the freed soldier and spell orders differ."""
    state.explore(approach='western')
    play = orders_type(state)
    _commander_opening(play, backstop=backstop)
    play.do('move', 0, (0, -1))
    play.do('cast', 'bolt', play.enemy('pikeman' if backstop else 'adept'))
    play.do('move', 3, (0, -2)); play.do('attack', 3, play.enemy('adept'))
    play.do('move', 2, (-1, -2) if backstop else (0, -3))
    play.do('move', 4, (0, 0)); play.do('move', 5, (0, 1)); play.do('move', 1, (-1, 0))
    _end(play)
    play.do('move', 0, (1, -2)); play.do('cast', 'bolt', play.enemy('pikeman'))
    if backstop:
        play.do('attack', 3, play.enemy('ranger'))
    else:
        play.do('attack', 3, play.enemy('pikeman'))
        play.do('move', 2, (2, -3)); play.do('attack', 2, play.enemy('pikeman'))
    play.do('move', 5, (1, 0)); play.do('attack', 5, play.enemy('ranger'))
    play.do('move', 4, (1, -1))
    if backstop:
        play.do('move', 2, (0, -3))
    _end(play)
    play.do('attack', 3, play.enemy('ranger'))
    if not backstop:
        if heal:
            play.do('move', 2, (2, -1)); play.do('attack', 2, play.enemy('ranger'))
        else:
            play.do('attack', 5, play.enemy('ranger'))
    if heal:
        play.do('cast', 'heal', 0, caster_id=5)
    play.do('move', 4, (3, -3)); play.do('move', 0, (2, -2)); play.do('swap', 4, 0)
    play.do('evacuate')
    return play


def causeway_focus_route(state, *, heal=False, orders_type=AdventureOrders):
    """Finish the Adept with full shots, then use the freed Militia to clear the exit Pike."""
    state.explore(approach='western')
    play = orders_type(state)
    for uid, pos in ((3, (-1, -1)), (4, (-1, 1)), (1, (-2, 2)),
                     (0, (-1, 0)), (5, (-2, 1)), (2, (-1, -2))):
        play.do('move', uid, pos)
    for uid in (3, 0, 5):
        play.do('attack', uid, play.enemy('adept'))
    _end(play)
    for uid, pos in ((0, (0, -1)), (3, (0, -2)), (2, (0, -3)),
                     (4, (0, 0)), (5, (0, 1)), (1, (-1, 0))):
        play.do('move', uid, pos)
    play.do('attack', 3, play.enemy('ranger')); _end(play)
    play.do('move', 0, (1, -2)); play.do('cast', 'bolt', play.enemy('pikeman'))
    play.do('attack', 3, play.enemy('pikeman'))
    play.do('move', 2, (2, -3)); play.do('attack', 2, play.enemy('pikeman'))
    play.do('move', 5, (1, 0)); play.do('attack', 5, play.enemy('ranger'))
    play.do('move', 4, (1, -1)); _end(play)
    if heal:
        play.do('cast', 'heal', 0, caster_id=5)
    play.do('move', 4, (3, -3)); play.do('move', 0, (2, -2))
    play.do('swap', 4, 0); play.do('evacuate')
    return play


def causeway_scout_route(state, *, heal=False, orders_type=AdventureOrders):
    """Five bodies take the oblique ranged route; optional late Heal spends the evacuation order."""
    state.explore(approach='western')
    play = orders_type(state)
    for uid, pos in ((3, (-1, -1)), (4, (-1, 1)), (1, (-2, 2)),
                     (0, (0, -1)), (2, (-1, -2))):
        play.do('move', uid, pos)
    play.do('attack', 3, play.enemy('adept')); play.do('attack', 0, play.enemy('adept'))
    _end(play)
    play.do('move', 3, (0, -2)); play.do('attack', 3, play.enemy('adept'))
    play.do('move', 0, (2, -3)); play.do('attack', 0, play.enemy('ranger'))
    play.do('move', 2, (0, -3)); play.do('move', 4, (0, 0)); _end(play)
    play.do('attack', 3, play.enemy('ranger')); play.do('move', 0, (2, -2))
    play.do('cast', 'bolt', play.enemy('pikeman'))
    play.do('move', 2, (2, -3)); play.do('attack', 2, play.enemy('pikeman'))
    play.do('move', 4, (1, -1)); _end(play)
    play.do('move', 0, (3, -3))
    if heal:
        play.do('cast', 'heal', 0)
        _end(play)
        if play.battle.outcome is None:
            play.do('attack', 3, play.enemy('guard'))
    else:
        play.do('evacuate')
    return play
