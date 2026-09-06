"""Complete file diagnostics are readable overlays, never hidden game commands."""

import pytest
from saga2d import Label, SaveError, Scene
from eador.app import create_game
from eador.preferences import reading_scale
from eador.style import RED
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_actual_file_diagnostic_reflows_and_does_not_leak_queued_input(tmp_path):
    """The complete OS error survives reading settings and paging; closing drops old queued actions."""
    from eador.diagnostics import DiagnosticScene

    class Underlay(Scene):
        controls = {'1': 'spend', 'return': 'spend', 'space': 'spend'}
        spent = 0

        def spend(self):
            self.spent += 1

    saves = tmp_path
    for index in range(8):
        saves /= f'ordinary-directory-{index}-' + 'a' * 70
    saves.mkdir(parents=True)
    occupied = saves / 'save_1.json'; occupied.mkdir()
    game = create_game(backend='mock', save_dir=saves)
    try:
        with pytest.raises(SaveError) as failure:
            game.save_manager.load(1)
        message = str(failure.value)
        below = Underlay(); game.push(below)
        game.push(DiagnosticScene(message, return_label='Return to saves'))
        player = PlayerInput(game)
        for key in ('1', 'space', 't', 'right', 'return'):
            player.press(key)
        assert isinstance(game.scene, DiagnosticScene) and reading_scale(game) == 125 and below.spent == 0
        parts = []
        for page in range(game.scene.pages):
            check_reading_layout(game.scene)
            parts.append(next(item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label))
                              if item.style.text_color == RED))
            if page + 1 < game.scene.pages:
                player.press('pagedown')
        assert ''.join(parts) == message and occupied.is_dir()
        for key in ('return', 'return', '1', 'space'):
            game.backend.inject_key(key)
        game.tick(1 / 60)
        assert game.scene is below and below.spent == 0
    finally:
        game._teardown()


def long_save_directory(base):
    directory = base
    for index in range(9):
        directory /= f'ordinary-directory-name-{index}-' + 'a' * 70
    directory.mkdir(parents=True)
    return directory


def read_diagnostic(player):
    """Read every visible page, preserving the actual filesystem diagnostic verbatim."""
    from eador.diagnostics import DiagnosticScene
    assert isinstance(player.game.scene, DiagnosticScene)
    message = player.game.scene.message
    while player.game.scene.page:
        player.press('pageup')
    parts = []
    for index in range(player.game.scene.pages):
        check_reading_layout(player.game.scene)
        parts.append(next(item.text for item in player.game.scene.ui.find_all(lambda item: isinstance(item, Label))
                          if item.style.text_color == RED))
        if index + 1 < player.game.scene.pages:
            player.press('pagedown')
    assert ''.join(parts) == message
    return message


def test_long_filesystem_error_preserves_replacement_quote_and_applied_decision(tmp_path):
    """A real long-path read failure cannot hide the exact quote or reapply an already bought replacement."""
    from tests.eador.test_replacement_scene import earned_army, review
    from eador.scene import ShardScene
    from eador.replacement_scene import ReplacementScene

    directory = long_save_directory(tmp_path)
    occupied = directory / 'save_1.json'; occupied.mkdir()
    state = earned_army()
    before = state.to_json()
    game = create_game(backend='mock', save_dir=directory)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        review(player, 1, 'warden')
        original = game.scene
        quote = original.quote
        for key in ('t', 'right', 'return', 'f5'):
            player.press(key)
        error = read_diagnostic(player)
        assert str(occupied) in error and state.to_json() == before
        for key in ('return', 'return', '1', 'space'):
            game.backend.inject_key(key)
        game.tick(1 / 60)
        assert game.scene is original and original.quote == quote and state.to_json() == before
        check_reading_layout(game.scene)
        player.button('Read error')
        assert read_diagnostic(player) == error
        player.press('escape')
        player.press('f5')
        assert read_diagnostic(player) == error
        player.press('escape')
        player.button('Replace veteran')
        assert isinstance(game.scene, ReplacementScene) and game.scene.applied
        after = state.to_json()
        player.press('f5')
        assert read_diagnostic(player) == error
        for key in ('return', 'return', '1', 'space'):
            game.backend.inject_key(key)
        game.tick(1 / 60)
        assert game.scene is original and original.applied and original.quote == quote
        assert state.to_json() == after and occupied.is_dir()
        check_reading_layout(game.scene)
        player.press('f6')
        assert game.scene.mode == 'save'
        player.press('2')
        assert game.scene.saves.load(2).to_json() == after
    finally:
        game._teardown()


def test_long_save_error_returns_to_same_slot_and_explicit_backup_preserves_files(tmp_path):
    """Reading a failed load never changes the current chronicle or prevents choosing its preserved backup."""
    from saga2d import SaveManager
    from eador.diagnostics import DiagnosticScene
    from eador.model import State
    from eador.persistence import CampaignSaves
    from eador.scene import ShardScene
    from tools.verify_eador_saves import select_slot

    directory = long_save_directory(tmp_path)
    saves = CampaignSaves(SaveManager(directory))
    state = State.new_campaign(7)
    backup = state.to_json()
    saves.save(state, 3)
    state.end_turn(); saves.save(state, 3)
    before = state.to_json()
    occupied = directory / 'save_3.json'; occupied.unlink(); occupied.mkdir()
    files = {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}
    game = create_game(backend='mock', save_dir=directory)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        for key in ('f6', 't', 'right', 'return'):
            player.press(key)
        browser = game.scene
        select_slot(player, 3)
        if isinstance(game.scene, DiagnosticScene):
            assert str(occupied) in read_diagnostic(player)
            player.press('escape')
        else:
            assert browser.message in [item.text for item in browser.ui.find_all(lambda item: isinstance(item, Label))]
        assert game.scene is browser and state.to_json() == before
        assert any(entry.slot == 3 for entry in browser.visible_entries)
        check_reading_layout(browser)
        select_slot(player, 3, backup=True)
        assert player.state.to_json() == backup and occupied.is_dir()
        assert {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()} == files
    finally:
        game._teardown()


def test_save_and_replacement_long_diagnostic_public_journeys(tmp_path):
    """The native-equivalent tracer keeps every veteran reachable and reloads both the backup and applied purchase."""
    from tools.verify_eador_diagnostics import verify
    verify(tmp_path, backend="mock")
