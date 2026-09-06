"""Earned equipment exposes the same saved tactical orders as ordinary troops."""


def test_earned_censer_screens_a_later_hold_through_saved_player_input(tmp_path):
    """Pay for the army, escape with loot, equip it, and use the hero's exact forecast."""
    from tools.verify_eador_relics import verify

    report = verify(tmp_path, backend='mock')
    assert report['relic'] == 'veil_censer'
    assert report['outcome_reason'] == 'hold'
    assert report['exact_save_reloads'] >= 6
