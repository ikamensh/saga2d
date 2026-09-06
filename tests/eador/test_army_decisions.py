"""Earned tactical choices should preserve their consequences through paid replenishment."""

import hashlib

from eador.model import State


def test_current_branches_preserve_the_adept_through_paid_aftermath_and_keep_historical_provenance():
    """Improved autoplay can differ from history while both current branches save every paid command."""
    from tools.audit_eador_army_decisions import compare
    report = compare('control')
    historical = report['source']['historical_first_after']
    assert State.from_json(historical).battle.unit(6).hp == 0
    assert hashlib.sha256(historical.encode()).hexdigest() == report['source']['historical_first_after_sha256']
    current = report['auto']['commands'][0]['after']
    assert State.from_json(current).battle.unit(6).hp > 0
    assert hashlib.sha256(current.encode()).hexdigest() == report['current_first_after_sha256']
    assert report['historical_first_after_matches_current'] is False
    for name in ('auto', 'manual'):
        branch = report[name]
        assert branch['outcome'] == 'player'
        state = State.from_json(branch['replenished'])
        assert any(t.id == 6 and t.kind == 'adept' and t.hp > 0 for t in state.hero.army)
        assert not branch['missing_roles']
        before = report['initial_state']
        for command in branch['commands']:
            assert command['before'] == before
            assert State.from_json(command['after']).to_json() == command['after']
            before = command['after']
        assert before == branch['replenished']
        assert any(command['command'] == 'resolve_battle' for command in branch['commands'])
        assert branch['purchase_gold'] == sum(command['gold_spent'] for command in branch['purchase_commands'])
        assert branch['purchase_crystals'] == sum(command['crystals_spent'] for command in branch['purchase_commands'])
