"""An optional Causeway preserves older sources and earned tactical consequences."""
from pathlib import Path

from eador.model import State
from tools.eador_campaign import finish_battle


def test_actual_pre_causeway_shrine_keeps_its_complete_saved_continuation():
    """New worlds may change this site; a real loaded Shrine battle and all rewards remain exact."""
    fixtures = Path(__file__).parent / 'fixtures'
    before = (fixtures / 'v12_pre_causeway_shrine_battle.json').read_text()
    state = State.from_json(before)
    assert state.to_json() == before
    assert state.provinces[(0, 1)].site_kind == 'shrine'
    finish_battle(state)
    assert state.to_json() == (fixtures / 'v12_pre_causeway_shrine_result.json').read_text()


def test_paid_travel_reaches_an_optional_causeway_with_the_recorded_reward():
    """Conquest does not force entry; the free assembly snapshots the inherited Shrine reward."""
    state = State.new(7, theme='ruins')
    province, = [p for p in state.provinces.values() if p.site_kind == 'runebound_causeway']
    from tools.eador_causeway_campaign import prepare_causeway

    prepare_causeway(state=state)
    assert state.hero.pos == province.pos and not province.explored
    assert state.battle is None
    gold, crystals = state.gold, state.crystals
    state.explore(approach='western')
    assert (state.gold, state.crystals) == (gold, crystals)
    assert (state.battle.objective.kind, state.battle.objective.deadline) == ('extract', 5)
    assert state.battle.objective.exits == ((3, -3),)
    assert [u.kind for u in state.battle.units if u.team == 'enemy'] == ['adept', 'pikeman', 'ranger', 'guard']
    attempt = state.battle_adventure
    assert (attempt.gold, attempt.crystals, attempt.relic, attempt.cargo_penalty) == (45, 2, 'moonstone', 1)
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_a_thousand_ruins_keep_recorded_reward_packages_and_conquest():
    """Moved packages retain the inherited loot, cheaper witness, Crown and conquest fields."""
    from dataclasses import asdict
    import gzip
    import json
    from eador.worldgen import generate

    path = Path(__file__).parents[2] / 'docs/evidence/causeway-placement-2026-09-06.json.gz'
    with gzip.open(path, 'rt') as handle:
        rows = json.load(handle)['source_audit']['witnesses']
    site_fields = {'site', 'site_kind', 'site_guards', 'site_guard_hp', 'site_relic', 'site_gold', 'site_crystals'}
    for row in rows:
        world = generate(row['seed'], 'ruins')
        before, witness = row['selected'], row['witness']
        pos = tuple(before['pos'])
        source, = [p for p in world.values() if p.site_kind == 'runebound_causeway']
        current = json.loads(json.dumps(asdict(world[pos])))
        assert {k: v for k, v in current.items() if k not in site_fields} == {
            k: v for k, v in before.items() if k not in site_fields}
        assert (source.site_gold, source.site_crystals, source.site_relic) == (
            before['site_gold'], before['site_crystals'], before['site_relic'])
        current_witness = json.loads(json.dumps(asdict(world[tuple(witness['pos'])])))
        assert {k: v for k, v in current_witness.items() if k not in site_fields} == {
            k: v for k, v in witness.items() if k not in site_fields}
        assert any(json.loads(json.dumps({field: getattr(p, field) for field in site_fields})) == {
            field: witness[field] for field in site_fields} for p in world.values())
        assert world[(1, 0)].site_kind == 'barrow' and world[(1, 0)].site_relic == 'iron_crown'
    for theme in ('frontier', 'elderwild'):
        assert all(p.site_kind != 'runebound_causeway' for p in generate(7, theme).values())


def test_actual_low_mana_commander_can_prioritize_the_caster_and_escape():
    """Ten earned mana permits focus+Heal now; the initial caster dies without a forced Guard order."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_focus_route
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward

    state = prepare_causeway()
    assert state.turn == 8 and state.hero.mana == 10
    play = causeway_focus_route(state, heal=True, orders_type=Journey)
    assert play.battle.outcome_reason == 'escape' and play.battle.round == 4
    assert play.battle.mana == 2
    assert sum(u.max_hp - u.hp for u in play.battle.units if u.team == 'player') == 15
    adept = next(u for u in play.battle.units if u.kind == 'adept')
    assert not adept.alive and not adept.spent_abilities
    assert_one_reward(play)


def test_guard_and_occupied_landing_trade_real_recovery_for_fewer_wounds():
    """The same paid six-body army has two safe Repulse counters; neither refills mana for free."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_guard_route
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward

    guard_state = prepare_causeway(mana=12)
    assert (guard_state.turn, guard_state.hero.mana) == (9, 14)
    guard = causeway_guard_route(guard_state, heal=True, orders_type=Journey)
    occupied_state = prepare_causeway(mana=16)
    assert (occupied_state.turn, occupied_state.hero.mana) == (10, 18)
    occupied = causeway_guard_route(occupied_state, backstop=True, heal=True, orders_type=Journey)
    assert guard.state.hero.army == occupied.state.hero.army
    for play, wounds, spent in ((guard, 12, 12), (occupied, 14, 16)):
        assert play.battle.round == 4 and play.battle.outcome_reason == 'escape'
        assert sum(u.max_hp - u.hp for u in play.battle.units if u.team == 'player') == wounds
        assert play.state.hero.mana - play.battle.mana == spent
        assert not next(u for u in play.battle.units if u.kind == 'adept').spent_abilities
        assert_one_reward(play)


