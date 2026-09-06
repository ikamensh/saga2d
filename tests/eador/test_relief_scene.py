"""Paid Relief routes execute through the same visible controls as the native verifier."""
import pytest
from tools.verify_eador_relief import verify


@pytest.mark.parametrize('plan', ['forward', 'western', 'scout', 'passive', 'failed-retry'])
def test_paid_relief_manual_orders_and_saved_recovery_use_actual_player_input(tmp_path, plan):
    """Read both approaches, spend actual orders, reload and receive the recorded reward once."""
    report = verify(tmp_path, backend='mock', plan=plan)
    assert report['outcome_reason'] == ('rout' if plan == 'failed-retry' else 'hold')
    assert report['exact_save_reloads'] > 0
    assert all(u['hp'] > 0 for u in report['survivors'])
