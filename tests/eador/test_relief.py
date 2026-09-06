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
