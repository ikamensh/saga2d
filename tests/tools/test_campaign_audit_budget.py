"""Campaign audit pacing must preserve the public policy's complete saved outcome."""

from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_linked_campaign import play_linked


def test_linked_audit_yields_within_the_journey_without_changing_its_outcome():
    """One shared CPU allowance follows the same paid army through all three shards."""
    class ObservedBudget(CpuBudget):
        def __init__(self):
            super().__init__(25)
            self.checkpoints = 0

        def checkpoint(self):
            self.checkpoints += 1
            super().checkpoint()

    budget = ObservedBudget()
    paced = play_linked(7, middle='foundries', finale='throne', budget=budget)
    expected = play_linked(7, middle='foundries', finale='throne')
    assert paced.campaign.phase == 'completed'
    assert paced.to_json() == expected.to_json()
    assert budget.checkpoints > len(paced.campaign.completed)
