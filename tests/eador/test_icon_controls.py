"""The icon presentation keeps ordinary game input and explanatory text usable."""

from eador.model import State
from tools.verify_eador_icons import verify
import pytest


def test_icon_journey_preserves_input_explanations_and_exact_saves(tmp_path):
    """One fresh route exercises real toolbar and combat controls through both click and keys."""
    receipt = verify(tmp_path, backend='mock')
    assert receipt['exact_save_reloads'] >= 2
    assert receipt['final_reading_size'] == 125
    assert {item['label'] for item in receipt['toolbar_visits']} == {
        'Settings', 'Text size', 'Guide', 'Hero', 'Codex', 'Save', 'Load',
        'Build stronghold', 'Recruit troops', 'Rival plan', 'Campaign'}
    assert {item['command'] for item in receipt['command_checks']} >= {
        'end_turn', 'explore', 'battle.guard', 'battle.move', 'battle.attack'}
    assert {item['label'] for item in receipt['aiming_checks']} == {'Arcane Bolt'}
    assert {item['name'] for item in receipt['captures']} >= {
        'campaign-icons', 'campaign-reading-125', 'battle-icons', 'battle-reloaded'}
    assert {item['name'] for item in receipt['army_metrics']} == {'level', 'health'}
    assert {item['spell'] for item in receipt['spell_costs']} == {'bolt', 'heal'}
    assert {item['label'] for item in receipt['contextual_controls']} >= {'Explore current province', 'Invade province'}
    assert {item['name'] for item in receipt['metrics']} >= {
        'gold', 'crystals', 'income', 'upkeep', 'actions', 'health', 'mana',
        'attack', 'defense', 'move', 'range'}
    assert {item['shortcut'] for item in receipt['disabled_checks']} == {'2', 'p'}
    assert any(not item['enabled'] and item['reading_size'] == 125 for item in receipt['tooltips'])
    final = State.from_json(receipt['final_state'])
    assert final.seed == 7 and final.theme == 'frontier' and final.campaign and final.battle is not None
    assert any(unit.acted and unit.can_pin for unit in final.battle.units if unit.team == 'player')


@pytest.mark.parametrize('percent', [100, 125])
def test_inspected_enemy_stats_keep_each_symbol_and_value_together(tmp_path, percent):
    """A spent hero can inspect the Guard without a wrapped, detached Range value."""
    from saga2d import Image, Label, Row
    from eador.app import create_game
    from eador.scene import ShardScene
    from eador.ui import icon_path
    from tests.eador.test_attack_motion import melee_state
    from tools.eador_ui import PlayerInput
    from tools.verify_eador_guidance import check_reading_layout

    state, actor, target = melee_state()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state)); game.tick(0)
        player = PlayerInput(game, finish_actions=False)
        player.press('f2'); player.press('right' if percent == 125 else 'left'); player.press('return')
        player.order('battle.attack', actor, target)
        inspected = state.battle.unit(target)
        for name, value in (('attack', inspected.attack), ('defense', inspected.effective_defense),
                            ('range', inspected.attack_range)):
            row = game.scene.ui.find(lambda item: isinstance(item, Row) and item.tooltip
                                     and inspected.name in item.tooltip
                                     and any(isinstance(child, Image) and child.image == icon_path(name)
                                             for child in item.children))
            assert row is not None, 'Each inspected stat must retain its icon, value and meaning'
            label = next(child for child in row.children if isinstance(child, Label))
            assert label.text == str(value) and label.bounds[1] == row.bounds[1]
        check_reading_layout(game.scene)
        player.reload(state.to_json())
    finally:
        game.close()
