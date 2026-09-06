"""Earned equipment exposes the same saved tactical orders as ordinary troops."""
import pytest


def test_earned_censer_screens_a_later_hold_through_saved_player_input(tmp_path):
    """Pay for the army, escape with loot, equip it, and use the hero's exact forecast."""
    from tools.verify_eador_relics import verify

    report = verify(tmp_path, backend='mock')
    assert report['relic'] == 'veil_censer'
    assert report['outcome_reason'] == 'hold'
    assert report['exact_save_reloads'] >= 6


@pytest.mark.parametrize('relic', ['porter_rune', 'mirror_badge'])
def test_earned_relic_survives_two_visible_departures_and_wins_the_final_gate(tmp_path, relic):
    """Real retinue choices carry the earned relic; hero use and the resulting victory are saved."""
    from tools.verify_eador_relics import verify

    report = verify(tmp_path, backend='mock', relic=relic)
    assert report['relic'] == relic
    assert report['outcome_reason'] == 'hold'
    assert report['campaign_phase'] == 'completed'
