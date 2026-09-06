"""Purchased Screen plans are executable through the shipped controls."""
import pytest


@pytest.mark.parametrize('plan,rounds,party', [('western', 4, 6), ('western-heal', 5, 6),
                                               ('northern', 5, 6), ('scout', 6, 5)])
def test_paid_screen_controls_preserve_saved_orders_and_claim_the_reward_once(tmp_path, plan, rounds, party):
    from tools.verify_eador_screen import verify

    report = verify(tmp_path, backend='mock', plan=plan)
    assert report['outcome_reason'] == 'rout' and report['battle_rounds'] == rounds
    assert len(report['survivors']) == party and report['troops_lost'] == 0
    assert report['reading_scale'] == 125 and report['briefing_checked']
    assert report['fee_gold'] == report['fee_crystals'] == 0
    assert report['building_gold'] == 100 and report['recruitment_gold'] > 0
    if plan == 'northern':
        assert report['rallied_after_shooting']
    elif plan == 'scout':
        assert report['sapper_denied_before_charge'] and not report['smoke_seen']


def test_failed_screen_controls_keep_losses_and_fund_replacements_before_reward(tmp_path):
    from tools.verify_eador_screen import verify

    report = verify(tmp_path, backend='mock', plan='failed-retry')
    failed = report['failed_attempt']
    assert failed['outcome_reason'] == 'hero_death' and failed['dead_troop_ids'] == [2, 3, 5]
    assert failed['replacement_gold'] == 180 and failed['retreat_gold'] == 20
    assert failed['guards_on_retry'] == [['archer', 20]] and not failed['reward_before_retry']
    assert report['outcome_reason'] == 'rout' and report['battle_rounds'] == 3