def test_existing_tower_infusion_can_pay_for_entry_now_instead_of_advancing_the_rival():
    """Three crystals and one actual hero action buy enough mana while leaving one action to enter."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_guard_route
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward
    from dataclasses import asdict

    state = prepare_causeway()
    assert (state.turn, state.actions_left, state.hero.mana) == (8, 2, 10)
    gold, crystals, rival = state.gold, state.crystals, asdict(state.rival)
    state.infuse()
    assert (state.turn, state.actions_left, state.hero.mana) == (8, 1, 18)
    assert (state.gold, state.crystals, asdict(state.rival)) == (gold, crystals - 3, rival)
    saved = state.to_json()
    for backstop, wounds in ((False, 12), (True, 14)):
        play = causeway_guard_route(State.from_json(saved), backstop=backstop, heal=True, orders_type=Journey)
        assert play.state.turn == 8 and play.state.actions_left == 0
        assert sum(u.max_hp - u.hp for u in play.battle.units if u.team == 'player') == wounds
        assert_one_reward(play)


def test_smaller_scout_can_escape_now_or_spend_its_exit_order_healing_before_a_rout():
    """The same paid five-body party trades four mana and another enemy phase for fewer wounds."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_scout_route
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward
    from tests.eador.test_relief import assert_one_reward as assert_rout_reward

    early = prepare_causeway('Scout')
    assert (early.turn, early.hero.level, early.hero.mana) == (6, 3, 14)
    saved = early.to_json()
    escape = causeway_scout_route(early, orders_type=Journey)
    assert escape.battle.round == 4 and escape.battle.outcome_reason == 'escape'
    assert sum(u.max_hp - u.hp for u in escape.battle.units if u.team == 'player') == 41
    assert not any(command == 'swap' for command, *_ in escape.orders)
    healing = State.from_json(saved)
    assert [t.kind for t in healing.hero.army] == ['militia', 'militia', 'archer', 'warden']
    healed = causeway_scout_route(healing, heal=True, orders_type=Journey)
    assert healed.battle.round == 5 and healed.battle.outcome_reason == 'rout'
    assert sum(command == 'end_turn' for command, *_ in healed.orders) == 4
    assert escape.battle.mana - healed.battle.mana == healed.battle.spell_cost('heal')
    assert sum(u.max_hp - u.hp for u in healed.battle.units if u.team == 'player') == 27
    assert_one_reward(escape)
    assert_rout_reward(healed)


def test_failed_causeway_keeps_the_dead_caster_and_finite_wounds_on_retry():
    """An exposed carrier really is pushed; deliberate deadline failure pays no partial-kill reward."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_failed_attempt, causeway_retry_route
    from tests.eador.test_extraction_journeys import Journey
    from tests.eador.test_relief import assert_one_reward

    failed = causeway_failed_attempt(prepare_causeway(), orders_type=Journey)
    assert failed.battle.outcome_reason == 'deadline' and failed.battle.round == 5
    assert any('repulses' in text for text in failed.battle.log)
    assert all(u.alive for u in failed.battle.units if u.team == 'player')
    state = failed.state
    gold, crystals, xp = state.gold, state.crystals, state.hero.xp
    state.resolve_battle()
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    assert state.choice is None and not state.provinces[state.hero.pos].explored
    survivors = [('pikeman', 28), ('ranger', 22), ('guard', 28)]
    assert list(zip(state.provinces[state.hero.pos].site_guards, state.provinces[state.hero.pos].site_guard_hp)) == survivors
    retry = causeway_retry_route(State.from_json(state.to_json()), orders_type=Journey)
    assert retry.battle.outcome_reason == 'rout'
    assert [u.kind for u in retry.battle.units if u.team == 'enemy'] == [kind for kind, _ in survivors]
    assert all(u.alive for u in retry.battle.units if u.team == 'player')
    assert_one_reward(retry)


def test_codex_uses_this_shards_recorded_causeway_reward_and_closes_without_mutation(tmp_path):
    """Variable loot must describe the actual saved source rather than a zero-valued registry default."""
    from eador.app import create_game
    from eador.content import RELICS
    from eador.scene import ShardScene
    from tools.eador_ui import PlayerInput

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        for seed in (0, 7):
            state = State.new(seed, theme='ruins')
            province = next(p for p in state.provinces.values() if p.site_kind == 'runebound_causeway')
            before = state.to_json()
            game.clear_and_push(ShardScene(state))
            player = PlayerInput(game); player.press('c'); player.press('5')
            entries = [e for e in game.scene.entries if e.title.startswith('Runebound Causeway')]
            assert len(entries) == 2
            for entry in entries:
                assert 'Recorded reward:' in entry.facts
                assert f'{province.site_gold} gold' in entry.facts
                assert RELICS[province.site_relic].name in entry.facts
            player.press('escape')
            assert isinstance(game.scene, ShardScene) and state.to_json() == before
    finally:
        game._teardown()
