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
