"""The Observatory's advertised price and tactical plan agree with its saved input journey."""


def test_paid_observatory_approach_spends_its_crystals_and_holds_through_visible_orders(tmp_path):
    """Pay for the actual army and lane, save the control orders, then claim the finite reward once."""
    from tools.verify_eador_observatory import verify

    report = verify(tmp_path, backend='mock')
    assert report['approach'] == 'clear' and report['fee_crystals'] == 2
    assert report['outcome_reason'] == 'hold' and report['troops_lost'] == 0


def test_the_same_visible_rune_orders_hold_both_lanes_and_show_the_paid_health_tradeoff(tmp_path):
    """The fee saves wounds in a matched battle, with every Repulse and reward passing through input."""
    from tools.verify_eador_observatory import verify

    free = verify(tmp_path / 'covered', backend='mock', support='adept', approach='covered')
    paid = verify(tmp_path / 'clear', backend='mock', support='adept', approach='clear')
    assert free['orders'] == paid['orders']
    assert free['battle_rounds'] == paid['battle_rounds']
    assert free['fee_crystals'] == 0 and paid['fee_crystals'] == 2
    assert free['hp_deficit'] > paid['hp_deficit']
    for report in (free, paid):
        assert report['outcome_reason'] == 'hold' and report['troops_lost'] == 0
        assert any(command == 'repulse' for command, *_ in report['orders'])
