"""The Observatory's advertised price and tactical plan agree with its saved input journey."""


def test_paid_observatory_approach_spends_its_crystals_and_holds_through_visible_orders(tmp_path):
    """Pay for the actual army and lane, save the control orders, then claim the finite reward once."""
    from tools.verify_eador_observatory import verify

    report = verify(tmp_path, backend='mock')
    assert report['approach'] == 'clear' and report['fee_crystals'] == 2
    assert report['outcome_reason'] == 'hold' and report['troops_lost'] == 0
