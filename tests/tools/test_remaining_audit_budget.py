"""Remaining authored audits yield while preserving their paid public outcomes."""
from functools import partial
import gzip
import json

import pytest

from eador.model import State
from saga2d.testing.cpu_budget import CpuBudget


@pytest.fixture
def clock(monkeypatch):
    """Control only elapsed CPU/wall time; all game rules and paid commands remain real."""
    samples = {'cpu': 0.0, 'wall': 0.0, 'sleeps': []}

    def process_time():
        samples['cpu'] += .06
        samples['wall'] += .06
        return samples['cpu']

    def sleep(seconds):
        samples['sleeps'].append(seconds)
        samples['wall'] += seconds

    monkeypatch.setattr('saga2d.testing.cpu_budget.time.process_time', process_time)
    monkeypatch.setattr('saga2d.testing.cpu_budget.time.monotonic', lambda: samples['wall'])
    monkeypatch.setattr('saga2d.testing.cpu_budget.time.sleep', sleep)
    return samples


def test_resource_quotes_yield_without_spending_the_campaigns_resources(clock):
    """Detached purchase quotes share the allowance but never mutate the observed campaign."""
    from tools.audit_eador_resource_breakpoints import options

    state = State.new(0)
    saved = state.to_json()
    expected = options(state)
    actual = options(state, budget=CpuBudget(25))
    assert actual == expected
    assert clock['sleeps'], 'The detached quote loop bypassed the audit allowance'
    assert state.to_json() == saved


def test_selected_resource_audit_cli_paces_observed_and_baseline_campaigns(clock, tmp_path):
    """One real CLI case reports its default allowance and retains every public outcome and quote."""
    from tools.audit_eador_resource_breakpoints import main

    path = tmp_path / 'resources.json'
    args = ['--theme', 'frontier', '--difficulty', 'standard', '--plan', 'economy', '--report', str(path)]
    main([*args, '--cpu-percent', '100'])
    assert not clock['sleeps']
    expected = json.loads(gzip.decompress(path.with_suffix('.rows.json.gz').read_bytes()))
    main(args)
    report = json.loads(path.read_text())
    assert report['cpu_percent'] == 25 and report['campaigns'] == 1
    assert 'tools/audit_eador_resource_breakpoints.py' in report['source_sha256']
    assert clock['sleeps'], 'The selected observed/baseline pair bypassed its CPU allowance'
    assert json.loads(gzip.decompress(path.with_suffix('.rows.json.gz').read_bytes())) == expected


@pytest.mark.parametrize('name,theme,expected_reason', [('aerie', 'ruins', 'rout'), ('relief', 'frontier', 'hold')])
def test_authored_preparation_and_recorded_commands_preserve_paid_results(clock, name, theme, expected_reason):
    """One earned Commander route keeps its purchases and exact saved orders while yielding."""
    from importlib import import_module
    from tools.audit_eador_aerie import Purchases, RecordedOrders

    campaign = import_module('tools.eador_' + name + '_campaign')
    prepare = getattr(campaign, 'prepare_' + name)
    route = getattr(campaign, name + ('_western_route' if name == 'aerie' else '_forward_route'))
    expected = prepare(state=Purchases(State.new(7, theme=theme)))
    budget = CpuBudget(25)
    actual = prepare(state=Purchases(State.new(7, theme=theme)), budget=budget)
    assert clock['sleeps'], 'Paid preparation bypassed its CPU allowance'
    assert actual.to_json() == expected.to_json() and actual.purchases == expected.purchases
    clock['sleeps'].clear()
    played = route(actual, orders_type=partial(RecordedOrders, budget=budget))
    baseline = route(expected, orders_type=RecordedOrders)
    assert clock['sleeps'], 'Recorded battle commands bypassed the shared allowance'
    assert played.battle.outcome_reason == expected_reason
    assert played.report() == baseline.report()


def test_pin_verifiers_earned_bell_preparation_yields_without_changing_the_battle(clock):
    """The verifier's model-only work defaults to pacing before it opens the earned Brace UI."""
    from tools.verify_eador_pin import prepare_watch_bell

    expected = prepare_watch_bell(budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = prepare_watch_bell()
    assert clock['sleeps'], 'Pin model preparation bypassed the default allowance'
    assert actual.battle.unit(0).can_brace
    assert actual.to_json() == expected.to_json()
