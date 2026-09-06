"""Earned tactical choices should preserve their consequences through paid replenishment."""

from eador.model import State


def test_ready_finishing_attacks_preserve_the_wounded_adept_and_its_replacement_cost():
    """A real earned party can win before sending its fragile specialist into retaliation."""
    from tools.audit_eador_army_decisions import compare
    report = compare('control')
    manual = report['manual']
    state = State.from_json(manual['replenished'])
    assert manual['outcome'] == 'player'
    assert any(t.id == 6 and t.kind == 'adept' and t.hp > 0 for t in state.hero.army)
    assert manual['purchase_gold'] < report['auto']['purchase_gold']
    assert manual['round'] == report['auto']['round']
