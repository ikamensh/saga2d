"""A public-command linked-campaign policy for executable journeys and balance probes."""
from eador.model import State
from tools.eador_campaign import play_campaign


def play_stage(state):
    route = None
    if state.campaign.contract == 'rootward':
        watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
        route = ((-2, 0), (-1, 0), (0, 0), watch, (1, 0), (2, 0))
    elif state.campaign.contract == 'foundries':
        route = ((-2, 0), (-1, 0), (0, -1), (0, 1), (1, 0), (2, 0))
    return play_campaign(state, route)


def travel_selection(state):
    troops = sorted(state.hero.army, key=lambda t: (t.level, t.xp, t.kind == 'swordsman', t.id), reverse=True)[:2]
    relics = sorted(state.inventory, key=lambda relic: (relic != 'moonstone', relic != 'merchant_seal', relic))[:2]
    return dict(troop_ids=tuple(t.id for t in troops), relic_ids=tuple(relics))


def play_linked(seed=7, hero_class='Commander', middle='rootward', finale='throne'):
    state = State.new_campaign(seed, hero_class)
    for destination in (middle, finale, None):
        state = play_stage(state)
        if state.status != 'victory':
            return state
        if destination is not None:
            state = State.from_json(state.to_json())
            state.advance(destination, **travel_selection(state))
            state = State.from_json(state.to_json())
    return state
