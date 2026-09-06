"""Legacy verification preparation and detached searches yield without changing their results."""

import gzip
import json
from pathlib import Path

import pytest

from eador.model import State
from tools.cpu_budget import CpuBudget


@pytest.fixture
def clock(monkeypatch):
    """Only fake CPU/wall time; preparation, rules, saves and search remain real."""
    samples = {'cpu': 0.0, 'wall': 0.0, 'sleeps': []}

    def process_time():
        samples['cpu'] += .06
        samples['wall'] += .06
        return samples['cpu']

    def sleep(seconds):
        samples['sleeps'].append(seconds)
        samples['wall'] += seconds

    monkeypatch.setattr('tools.cpu_budget.time.process_time', process_time)
    monkeypatch.setattr('tools.cpu_budget.time.monotonic', lambda: samples['wall'])
    monkeypatch.setattr('tools.cpu_budget.time.sleep', sleep)
    return samples


def test_saved_phase_preparation_yields_and_keeps_every_earned_snapshot(clock):
    """Default preparation preserves paid linked-campaign phases and old save payloads exactly."""
    from tools.verify_eador_saves import prepared_saves

    expected = prepared_saves(budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = prepared_saves()
    assert clock['sleeps'], 'The default saved-phase preparation must yield'
    assert actual == expected
    phases = dict(actual)
    assert State.from_json(phases['completed']).status == 'victory'
    assert State.from_json(phases['recovery']).status == 'defeat'
    for _, snapshot in actual:
        restored = State.from_json(snapshot)
        assert State.from_json(restored.to_json()).to_json() == restored.to_json()


def test_result_preparation_yields_and_keeps_real_battle_and_campaign_outcomes(clock):
    """The actual escape, hold, loss and victory preparations keep identical saved results."""
    from tools.verify_eador_results import prepared_results

    expected = prepared_results(budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = prepared_results()
    assert clock['sleeps'], 'The default result preparation must yield'
    assert actual == expected
    results = {name: State.from_json(snapshot) for name, snapshot in actual}
    for name in ('rout', 'hero-death', 'escape', 'hold', 'extract-deadline', 'hold-deadline'):
        assert results[name].battle.outcome is not None
    assert results['shard-victory'].status == 'victory'
    assert results['capital-lost'].status == 'defeat'


def test_choice_preparation_yields_and_preserves_every_earned_reward(clock):
    """All real hero/theme campaigns earn identical reloadable decisions with the default allowance."""
    from tools.verify_eador_choices import prepared_choices

    actual = prepared_choices()
    assert clock['sleeps'], 'The default reward preparation must yield'
    clock['sleeps'].clear()
    expected = prepared_choices(budget=CpuBudget(100))
    assert not clock['sleeps']
    assert actual == expected
    kinds = set()
    for _, snapshot in actual:
        state = State.from_json(snapshot)
        assert state.choice is not None
        kinds.add(state.choice.kind)
        state.choose(state.choice.options[0].id)
        assert State.from_json(state.to_json()).to_json() == state.to_json()
    assert kinds == {'relic', 'skill'}


@pytest.mark.parametrize('cpu_percent', [25, 100], ids=['default', 'explicit-unpaced'])
def test_choice_cli_paces_its_real_input_journey_and_closes_both_sessions(
        cpu_percent, clock, tmp_path, monkeypatch):
    """Default CLI preparation yields, explicit stress bypasses it, and both sessions always close."""
    from saga2d.backends.mock_backend import MockBackend
    from tools.verify_eador_choices import main

    backends = []

    class ObservedBackend(MockBackend):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            backends.append(self)

    monkeypatch.setattr('saga2d.backends.mock_backend.MockBackend', ObservedBackend)
    args = ['--backend', 'mock', '--output', str(tmp_path)]
    if cpu_percent == 100:
        args += ['--cpu-percent', '100']
    main(args)
    assert bool(clock['sleeps']) == (cpu_percent < 100)
    metrics = json.loads((tmp_path / 'matrix.json').read_text())
    assert metrics and {row['percent'] for row in metrics} == {100, 125}
    assert {row['cpu_percent'] for row in metrics} == {cpu_percent}
    assert len(backends) == 2
    assert all(not backend.is_running for backend in backends)


def test_prototype_paid_preparation_and_saved_orders_share_the_allowance(clock):
    """Paid troops and an explicit detached hold keep exact forecasts and snapshots when paced."""
    from tools.prototype_eador_relief import Orders, create, forward, prepare

    expected = prepare(budget=CpuBudget(100))
    baseline = forward(Orders(create(expected, 'forward'), budget=CpuBudget(100))).report()
    assert not clock['sleeps']
    budget = CpuBudget(25)
    actual = prepare(budget=budget)
    assert clock['sleeps'], 'Prototype preparation bypassed its allowance'
    assert actual.to_json() == expected.to_json()
    assert actual.purchases == expected.purchases
    clock['sleeps'].clear()
    played = forward(Orders(create(actual, 'forward'), budget=budget)).report()
    assert clock['sleeps'], 'Prototype orders bypassed the shared allowance'
    assert played == baseline
    assert played['outcome'] == 'hold'


def test_bounded_prototype_cli_preserves_search_and_world_results_with_default_pacing(clock, tmp_path):
    """Two trials per approach and two world seeds exercise real CLI forwarding without the full search."""
    from tools.prototype_eador_relief import main

    path = tmp_path / 'prototype.json.gz'
    args = ['--output', str(path), '--trials', '2', '--world-seeds', '2']
    main([*args, '--cpu-percent', '100'])
    assert not clock['sleeps']
    expected = json.loads(gzip.decompress(path.read_bytes()))
    main(args)
    assert clock['sleeps'], 'The prototype CLI bypassed its default allowance'
    actual = json.loads(gzip.decompress(path.read_bytes()))
    assert actual['cpu_percent'] == 25
    assert 'tools/cpu_budget.py' in actual['source_sha256']
    for field in ('parties', 'plans', 'automatic', 'passive_search', 'source_audit'):
        assert actual[field] == expected[field]
    for result in actual['passive_search'].values():
        assert result['trials'] == sum(result['outcomes'].values()) == 2
    assert actual['source_audit']['seeds_per_theme'] == 2


def test_detached_search_and_world_audit_each_yield_without_changing_results(clock):
    """Each formerly long loop must yield independently of preparation and explicit orders."""
    from tools.prototype_eador_relief import passive_search, prepare, source_audit

    party = prepare(budget=CpuBudget(100))
    before = party.to_json()
    expected = passive_search({'commander': party}, trials=2, budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = passive_search({'commander': party}, trials=2, budget=CpuBudget(25))
    assert clock['sleeps'], 'The detached search itself must yield'
    assert actual == expected and party.to_json() == before

    clock['sleeps'].clear()
    expected = source_audit(seed_count=2, budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = source_audit(seed_count=2, budget=CpuBudget(25))
    assert clock['sleeps'], 'The world audit itself must yield'
    assert actual == expected


@pytest.mark.parametrize('name', ['saves', 'results'])
def test_verifier_closes_both_actual_mock_backends_after_its_input_journey(name, tmp_path, monkeypatch):
    """The real verifier must quit its initial and restarted backends after completing input checks."""
    from importlib import import_module
    from saga2d.backends.mock_backend import MockBackend

    backends = []

    class ObservedBackend(MockBackend):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            backends.append(self)

    monkeypatch.setattr('saga2d.backends.mock_backend.MockBackend', ObservedBackend)
    verify = import_module('tools.verify_eador_' + name).verify
    verify(tmp_path, backend='mock')
    assert len(backends) == 2
    assert all(not backend.is_running for backend in backends)


def test_replacement_prototype_battle_and_investment_each_yield_without_changing_results(clock):
    """One retained battle and the bounded paid ledger comparison preserve outcomes while yielding independently."""
    from tools.prototype_eador_army_replacement import exercise, investment_observation

    examples = Path(__file__).resolve().parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    payload = json.loads(examples.read_text())['late_full_roster']['state']
    before = json.dumps(payload, sort_keys=True)
    expected = exercise(payload, budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = exercise(payload)
    assert clock['sleeps'], 'The prototype battle loop itself must yield'
    assert actual == expected and actual['rounds']

    clock['sleeps'].clear()
    expected = investment_observation(payload, budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = investment_observation(payload)
    assert clock['sleeps'], 'The paid observed/baseline campaign comparison must yield'
    assert actual == expected and actual['ledger']
    assert json.dumps(payload, sort_keys=True) == before
