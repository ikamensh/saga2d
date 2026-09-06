"""Actual Aerie purchases and manual lines are executable through the shipped controls."""
import pytest


@pytest.mark.parametrize('plan,rounds,wounds,mana,bodies', [
    ('western',4,53,4,7), ('western-heal',4,45,8,7), ('northern',3,34,8,7), ('scout',5,27,4,6),
])
def test_paid_aerie_input_plans_keep_exact_saves_and_reward_once(tmp_path, plan, rounds, wounds, mana, bodies):
    from tools.verify_eador_aerie import verify

    report = verify(tmp_path, backend='mock', plan=plan)
    assert (report['battle_rounds'],report['hp_deficit'],report['mana_spent']) == (rounds,wounds,mana)
    assert len(report['survivors']) == bodies and report['troops_lost'] == 0
    assert report['reading_scale'] == 125 and report['reward_relic'] == 'watch_bell'
    assert report['exact_save_reloads'] >= rounds + 3
    assert report['source_files_changed'] == []
    assert sum(p['gold'] for p in report['purchases']) == (200 if plan == 'scout' else 395)


def test_failed_aerie_inputs_keep_dead_guards_and_fund_the_retry(tmp_path):
    from tools.verify_eador_aerie import verify

    report = verify(tmp_path, backend='mock', plan='failed-retry')
    failure = report['failed_attempt']
    assert failure['outcome_reason'] == 'hero_death' and failure['round'] == 56
    assert failure['dead_troop_ids'] == [1,2,3,5,6]
    assert failure['retreat_gold'] == 20 and failure['replacement_gold'] == 60 and failure['replacement_crystals'] == 3
    assert failure['guards_on_retry'] == [['archer',12]] and not failure['reward_before_retry']
    assert report['battle_rounds'] == 1 and report['outcome_reason'] == 'rout'
