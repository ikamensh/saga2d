"""Reading campaign transitions must not alter the reviewed departure or saved journey."""

from eador.app import create_game
from eador.campaign_scene import CampaignScene
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ShardScene
from tools.eador_linked_campaign import play_stage
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
import pytest


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


def test_reflow_keeps_the_page_anchor_and_moves_hidden_focus_before_space(tmp_path):
    """An earned last-row relic remains kept when Settings or resizing makes its former page shorter."""
    from tools.verify_eador_campaign_reading import verify_reflow
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        verify_reflow(PlayerInput(game))
    finally:
        game._teardown()


def test_earned_and_legacy_transitions_show_complete_facts_at_each_supported_reading_size(tmp_path):
    """Current modes, both finales, recovered/declined endings and old Challenge rules retain exact saved facts."""
    from tools.verify_eador_campaign_reading import verify
    verify(tmp_path, backend='mock')



@pytest.mark.parametrize('recovery', [False, True])
def test_complete_checkpoint_error_keeps_decision_pending_until_exact_manual_remedy(tmp_path, recovery):
    """Damaged autosaves, Settings and repeated Enter cannot spend a transition before a valid checkpoint."""
    from saga2d import Label
    from eador.persistence import AUTO_SLOTS, CampaignSaves
    from tools.eador_linked_campaign import lose_shard

    state = State.new_campaign()
    state = lose_shard(state) if recovery else play_stage(state)
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        saves = CampaignSaves(game.save_manager)
        for _ in AUTO_SLOTS:
            saves.autosave(state)
        paths = list((tmp_path / 'saves').glob('*.json'))
        for path in paths:
            path.write_bytes(b'Damaged autosave')
        game.push(ShardScene(state)); game.tick(1 / 60)
        player = PlayerInput(game)
        if not recovery:
            player.press('1')
        player.press('space')
        selected = game.scene.troop_ids.copy()
        for key in ('return', 'return', 't', 'right', 'return', 'f6', 'escape'):
            player.press(key)
        scene = game.scene
        assert isinstance(scene, CampaignScene) and state.to_json() == before and scene.troop_ids == selected
        assert scene.message.startswith('Autosave failed')
        assert scene.message in [item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))]
        check_reading_layout(scene)
        player.press('f5')
        # One batch cannot advance twice, even though the successful callback reveals a new scene.
        game.backend.inject_key('return'); game.backend.inject_key('return'); game.tick(1 / 60)
        assert isinstance(game.scene, ShardScene) and state.campaign.phase == 'playing'
        assert state.campaign.recovery_used if recovery else state.campaign.stage == 2
        assert all(path.read_bytes() == b'Damaged autosave' for path in paths)
        player.press('f9')
        assert player.state.to_json() == before
    finally:
        game._teardown()


def test_long_real_filesystem_error_is_read_in_full_without_hidden_retinue_actions(tmp_path):
    """A valid deep directory cannot consume the row budget or hide a Space-triggered selection."""
    from tools.verify_eador_campaign_reading import verify_long_error
    verify_long_error(tmp_path, backend='mock')
