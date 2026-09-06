"""Tactical audit preparation yields without changing earned armies or public orders."""
from functools import partial

import pytest

from tools.cpu_budget import CpuBudget


@pytest.fixture
def clock(monkeypatch):
    """Only replace the clock boundary; paid preparation and combat remain real."""
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


def test_crossing_preparation_and_orders_yield_without_changing_the_earned_result(clock):
    """The purchased seven-body party and its actual escape match an unpaced run exactly."""
    from tools.eador_extraction_campaign import AdventureOrders, crossing_route, prepared_crossing

    expected = prepared_crossing()
    budget = CpuBudget(25)
    paced = prepared_crossing(budget=budget)
    assert clock['sleeps'], 'Paid preparation bypassed its CPU allowance'
    assert paced.to_json() == expected.to_json()
    clock['sleeps'].clear()
    outcome = crossing_route(paced, 'direct', orders_type=partial(AdventureOrders, budget=budget))
    baseline = crossing_route(expected, 'direct')
    assert clock['sleeps'], 'Explicit tactical orders bypassed the same allowance'
    assert outcome.battle.outcome_reason == 'escape'
    assert outcome.state.to_json() == baseline.state.to_json()


def test_scout_causeway_preparation_and_recorded_orders_share_the_allowance(clock):
    """Scout preparation and exact-save tactical recording preserve the same paid escape."""
    from tools.audit_eador_aerie import RecordedOrders
    from tools.eador_causeway_campaign import causeway_scout_route, prepare_causeway

    expected = prepare_causeway('Scout')
    budget = CpuBudget(25)
    paced = prepare_causeway('Scout', budget=budget)
    assert clock['sleeps'], 'The Scout preparation bypassed its CPU allowance'
    assert paced.to_json() == expected.to_json()
    clock['sleeps'].clear()
    outcome = causeway_scout_route(paced, orders_type=partial(RecordedOrders, budget=budget))
    baseline = causeway_scout_route(expected, orders_type=RecordedOrders)
    assert clock['sleeps'], 'Recorded commands bypassed the preparation allowance'
    assert outcome.battle.outcome_reason == 'escape'
    assert outcome.report() == baseline.report()


def test_hero_collection_preparation_defaults_to_pacing_without_changing_its_save(clock):
    """The fixed collection preparations yield by default and preserve every earned result."""
    from tools.verify_eador_hero import prepared_heroes

    expected = prepared_heroes(budget=CpuBudget(100))
    assert not clock['sleeps'], 'Explicit stress allowance must disable sleeping'
    actual = prepared_heroes()
    assert clock['sleeps'], 'Default model preparation must yield even before native inputs start'
    assert actual == expected
