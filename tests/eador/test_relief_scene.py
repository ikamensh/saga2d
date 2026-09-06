"""Paid Relief routes execute through the same visible controls as the native verifier."""
import pytest
from tools.verify_eador_relief import verify


@pytest.mark.parametrize('plan', ['forward', 'western', 'scout', 'passive', 'failed-retry'])
def test_paid_relief_manual_orders_and_saved_recovery_use_actual_player_input(tmp_path, plan):
    """Read both approaches, spend actual orders, reload and receive the recorded reward once."""
    report = verify(tmp_path, backend='mock', plan=plan)
    assert report['outcome_reason'] == ('rout' if plan == 'failed-retry' else 'hold')
    assert report['exact_save_reloads'] > 0
    assert all(u['hp'] > 0 for u in report['survivors'])


def test_retry_briefing_keeps_flight_advice_after_its_rally_support_dies(tmp_path):
    """An earned, saved retreat must not recommend killing the already-defeated Militia."""
    from saga2d import Label
    from eador.app import create_game
    from eador.model import State
    from eador.persistence import CampaignSaves
    from eador.scene import ShardScene
    from tools.eador_extraction_campaign import AdventureOrders
    from tools.eador_relief_campaign import prepare_relief, relief_forward_opening
    from tools.eador_ui import PlayerInput

    state = prepare_relief()
    state.explore(approach='forward')
    relief_forward_opening(AdventureOrders(state))
    state.retreat()
    assert state.provinces[state.hero.pos].site_guards == ['skyrider', 'archer', 'guard']
    saved = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        CampaignSaves(game.save_manager).save(state)
        game.push(ShardScene(State.new(7)))
        player = PlayerInput(game)
        player.press('f9')
        assert player.state.to_json() == saved
        player.press('x')
        player.press('t'); player.press('right'); player.press('return')
        for approach in ('1', '2'):
            player.press(approach)
            text = '\n'.join(c.text for c in game.scene.ui.walk() if isinstance(c, Label))
            assert 'Skyrider crosses occupied cells; deny its landing.' in text
            assert 'remove support' not in text and "Militia clears adjacent allies' Pin" not in text
            assert player.state.to_json() == saved
    finally:
        game._teardown()
