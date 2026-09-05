"""Encirclement has observable costs, deterministic upkeep, and a playable breakout."""
from eador.model import BUILDINGS, State


def resolve(state):
    while state.battle.outcome is None:
        state.battle.auto_turn()
    result = state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    return result


def surrounded_capital(*, market=False, veterans=False, outpost=False):
    """A real fortified defense lets the rival take the surrounding countryside."""
    state = State.new(7)
    state.build('barracks')
    state.recruit('swordsman')
    if veterans:
        state.explore()
        resolve(state)
    if outpost:
        for destination in ((-2, 1), (-2, 2)):
            state.travel(destination)
            resolve(state)
        state.end_turn()
        state.travel((-2, 1))
        state.travel((-2, 0))
    for _ in range(100):
        if all(state.provinces[pos].owner == 'rival' for pos in state.grid.neighbors((-2, 0))):
            return state
        if 'temple' not in state.buildings and state.gold >= BUILDINGS['temple'].cost:
            state.build('temple')
        while state.gold >= state.recruit_cost('swordsman') and len(state.hero.army) < state.hero.max_army:
            state.recruit('swordsman')
        if market and 'market' not in state.buildings and state.gold >= BUILDINGS['market'].cost:
            state.build('market')
        state.end_turn()
        if state.battle:
            assert resolve(state).startswith('Defended')
    raise AssertionError('The rival never encircled the capital.')


def test_encirclement_blocks_capital_and_market_production_with_a_persistent_warning():
    state = surrounded_capital(market=True)
    assert 'market' in state.buildings
    assert state.encircled
    assert state.income == state.crystal_income == 0
    warnings = [entry for entry in state.log if entry.startswith('Westwatch is encircled:')]
    assert len(warnings) == 1
    assert 'neighboring province' in warnings[0]
    saved = State.from_json(state.to_json())
    gold, crystals, upkeep = state.gold, state.crystals, state.upkeep
    assert gold >= upkeep
    for campaign in (state, saved):
        campaign.end_turn()
        assert campaign.gold == gold - upkeep
        assert campaign.crystals == crystals
    assert state.to_json() == saved.to_json()


def wound_the_army(state):
    """Command the hero into a guarded site, spend Heal, then withdraw injured."""
    state.explore()
    battle = state.battle
    for _ in range(12):
        hero = battle.unit(0)
        wounded = [unit for unit in battle.units if unit.team == 'player' and unit.alive
                   and unit.hp < unit.max_hp and battle.grid.distance(hero.pos, unit.pos) <= 4]
        if wounded and battle.mana == state.hero.max_mana:
            battle.cast('heal', wounded[0].id)
        elif battle.targets(0):
            battle.attack(0, battle.targets(0)[0].id)
        elif battle.reachable(0):
            enemies = [unit for unit in battle.units if unit.team == 'enemy' and unit.alive]
            target = min(battle.reachable(0), key=lambda pos: (min(battle.grid.distance(pos, enemy.pos)
                                                                       for enemy in enemies), pos))
            battle.move(0, target)
        if battle.outcome:
            break
        battle.end_turn()
        if hero.hp < hero.max_hp and battle.mana < state.hero.max_mana:
            break
    assert battle.unit(0).hp < battle.unit(0).max_hp
    assert battle.mana < state.hero.max_mana
    if battle.outcome:
        state.resolve_battle()
    else:
        state.retreat()


def test_rest_is_blocked_inside_encircled_westwatch_and_a_real_breakout_restores_it():
    state = surrounded_capital()
    wound_the_army(state)
    health = (state.hero.hp, state.hero.mana, {troop.id: troop.hp for troop in state.hero.army})
    state.end_turn()
    assert (state.hero.hp, state.hero.mana, {troop.id: troop.hp for troop in state.hero.army}) == health
    destination = min((pos for pos in state.grid.neighbors(state.hero.pos) if pos != state.rival.pos),
                      key=lambda pos: (len(state.provinces[pos].guards), pos))
    state.travel(destination)
    if state.battle:
        resolve(state)
    assert state.hero.pos == destination
    assert not state.encircled
    assert state.income > 0
    assert any(entry.startswith('Westwatch has an open supply route:') for entry in state.log)
    hp, mana = state.hero.hp, state.hero.mana
    state.end_turn()
    assert state.hero.hp > hp
    assert state.hero.mana > mana
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_upkeep_shortfall_warns_before_deterministic_desertion_and_preserves_veterans():
    state = surrounded_capital(veterans=True)
    assert len({troop.level for troop in state.hero.army}) > 1
    for _ in range(100):
        if state.upkeep_shortfall:
            break
        state.end_turn()
        if state.battle:
            resolve(state)
    else:
        raise AssertionError('An encircled unpaid army did not exhaust its treasury.')
    available = state.gold + state.income
    assert state.upkeep_shortfall == state.upkeep - available
    assert state.upkeep_shortfall > 0
    original_troops = {troop.id for troop in State.new(7).hero.army}
    restored = State.from_json(state.to_json())
    for campaign in (state, restored):
        campaign.end_turn()
        # The two inexperienced swordsmen leave first, then the newest expensive
        # veteran. The original militia and archer remain and are fully paid.
        assert {troop.id for troop in campaign.hero.army} == original_troops
        assert all(troop.level > 1 for troop in campaign.hero.army)
        assert campaign.gold == available - campaign.upkeep >= 0
        assert any('deserted' in entry and 'upkeep' in entry for entry in campaign.log)
    assert state.to_json() == restored.to_json()


def test_permanent_marketplace_camping_eventually_loses_instead_of_farming_income():
    state = surrounded_capital(market=True)
    start_turn = state.turn
    for _ in range(100):
        if state.status != 'playing':
            break
        state.end_turn()
        assert state.gold >= 0
        if state.battle:
            resolve(state)
    assert state.status == 'defeat'
    assert state.turn > start_turn
    assert any('deserted' in entry for entry in state.log)


def test_an_outlying_owned_province_still_produces_while_capital_supply_is_cut():
    state = surrounded_capital(outpost=True)
    outpost = state.provinces[(-2, 2)]
    assert state.encircled and outpost.owner == 'player'
    assert state.income == outpost.income
    assert state.crystal_income == outpost.crystals
    gold, crystals, upkeep = state.gold, state.crystals, state.upkeep
    state.end_turn()
    assert outpost.owner == 'player'
    assert state.gold == gold + outpost.income - upkeep
    assert state.crystals == crystals + outpost.crystals
