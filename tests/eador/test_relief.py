"""Relief is optional paid campaign content with finite, saved consequences."""
from eador.model import State
from tools.eador_campaign import finish_battle, march_to, rest


def test_frontier_offers_an_optional_hold_with_its_original_reward_and_four_defenders():
    """Conquest does not force the signal fight; exploration snapshots its inherited reward."""
    state = State.new(7)
    province = state.provinces[(0, 0)]
    assert province.site_kind == 'relief_column'
    assert (province.site_gold, province.site_crystals, province.site_relic) == (35, 3, 'oak_standard')
    state.build('barracks'); state.recruit('swordsman')
    state.explore(); finish_battle(state)
    for pos in ((-1, 0), (0, 0)):
        march_to(state, pos); rest(state)
    assert not province.explored and state.battle is None
    state.explore(approach='forward')
    assert state.battle.objective.kind == 'hold'
    assert state.battle.objective.deadline == 4
    assert len(state.battle.grid.neighbors(state.battle.objective.target)) == 6
    assert [u.kind for u in state.battle.units if u.team == 'enemy'] == ['skyrider', 'militia', 'archer', 'guard']
    assert (state.battle_adventure.gold, state.battle_adventure.crystals, state.battle_adventure.relic) == (35, 3, 'oak_standard')
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_codex_quotes_the_recorded_variable_reward_and_never_invents_a_default(tmp_path):
    """Relief inherits different loot across shards; its reference must use this saved world."""
    from eador.app import create_game
    from eador.scene import ShardScene
    from tools.eador_ui import PlayerInput

    game = create_game(backend='mock', save_dir=tmp_path)
    try:
        for seed, reward in ((7, '35 gold / 3 crystals / Oak Standard'), (2, '55 gold / 1 crystal / Iron Crown')):
            state = State.new(seed)
            game.clear_and_push(ShardScene(state))
            player = PlayerInput(game); player.press('c'); player.press('5')
            entries = [e for e in game.scene.entries if e.title.startswith('Relief Column')]
            assert len(entries) == 3 and all(reward in e.facts for e in entries)
            assert state.to_json() == State.from_json(state.to_json()).to_json()
    finally:
        game._teardown()


def test_a_thousand_frontiers_preserve_the_recorded_ordinary_witness_and_conquest():
    """Pre-integration witnesses protect cheaper sources and every non-site province field."""
    import gzip
    import json
    from dataclasses import asdict
    from pathlib import Path
    from eador.worldgen import generate

    path = Path(__file__).parents[2] / 'docs/evidence/relief-revised-prototype-2026-09-06.json.gz'
    with gzip.open(path, 'rt') as handle:
        witnesses = json.load(handle)['source_audit']['selections']
    site_fields = {'site', 'site_kind', 'site_guards', 'site_guard_hp'}
    for witness in witnesses:
        world = generate(witness['seed'])
        selected = witness['proposed_source']
        source = world[tuple(selected['pos'])]
        assert source.site_kind == 'relief_column'
        assert sum(p.site_kind == 'relief_column' for p in world.values()) == 1
        current = json.loads(json.dumps(asdict(source)))
        assert {k: v for k, v in current.items() if k not in site_fields} == {
            k: v for k, v in selected.items() if k not in site_fields}
        ordinary = witness['unchanged_ordinary_route']
        assert json.loads(json.dumps(asdict(world[tuple(ordinary['pos'])]))) == ordinary
        assert source.site_guards == ['skyrider', 'militia', 'archer', 'guard']
    assert generate(2)[(0, 0)].site_kind == 'tower'
    for theme in ('elderwild', 'ruins'):
        assert all(p.site_kind != 'relief_column' for p in generate(7, theme).values())


def test_actual_pre_relief_grove_battle_preserves_its_exact_saved_reward_continuation():
    """Loading the replaced source retains its ordinary encounter, world and complete result."""
    from pathlib import Path

    fixtures = Path(__file__).parent / 'fixtures'
    before = (fixtures / 'v12_pre_relief_grove_battle.json').read_text()
    state = State.from_json(before)
    assert state.to_json() == before
    assert state.provinces[(0, 0)].site_kind == 'grove'
    finish_battle(state)
    assert state.to_json() == (fixtures / 'v12_pre_relief_grove_result.json').read_text()


