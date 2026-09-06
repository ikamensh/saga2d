"""Paid Causeway preparations and manual orders reusable by input adapters."""
from eador.model import BUILDINGS, State
from tools.eador_campaign import march_to, rest
from tools.eador_explorer_campaign import prepare_explorer
from tools.eador_extraction_campaign import prepare_adventure


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
