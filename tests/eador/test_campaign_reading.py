"""Reading campaign transitions must not alter the reviewed departure or saved journey."""

from eador.app import create_game
from eador.campaign_scene import CampaignScene
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ShardScene
from tools.eador_linked_campaign import play_stage
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_saved_departure_reflows_without_losing_retinue_or_cursor(tmp_path):
    """Settings preview/cancel, apply and restart preserve the real earned state and selected IDs."""
    state = play_stage(State.new_campaign())
    before = state.to_json()
    saves = tmp_path / 'saves'
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state)); game.tick(1 / 60)
        player = PlayerInput(game)
        player.press('1'); player.press('space'); player.press('right'); player.press('space')
        scene = game.scene
        selected = scene.troop_ids.copy(), scene.relic_ids.copy()
        cursors = scene.cursors.copy()
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert game.scene is scene and reading_scale(game) == 100
        assert not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return'):
            player.press(key)
        assert game.scene is scene and reading_scale(game) == 125
        assert (scene.troop_ids, scene.relic_ids) == selected and scene.cursors == cursors
        check_reading_layout(scene)
        assert state.to_json() == before
        player.press('f5')
        player.press('return')
        assert isinstance(game.scene, ShardScene) and state.campaign.stage == 2
        assert selected[0] <= {troop.id for troop in state.hero.army}
        assert set(state.inventory) == selected[1]
        player.press('f9')
        assert isinstance(game.scene, CampaignScene) and player.state.to_json() == before
    finally:
        game._teardown()
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(State.from_json(before))); game.tick(1 / 60)
        assert reading_scale(game) == 125
        check_reading_layout(game.scene)
    finally:
        game._teardown()
