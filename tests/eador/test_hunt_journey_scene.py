"""Paid preparations and all three Hunt plans execute through the same real-input adapter."""
import pytest


@pytest.mark.parametrize('plan,rounds,cost', [('compact', 3, 0), ('lure', 2, 20), ('spears', 3, 0)])
def test_hunt_manual_orders_keep_the_selected_cost_and_reward_once(tmp_path, plan, rounds, cost):
    from tools.verify_eador_pack_hunt import verify
    report = verify(tmp_path, backend='mock', plan=plan)
    assert report['battle_rounds'] == rounds and report['fee_gold'] == cost
    assert report['reward_gold'] == 55 and report['reward_relic'] == 'storm_quiver'
    assert report['exact_save_reloads'] >= 2 and report['troops_lost'] == 0
