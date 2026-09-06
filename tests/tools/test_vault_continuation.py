"""A paid adventure comparison must retain its real preparation and later consequences."""
from eador.model import State


def test_vault_approaches_share_an_earned_army_and_preserve_their_campaign_consequences():
    """Follow ordinary purchases, both manual escapes and bounded rival-aware continuation."""
    from tools.audit_eador_vault_continuation import compare

    report = compare()
    entry = State.from_json(report['entry_state'])
    assert entry.hero.pos == (-1, 1)
    assert entry.provinces[entry.hero.pos].site_kind == 'sealed_vault'
    assert {troop.kind for troop in entry.hero.army} >= {'warden', 'ranger'}
    preparation = report['preparation_commands']
    assert any(order['command'] == 'recruit' and order['args'] == ('warden',) for order in preparation)
    assert any(order['command'] == 'recruit' and order['args'] == ('ranger',) for order in preparation)
    assert report['branches']['crossfire']['entry_fee_crystals'] == 0
    assert report['branches']['unseal']['entry_fee_crystals'] == 2
    for commands, initial, final in [
        (preparation, report['initial_state'], report['entry_state']),
        *((branch['commands'], report['entry_state'], branch['final_state'])
          for branch in report['branches'].values()),
    ]:
        previous = initial
        for order in commands:
            assert order['before'] == previous
            assert State.from_json(order['after']).to_json() == order['after']
            previous = order['after']
        assert previous == final
    for branch in report['branches'].values():
        resolved = State.from_json(branch['vault']['resolved_state'])
        final = State.from_json(branch['final_state'])
        assert resolved.provinces[(-1, 1)].explored
        assert final.provinces[(-1, 1)].explored
        assert branch['campaign_orders'] <= report['campaign_order_limit']
        assert all(turn['reason'] for turn in branch['end_turns'])
        assert branch['replacement_gold'] == sum(order['gold_spent'] for order in branch['replacement_purchases'])
        assert not any(order['command'] in ('build', 'replace_troop', 'infuse')
                       for order in branch['commands'])


def test_campaign_order_bound_keeps_the_actual_unfinished_position_without_cleanup_turns():
    """One allowed aftermath order ends at its real save, without funding or forcing the objective."""
    from tools.audit_eador_vault_continuation import compare

    report = compare(campaign_order_limit=1)
    entry = State.from_json(report['entry_state'])
    for branch in report['branches'].values():
        final = State.from_json(branch['final_state'])
        assert branch['stop_reason'] == 'campaign_order_bound'
        assert branch['campaign_orders'] == len(branch['decisions']) == 1
        assert branch['capture'] is None
        assert not branch['rival_operation_after_capture']
        assert final.status == 'playing' and final.battle is None
        assert final.provinces[(0, 0)].owner != 'player'
        assert not final.provinces[(0, 0)].explored
        assert len(branch['end_turns']) == 1
        assert final.turn == entry.turn + 1
        assert branch['commands'][-1]['command'] == 'end_turn'
        assert branch['commands'][-1]['after'] == branch['final_state']
