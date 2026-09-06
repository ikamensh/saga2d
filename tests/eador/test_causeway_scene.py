"""Causeway guidance quotes actual sources and remains truthful after a saved failure."""
import pytest
from saga2d import Label
from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.scene import ShardScene
from tools.eador_causeway_campaign import prepare_causeway, causeway_failed_attempt
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_causeway_briefing_teaches_choices_at_both_sizes_and_removes_dead_caster_advice(tmp_path):
    """The source has one free assembly; surviving-roster advice changes without spending an order."""
    fresh = prepare_causeway()
    failed = causeway_failed_attempt(prepare_causeway())
    failed.state.resolve_battle()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        for state, caster_present in ((fresh, True), (failed.state, False)):
            game.clear_and_push(ShardScene(state))
            player = PlayerInput(game)
            before = state.to_json()
            player.press('x')
            assert isinstance(game.scene, EncounterScene)
            assert len(game.scene.approaches) == 1
            for percent in (100, 125):
                player.press('t'); player.press('left' if percent == 100 else 'right'); player.press('return')
                labels = '\n'.join(c.text for c in game.scene.ui.walk() if isinstance(c, Label))
                assert ('one Repulse charge' in labels) == caster_present
                assert '45 gold · 2 crystals · Moonstone' in labels
                assert 'round 5' in labels and 'cargo slows the hero by 1' in labels
                check_reading_layout(game.scene)
                assert state.to_json() == before
            player.press('escape')
            assert isinstance(game.scene, ShardScene) and state.to_json() == before
    finally:
        game._teardown()


@pytest.mark.parametrize('plan', ['focus', 'guard', 'backstop', 'infused-guard', 'scout', 'scout-heal', 'failed-retry'])
def test_paid_causeway_orders_and_saved_retry_use_actual_player_input(tmp_path, plan):
    """Read the real reward, execute paid commands, checkpoint and finish this finite site once."""
    from tools.verify_eador_causeway import verify
    report = verify(tmp_path, backend='mock', plan=plan)
    assert report['exact_save_reloads'] > 0
    assert all(unit['hp'] > 0 for unit in report['survivors'])
