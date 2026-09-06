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
    assert state.provinces[(0, 1)].site_kind == 'runebound_causeway'
    from tools.eador_causeway_campaign import prepare_causeway

    prepare_causeway(state=state)
    assert state.hero.pos == (0, 1) and not state.provinces[(0, 1)].explored
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


def test_a_thousand_ruins_keep_the_recorded_witness_and_every_other_world_field():
    """Prechange whole-world hashes protect all authored sources, Crown, fallback and economics."""
    from dataclasses import asdict
    import gzip
    import hashlib
    import json
    from eador.worldgen import generate

    path = Path(__file__).parents[2] / 'docs/evidence/causeway-placement-2026-09-06.json.gz'
    with gzip.open(path, 'rt') as handle:
        rows = json.load(handle)['source_audit']['witnesses']
    for row in rows:
        world = generate(row['seed'], 'ruins')
        before, witness = row['selected'], row['witness']
        pos = tuple(before['pos'])
        assert world[pos].site_kind == 'runebound_causeway'
        assert sum(p.site_kind == 'runebound_causeway' for p in world.values()) == 1
        current = json.loads(json.dumps(asdict(world[pos])))
        for field in ('site', 'site_kind', 'site_guards', 'site_guard_hp'):
            current[field] = before[field]
        assert current == before
        assert json.loads(json.dumps(asdict(world[tuple(witness['pos'])]))) == witness
        restored = [before if key == pos else asdict(world[key]) for key in sorted(world)]
        assert hashlib.sha256(json.dumps(restored, sort_keys=True).encode()).hexdigest() == row['original_world_sha256']
        assert world[(1, 0)].site_kind == 'barrow' and world[(1, 0)].site_relic == 'iron_crown'
    for theme in ('frontier', 'elderwild'):
        assert all(p.site_kind != 'runebound_causeway' for p in generate(7, theme).values())


def test_actual_low_mana_commander_can_prioritize_the_caster_and_escape():
    """Ten earned mana permits focus+Heal now; the initial caster dies without a forced Guard order."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_focus_route
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward

    state = prepare_causeway()
    assert state.turn == 9 and state.hero.mana == 10
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
    assert (guard_state.turn, guard_state.hero.mana) == (10, 14)
    guard = causeway_guard_route(guard_state, heal=True, orders_type=Journey)
    occupied_state = prepare_causeway(mana=16)
    assert (occupied_state.turn, occupied_state.hero.mana) == (11, 18)
    occupied = causeway_guard_route(occupied_state, backstop=True, heal=True, orders_type=Journey)
    assert guard.state.hero.army == occupied.state.hero.army
    for play, wounds, spent in ((guard, 12, 12), (occupied, 14, 16)):
        assert play.battle.round == 4 and play.battle.outcome_reason == 'escape'
        assert sum(u.max_hp - u.hp for u in play.battle.units if u.team == 'player') == wounds
        assert play.state.hero.mana - play.battle.mana == spent
        assert not next(u for u in play.battle.units if u.kind == 'adept').spent_abilities
        assert_one_reward(play)


def test_smaller_scout_can_leave_at_low_mana_or_recover_and_finish_with_healing():
    """A five-body flank needs no Acolyte; later recovery includes the real rival and level gain."""
    from tools.eador_causeway_campaign import prepare_causeway, causeway_scout_route
    from tests.eador.test_extraction_journeys import Journey, assert_one_reward
    from tests.eador.test_relief import assert_one_reward as assert_rout_reward

    early = prepare_causeway('Scout')
    assert (early.turn, early.hero.level, early.hero.mana) == (6, 3, 6)
    escape = causeway_scout_route(early, orders_type=Journey)
    assert escape.battle.round == 4 and escape.battle.outcome_reason == 'escape'
    assert sum(u.max_hp - u.hp for u in escape.battle.units if u.team == 'player') == 41
    assert not any(command == 'swap' for command, *_ in escape.orders)
    assert_one_reward(escape)
    recovered = prepare_causeway('Scout', mana=8)
    assert (recovered.turn, recovered.hero.level, recovered.hero.mana) == (8, 4, 8)
    assert [t.kind for t in recovered.hero.army] == ['militia', 'militia', 'archer', 'warden']
    healed = causeway_scout_route(recovered, heal=True, orders_type=Journey)
    assert healed.battle.round == 4 and healed.battle.outcome_reason == 'rout'
    assert sum(command == 'end_turn' for command, *_ in healed.orders) == 4
    assert sum(u.max_hp - u.hp for u in healed.battle.units if u.team == 'player') == 19
    assert_rout_reward(healed)
