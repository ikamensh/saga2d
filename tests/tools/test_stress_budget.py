"""Random tactical audits should yield without changing their reproducible work."""
from collections import Counter

import pytest

from tools.cpu_budget import CpuBudget


@pytest.mark.parametrize('scenario', ['control', 'roles', 'relic_preparation'])
def test_random_orders_yield_without_changing_saved_battles(monkeypatch, scenario):
    """A bounded random-order run preserves its results under a cooperative CPU allowance."""
    from tools import stress_eador_control, stress_eador_roles

    def run(budget):
        metrics = Counter()
        if scenario == 'relic_preparation':
            from tools.stress_eador_relics import earned_checkpoints
            return earned_checkpoints(budget=budget)
        if scenario == 'control':
            battle = stress_eador_control.fixture(0)
            stress_eador_control.exercise(0, metrics, battle=battle, budget=budget)
            return metrics, battle.to_dict()
        stress_eador_roles.exercise(0, metrics, budget=budget)
        return metrics

    expected = run(CpuBudget(100))
    clock = {'cpu': 0.0, 'wall': 0.0}
    sleeps = []

    def process_time():
        clock['cpu'] += .02
        clock['wall'] += .02
        return clock['cpu']

    def sleep(seconds):
        assert seconds > 0
        sleeps.append(seconds)
        clock['wall'] += seconds

    monkeypatch.setattr('tools.cpu_budget.time.process_time', process_time)
    monkeypatch.setattr('tools.cpu_budget.time.monotonic', lambda: clock['wall'])
    monkeypatch.setattr('tools.cpu_budget.time.sleep', sleep)
    assert run(CpuBudget(25)) == expected
    assert sleeps, 'The random tactical orders completed without yielding CPU'