def test_actually_purchased_commanders_intercept_support_and_save_a_manual_hold():
    """The real journey earns its stats; full-State reloads preserve the support kill and seal score."""
    from tools.eador_relief_campaign import prepare_relief, relief_forward_route
    from tests.eador.test_extraction_journeys import Journey

    state = prepare_relief()
    assert state.hero.pos == (0, 0) and state.hero.mana == state.hero.max_mana
    assert [t.kind for t in state.hero.army] == ['militia', 'militia', 'archer', 'pikeman', 'warden', 'adept']
    play = relief_forward_route(state, orders_type=Journey)
    assert play.battle.outcome_reason == 'hold' and play.battle.round == 2
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert any(u.alive for u in play.battle.units if u.team == 'enemy')
    assert any(command == 'pin' for command, *_ in play.orders)


def assert_one_reward(play):
    """Success closes this saved site and resolves its actual inherited reward once."""
    import pytest
    from eador.model import RuleError

    state, battle = play.state, play.battle
    assert battle.outcome == 'player'
    gold, crystals, reward, pos = state.gold, state.crystals, state.battle_adventure, state.hero.pos
    surviving_guards = [(u.kind, u.hp) for u in battle.units if u.team == 'enemy' and u.alive]
    state.resolve_battle()
    assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
    assert state.provinces[pos].explored
    assert list(zip(state.provinces[pos].site_guards, state.provinces[pos].site_guard_hp)) == surviving_guards
    state = State.from_json(state.to_json())
    while state.choice:
        state.choose(state.choice.options[0].id)
        state = State.from_json(state.to_json())
    before = state.to_json()
    with pytest.raises(RuleError):
        state.explore()
    with pytest.raises(RuleError):
        state.resolve_battle()
    assert state.to_json() == before


def test_purchased_active_passive_and_smaller_parties_hold_in_three_modes_and_five_worlds():
    """Sixty actual paid routes retain manual hold/survivors and exact full-State order reloads."""
    from tools.eador_relief_campaign import (prepare_relief, relief_forward_route, relief_western_route,
                                             relief_passive_route, relief_scout_route)
    from tests.eador.test_extraction_journeys import Journey

    for mode in ('accessible', 'standard', 'challenge'):
        for seed in (0, 2, 7, 11, 29):
            for hero, routes in (('Commander', (relief_forward_route, relief_western_route, relief_passive_route)),
                                 ('Scout', (relief_scout_route,))):
                prepared = prepare_relief(hero, seed=seed, difficulty=mode).to_json()
                for route in routes:
                    play = route(State.from_json(prepared), orders_type=Journey)
                    assert play.battle.outcome_reason == 'hold'
                    assert play.battle.round == (4 if route == relief_western_route else 2)
                    assert all(u.alive for u in play.battle.units if u.team == 'player')
                    assert any(u.alive for u in play.battle.units if u.team == 'enemy')
                    assert_one_reward(play)


def test_actual_rally_mistake_loses_a_veteran_then_paid_retry_keeps_finite_wounds():
    """The missed support is consequential; neither the Pike nor killed enemies respawn after reload."""
    from tools.eador_relief_campaign import prepare_relief, relief_failed_support, relief_retry_route
    from tests.eador.test_extraction_journeys import Journey

    play = relief_failed_support(prepare_relief(), orders_type=Journey)
    state = play.state
    assert play.battle.outcome_reason == 'deadline' and play.battle.round == 4
    assert not play.battle.unit(4).alive
    assert any('rallies Skyrider' in text for text in play.battle.log)
    gold, crystals, xp, actions = state.gold, state.crystals, state.hero.xp, state.actions_left
    state.resolve_battle()
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    assert state.choice is None and not state.provinces[state.hero.pos].explored
    survivors = [('archer', 20), ('guard', 36)]
    assert list(zip(state.provinces[state.hero.pos].site_guards, state.provinces[state.hero.pos].site_guard_hp)) == survivors
    state = State.from_json(state.to_json())
    price, gold = state.recruit_cost('pikeman'), state.gold
    state.recruit('pikeman')
    replacement = state.hero.army[-1]
    assert replacement.id != 4 and replacement.level == 1 and replacement.xp == 0
    assert state.gold == gold - price and state.actions_left == actions
    retry = relief_retry_route(State.from_json(state.to_json()), orders_type=Journey)
    assert [(u.kind, u.max_hp) for u in retry.battle.units if u.team == 'enemy'] == [('archer', 20), ('guard', 42)]
    assert retry.battle.outcome_reason == 'rout'
    assert all(u.alive for u in retry.battle.units if u.team == 'player')
    assert_one_reward(retry)
