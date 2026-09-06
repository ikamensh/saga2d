"""Audit pacing must preserve the real campaign decisions it measures."""

from tools.audit_eador_difficulty import DifficultyTrial


def test_budgeted_paid_campaign_preserves_all_results_and_yields_between_orders():
    """The same earned economy route has identical costs, losses and saved final state."""
    class Budget:
        def __init__(self):
            self.checkpoints = 0

        def checkpoint(self):
            self.checkpoints += 1

    case = (0, 'Commander', 'ruins', 'economy', 'standard', 'direct')
    expected = DifficultyTrial(*case).run()
    budget = Budget()
    assert DifficultyTrial(*case, budget=budget).run() == expected
    assert budget.checkpoints > expected['metrics']['battles']
