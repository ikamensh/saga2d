"""Retained economic experiments yield without altering paid public outcomes."""

import json
from pathlib import Path

import pytest

from saga2d.testing.cpu_budget import CpuBudget


@pytest.fixture
def clock(monkeypatch):
    """Fake only CPU/wall time; every campaign, battle and save stays real."""
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


def test_late_realm_paid_plan_yields_without_changing_its_economy(clock):
    """One real paid campaign retains its outcome and cash ledger when paced."""
    from tools.prototype_eador_late_realm import MeasuredState, paid_plan

    case = (0, 'Commander', 'frontier', 'economy', 'standard', 'direct')
    expected = paid_plan(case, MeasuredState, budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = paid_plan(case, MeasuredState)
    assert clock['sleeps'], 'The default paid-plan loop must yield'
    assert actual == expected and actual['cash_flow']
    assert actual['result']['metrics']['battles'] > 0


def test_veteran_recovery_preparation_and_waiting_each_yield_without_changing_results(clock):
    """A paid departure, actual loss and recovery retain their saves and later wage costs."""
    from tools.prototype_eador_veteran_upkeep import SalaryOne, recovery_input, recovery_probe

    expected = recovery_input('standard', budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = recovery_input('standard')
    assert clock['sleeps'], 'Paid recovery preparation must yield'
    assert actual == expected and actual['campaign']['recovery_used']

    clock['sleeps'].clear()
    expected_probe = recovery_probe(expected, SalaryOne, 'wait_three', budget=CpuBudget(100))
    assert not clock['sleeps']
    actual_probe = recovery_probe(actual, SalaryOne, 'wait_three')
    assert clock['sleeps'], 'Recovery waiting must yield independently of preparation'
    assert actual_probe == expected_probe and len(actual_probe['events']) == 4


def test_camp_service_and_actual_battle_yield_without_changing_paid_outcome(clock):
    """A retained paid camp keeps its service cost, battle and original save when yielding."""
    from tools.prototype_eador_camp_services import exercise

    path = Path(__file__).resolve().parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    payload = json.loads(path.read_text())['pre_assault_mana']['state']
    before = json.dumps(payload, sort_keys=True)
    expected = exercise(payload, 'infusion', budget=CpuBudget(100))
    assert not clock['sleeps']
    actual = exercise(payload, 'infusion')
    assert clock['sleeps'], 'The camp service continuation must yield'
    assert actual == expected and actual['metrics']['battles'] == 1
    assert actual['before']['crystals'] > actual['after_preparation']['crystals']
    assert json.dumps(payload, sort_keys=True) == before
