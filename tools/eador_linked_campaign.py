"""A public-command linked-campaign policy for executable journeys and balance probes."""
from eador.model import State
from tools.eador_campaign import play_campaign


def play_stage(state, **options):
    route = None
    if state.campaign.contract == 'rootward':
        watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
        route = ((-2, 0), (-1, 0), (0, 0), watch, (1, 0), (2, 0))
    elif state.campaign.contract == 'foundries':
        route = ((-2, 0), (-1, 0), (0, -1), (0, 1), (1, 0), (2, 0))
    return play_campaign(state, route, **options)


def travel_selection(state):
    troops = sorted(state.hero.army, key=lambda t: (t.level, t.xp, t.kind == 'swordsman', t.id), reverse=True)[:2]
    relics = sorted(state.inventory, key=lambda relic: (relic != 'moonstone', relic != 'merchant_seal', relic))[:2]
    return dict(troop_ids=tuple(t.id for t in troops), relic_ids=tuple(relics))


def secure_frontier(state):
    """Invest and meet the visible expedition before taking the distant Watch detour."""
    from tools.eador_campaign import finish_battle, march_to, provision_army
    state.build('barracks')
    state.recruit('swordsman')
    state.explore(); finish_battle(state)
    march_to(state, (0, 0))
    for _ in range(20):
        provision_army(state)
        if state.rival.defeats:
            return state
        if state.actions_left and state.grid.distance(state.hero.pos, state.rival.pos) == 1:
            state.travel(state.rival.pos)
        else:
            state.end_turn()
        if state.battle:
            finish_battle(state)
        if state.status != 'playing':
            return state
    raise AssertionError('The early interception did not meet the announced expedition.')


def play_linked(seed=7, hero_class='Commander', middle='rootward', finale='throne', *,
                difficulty='standard', secure_before_watch=False):
    state = State.new_campaign(seed, hero_class, difficulty=difficulty)
    for destination in (middle, finale, None):
        state = play_stage(state)
        if state.status != 'victory':
            return state
        if destination is not None:
            state = State.from_json(state.to_json())
            state.advance(destination, **travel_selection(state))
            state = State.from_json(state.to_json())
            if destination == 'rootward' and secure_before_watch:
                state = secure_frontier(state)
    return state


def lose_shard(state):
    """Leaving the capital and declining tactical defenses permits the finite rival to win."""
    from tools.eador_campaign import finish_battle
    if state.hero.pos == (-2, 0):
        if not state.actions_left:
            state.end_turn()
        state.travel((-2, 1))
        if state.battle:
            finish_battle(state)
    for _ in range(120):
        if state.status == 'defeat':
            return state
        state.end_turn()
        if state.battle:
            state.retreat()
    raise AssertionError('Neglect never lost the capital.')
