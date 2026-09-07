"""The icon presentation keeps ordinary game input and explanatory text usable."""

from eador.model import State
from tools.verify_eador_icons import verify


def test_icon_journey_preserves_input_explanations_and_exact_saves(tmp_path):
    """One fresh route exercises real toolbar and combat controls through both click and keys."""
    receipt = verify(tmp_path, backend='mock')
    assert receipt['exact_save_reloads'] == 2
    assert receipt['final_reading_size'] == 125
    assert len(receipt['captures']) == 10
    assert {item['label'] for item in receipt['toolbar_visits']} == {
        'Settings', 'Text size', 'Guide', 'Hero', 'Codex', 'Save', 'Load'}
    assert {item['name'] for item in receipt['metrics']} >= {
        'gold', 'crystals', 'income', 'upkeep', 'actions', 'health', 'mana',
        'attack', 'defense', 'move', 'range'}
    assert {item['shortcut'] for item in receipt['disabled_checks']} == {'2', 'p'}
    assert any(not item['enabled'] and item['reading_size'] == 125 for item in receipt['tooltips'])
    final = State.from_json(receipt['final_state'])
    assert final.seed == 7 and final.theme == 'frontier' and final.battle is not None
    assert any(unit.acted and unit.can_pin for unit in final.battle.units if unit.team == 'player')
