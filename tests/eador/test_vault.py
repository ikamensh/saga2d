"""A crystal-funded exit changes a real Ruins adventure without replacing its guards."""
import pytest

from eador.model import State
from tools.eador_vault_campaign import prepare_vault as prepared_vault, vault_route


def test_spending_crystals_opens_a_second_vault_exit_without_changing_the_encounter():
    """The entry charge changes the route, not the saved guards, cargo or player deployment."""
    before = prepared_vault().to_json()
    free, paid = State.from_json(before), State.from_json(before)
    assert free.provinces[free.hero.pos].site_kind == 'sealed_vault'
    assert free.provinces[(-2, 0)].site_kind == 'shrine'
    options = free.adventure_approaches()
    assert [(option.id, option.crystals_cost) for option in options] == [('crossfire', 0), ('unseal', 2)]
    free.explore(); paid.explore(approach='unseal')
    assert free.gold == paid.gold and free.crystals == paid.crystals + 2
    assert free.actions_left == paid.actions_left
    assert free.battle.objective.exits == ((3, -1),)
    assert paid.battle.objective.exits == ((3, -1), (-1, 3))
    assert free.battle.units == paid.battle.units and free.battle.terrain == paid.battle.terrain
    assert free.battle_adventure.gold == paid.battle_adventure.gold
    assert State.from_json(paid.to_json()).to_json() == paid.to_json()


@pytest.mark.parametrize('world', ('fresh', 'saved-1524c48'))
def test_crystals_buy_a_shorter_route_past_a_stationary_or_rescuing_warden(world):
    """Both real worlds fund their armies; paid escape beats either observed Warden response."""
    from pathlib import Path
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward

    if world == 'fresh':
        initial = State.new(7, theme='ruins')
    else:
        # Exact Standard State.new(7, theme='ruins') retained at 1524c48 before site
        # variation, from shardbound-worldgen-before-1524c48.json.gz. Current rules
        # still earn and purchase the army; no prepared stats or positions are injected.
        text = (Path(__file__).parent / 'fixtures/v12_ruins_seed7_before_site_variation.json').read_text()
        initial = State.from_json(text)
        assert initial.to_json() == text
    before = prepared_vault(state=initial).to_json()
    free = vault_route(State.from_json(before), 'crossfire', orders_type=Journey)
    paid = vault_route(State.from_json(before), 'unseal', orders_type=Journey)
    assert free.battle.round == 4 and paid.battle.round == 2
    assert free.state.gold == paid.state.gold and free.state.crystals == paid.state.crystals + 2
    assert free.battle.mana == paid.battle.mana - 4
    assert sum(unit.hp for unit in free.battle.units if unit.team == 'player') < sum(
        unit.hp for unit in paid.battle.units if unit.team == 'player')
    rescued = any('Warden swaps places with Dread Guard' in line for line in free.battle.log)
    if world == 'saved-1524c48':
        assert rescued
    else:
        warden = next(u for u in free.battle.units if u.team == 'enemy' and u.kind == 'warden')
        assert not rescued and not warden.alive and warden.pos == (2, -1)
        assert ('move', (2, (3, 0)), {}) in free.orders
        assert ('move', (1, (2, -1)), {}) in free.orders
    assert paid.battle.unit(0).pinned  # Pin restricts walking, but allied delivery preserves evacuation.
    assert sum(u.alive for u in free.battle.units if u.team == 'enemy') == 1
    assert sum(u.alive for u in paid.battle.units if u.team == 'enemy') == 3
    assert_one_reward(free); assert_one_reward(paid)


def test_a_failed_paid_attempt_keeps_its_crystal_cost_and_finite_wounded_guard_roster():
    """Changing the next approach cannot resurrect the fallen rear Archer or refund its key."""
    from eador.model import RuleError
    state = prepared_vault()
    crystals = state.crystals
    state.explore(approach='unseal')
    battle = state.battle
    rear = next(u.id for u in battle.units if u.team == 'enemy' and u.pos == (-3, 3))
    east = next(u.id for u in battle.units if u.team == 'enemy' and u.pos == (2, 1))
    battle.move(2, (-3, 2)); battle.attack(2, rear)
    battle.attack(5, rear)
    battle.move(4, (-2, 3)); battle.attack(4, rear)
    battle.move(3, (0, 0)); battle.pin(3, east)
    assert not battle.unit(rear).alive
    survivors = [(unit.kind, unit.hp) for unit in battle.units if unit.team == 'enemy' and unit.alive]
    state = State.from_json(state.to_json())
    state.retreat()
    assert state.crystals == crystals - 2 and not state.choice
    province = state.provinces[state.hero.pos]
    assert list(zip(province.site_guards, province.site_guard_hp)) == survivors
    if not state.actions_left:
        state.end_turn()
    state.explore(approach='crossfire')
    assert state.crystals == crystals - 2
    assert [(unit.kind, unit.hp) for unit in state.battle.units if unit.team == 'enemy'] == survivors
    assert state.battle.objective.exits == ((3, -1),)
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    state.retreat()
    if not state.actions_left:
        state.end_turn()
    state.crystals = 1  # An otherwise valid resource-boundary fixture.
    before = state.to_json()
    with pytest.raises(RuleError, match='crystals'):
        state.explore(approach='unseal')
    assert state.to_json() == before


@pytest.mark.parametrize('hero', ['Warrior', 'Scout', 'Wizard'])
def test_the_other_heroes_can_buy_a_support_army_and_manually_use_the_second_exit(hero):
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward

    state = prepared_vault(hero)
    crystals = state.crystals
    play = vault_route(state, 'unseal', orders_type=Journey)
    assert play.state.crystals == crystals - 2 and play.battle.round == 2
    assert all(unit.alive for unit in play.battle.units if unit.team == 'player')
    assert_one_reward(play)


def test_an_existing_v10_ruins_battle_and_site_array_keep_their_actual_continuation():
    """The new Vault never replaces a Tower already recorded in a player's shard."""
    import json
    from pathlib import Path
    from tools.eador_campaign import finish_battle
    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v10_ruins_battle.json').read_text())
    assert state.provinces[(-1, 1)].site_kind == 'tower'
    finish_battle(state)
    actual = json.loads(state.to_json())
    expected = json.loads((fixtures / 'v10_ruins_battle_result.json').read_text())
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual.pop('rules_id') == 'standard-1'
    assert actual == expected


def test_new_ruins_keep_their_required_sources_and_offer_exactly_one_vault():
    for seed in range(20):
        state = State.new(seed, theme='ruins')
        kinds = [province.site_kind for province in state.provinces.values()]
        assert kinds.count('sealed_vault') == kinds.count('border_watch') == 1
        assert state.provinces[(-2, 0)].site_kind == 'shrine'
        assert {'den', 'explorer_camp'} <= set(kinds)
        assert state.provinces[(2, 0)].site_kind is None
