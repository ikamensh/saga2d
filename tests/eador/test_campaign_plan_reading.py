"""Campaign objectives stay complete while reading settings and map selection change."""

from saga2d import Button, Label

from eador.app import create_game
from eador.campaign_scene import CampaignPlanScene, campaign_targets
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ShardScene
from tools.eador_linked_campaign import play_stage
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_earned_foundry_plan_reflows_without_spending_and_locates_its_saved_objectives(tmp_path):
    """A real second-stage contract survives reading preview/restart; mouse and number locate the shown targets."""
    state = play_stage(State.new_campaign())
    state.advance('foundries')
    before = state.to_json()
    saves = tmp_path / 'saves'
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('j')
        assert isinstance(game.scene, CampaignPlanScene)
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert reading_scale(game) == 100 and not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return', 'h', 'escape'):
            player.press(key)
        assert isinstance(game.scene, CampaignPlanScene) and reading_scale(game) == 125
        assert state.to_json() == before
        check_reading_layout(game.scene)
        labels = [item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label))]
        assert state.campaign.objective in labels
        assert state.assault_blocked_reason in labels
        targets = campaign_targets(state)
        assert all(f'{index + 1}. {label}' in labels for index, (_, label, _) in enumerate(targets))
        assert any(record['text'] == f'1. {targets[0][1]}' and record['font_size'] == 20
                   for record in game.backend.texts)
        locate = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Locate')
        x, y, width, height = locate.bounds
        player.click(x + width / 2, y + height / 2)
        assert isinstance(game.scene, ShardScene) and game.scene.selected == targets[0][0]
        assert state.to_json() == before
        player.reload(before)
    finally:
        game._teardown()

    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(State.from_json(before)))
        player = PlayerInput(game)
        player.press('j')
        assert reading_scale(game) == 125
        check_reading_layout(game.scene)
        player.press('2')
        assert isinstance(game.scene, ShardScene) and game.scene.selected == targets[1][0]
        assert player.state.to_json() == before
    finally:
        game._teardown()
