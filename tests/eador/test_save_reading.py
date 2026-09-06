"""The save browser keeps whole slot descriptions and errors readable without changing progress."""
from saga2d import Label, SaveManager
from eador.app import create_game
from eador.model import State
from eador.persistence import CampaignSaves
from eador.preferences import reading_scale
from eador.scene import SaveScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_save_browser_keeps_slot_and_current_campaign_through_reading_changes(tmp_path):
    """Text-size overlays preserve the current slot; an explicit visible manual save retains the whole campaign."""
    state = State.new_campaign(7)
    state.explore()
    before = state.to_json()
    saves = CampaignSaves(SaveManager(tmp_path / 'saves'))
    for slot in (1, 2, 3):
        saves.save(state, slot)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        from eador.scene import BattleScene
        game.push(ShardScene(state))
        assert isinstance(game.scene, BattleScene)
        player = PlayerInput(game)
        player.press('f6')
        assert isinstance(game.scene, SaveScene)
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert reading_scale(game) == 100
        for key in ('t', 'right', 'return'):
            player.press(key)
        assert isinstance(game.scene, SaveScene) and reading_scale(game) == 125
        assert player.state.to_json() == before
        labels = [item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label))]
        assert any('Stage 1/3' in text and 'Battle round 1' in text for text in labels)
        check_reading_layout(game.scene)
        player.press('tab')
        player.press('1')
        assert saves.load(1).to_json() == before
        assert player.state.to_json() == before
        player.press('escape')
        assert isinstance(game.scene, BattleScene)
    finally:
        game._teardown()


def test_failed_load_stays_readable_and_recovery_preserves_every_file(tmp_path):
    """A real bad file reflows the message; its explicit backup loads without rewriting the damaged current file."""
    import json
    state = State.new_campaign(7)
    original = state.to_json()
    directory = tmp_path / 'saves'
    saves = CampaignSaves(SaveManager(directory))
    saves.save(state)
    state.end_turn()
    saves.save(state)
    damaged = directory / 'save_1.json'
    damaged.write_text(json.dumps({'version': 'X' * 5000}))
    before_files = {path.name: path.read_bytes() for path in directory.iterdir()}
    (tmp_path / 'settings.json').write_text('{"codex_text_scale":125}')
    game = create_game(backend='mock', save_dir=directory)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('f6'); player.press('1')
        assert isinstance(game.scene, SaveScene)
        assert any('Save format version must be integer 1' in item.text
                   for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        check_reading_layout(game.scene)
        player.button('Backup')
        assert isinstance(game.scene, ShardScene) and player.state.to_json() == original
        assert {path.name: path.read_bytes() for path in directory.iterdir()} == before_files
    finally:
        game._teardown()


def test_complete_saved_phase_reading_and_native_equivalent_recovery(tmp_path):
    """All slot metadata remains reachable and file-identical through reflow; the real error/recovery tracer stays executable."""
    from tools.verify_eador_saves import verify
    verify(tmp_path, backend='mock')
