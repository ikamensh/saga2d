"""The scoped reading preference changes actual Codex text through the shipped UI."""
import pytest

from saga2d import Button, Settings
from eador.app import create_game
from eador.codex import CodexScene
from eador.model import State
from eador.preferences import DEFAULTS
from eador.scene import ShardScene
from eador.settings_scene import SettingsScene
from tools.eador_ui import PlayerInput


def reading_fonts(game):
    return {record['font_size'] for record in game.backend.texts if 'Recruit for' in record['text']}


def test_codex_reading_preview_cancel_apply_and_restart_keep_progress_and_reading_position(tmp_path):
    """Larger reference text is real, reversible, and independent of campaign saves."""
    state = State.new(7)
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        root = ShardScene(state)
        game.push(root)
        game.push(CodexScene(root))
        player = PlayerInput(game)
        game.tick(1 / 60)
        assert reading_fonts(game) == {13}
        player.button('Text size')
        assert isinstance(game.scene, SettingsScene)
        player.press('right')
        assert game.scene.draft['codex_text_scale'] == 125
        player.press('escape')
        assert isinstance(game.scene, CodexScene) and reading_fonts(game) == {13}
        assert not (tmp_path / 'settings.json').exists()
        player.button('Next')
        anchor = game.scene.visible_entries[0].title
        player.button('Text size')
        player.press('right')
        player.button('Apply')
        assert isinstance(game.scene, CodexScene)
        assert game.scene.visible_entries[0].title == anchor
        player.press('home')
        assert reading_fonts(game) == {16}
        assert Settings(tmp_path / 'settings.json', DEFAULTS)['codex_text_scale'] == 125
        assert root.state.to_json() == before
    finally:
        game._teardown()
    restarted = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        root = ShardScene(State.from_json(before))
        restarted.push(root)
        restarted.push(CodexScene(root))
        restarted.tick(1 / 60)
        assert reading_fonts(restarted) == {16}
        assert root.state.to_json() == before
    finally:
        restarted._teardown()


def test_reading_mouse_controls_match_keyboard_and_failed_apply_keeps_edits_open(tmp_path):
    """The visible reading +/- row and keys share preview; a disk error cannot commit it."""
    from eador.preferences import codex_text_scale, load_preferences

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        prefs = load_preferences(game)
        prefs.save()
        before = prefs.path.read_bytes()
        prefs.path.with_suffix('.backup.json').mkdir()
        root = ShardScene(State.new(7))
        game.push(root)
        game.push(CodexScene(root))
        player = PlayerInput(game)
        game.tick(1 / 60)
        player.press('right')
        anchor = game.scene.visible_entries[0].title
        player.press('t')
        # The bottom +/- pair is the visible reading-size row, below window size.
        def reading_button(label):
            controls = game.scene.ui.find_all(lambda item: isinstance(item, Button) and item.text == label)
            button = max(controls, key=lambda item: item.bounds[1])
            x, y, width, height = button.bounds
            player.click(x + width / 2, y + height / 2)
        reading_button('+')
        assert codex_text_scale(game) == 125
        player.press('left')
        assert codex_text_scale(game) == 100
        player.press('right')
        reading_button('−')
        assert codex_text_scale(game) == 100
        reading_button('+')
        player.button('Apply')
        assert isinstance(game.scene, SettingsScene)
        assert 'Could not apply' in game.scene.message
        assert codex_text_scale(game) == 125 and prefs['codex_text_scale'] == 100
        assert prefs.path.read_bytes() == before
        player.button('Cancel')
        assert game.scene.visible_entries[0].title == anchor
        assert codex_text_scale(game) == 100
        assert prefs.path.read_bytes() == before
    finally:
        game._teardown()


def test_reading_corruption_recovery_is_explicit_and_preserves_displaced_bytes(tmp_path):
    """A damaged file must not be overwritten by ordinary Apply of the reading size."""
    from eador.preferences import codex_text_scale

    path = tmp_path / 'settings.json'
    damaged = b'{"codex_text_scale": 125.0}'
    path.write_bytes(damaged)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new(7)))
        game.push(CodexScene(game.scene))
        player = PlayerInput(game)
        game.tick(1 / 60)
        player.button('Text size')
        player.press('right')
        player.button('Apply')
        assert isinstance(game.scene, SettingsScene)
        assert path.read_bytes() == damaged
        player.button('Preserve damaged file & use defaults')
        assert codex_text_scale(game) == 100
        player.button('Cancel')
        assert path.read_bytes() == damaged
        assert not list(tmp_path.glob('settings.recovery-*.json'))
        player.button('Text size')
        player.button('Preserve damaged file & use defaults')
        player.press('right')
        player.button('Apply')
        assert isinstance(game.scene, CodexScene) and reading_fonts(game) == {16}
        assert [item.read_bytes() for item in tmp_path.glob('settings.recovery-*.json')] == [damaged]
    finally:
        game._teardown()


def test_old_preferences_gain_default_reading_size_without_rewriting_on_load(tmp_path):
    from eador.preferences import codex_text_scale, load_preferences

    path = tmp_path / 'settings.json'
    old = b'{"master": 0.6, "reduced_motion": true}'
    path.write_bytes(old)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        assert codex_text_scale(game) == 100
        assert not load_preferences(game).error
        assert game.audio.get_volume('master') == .6
        assert path.read_bytes() == old
    finally:
        game._teardown()


def test_both_reading_sizes_preserve_all_current_and_older_entries_after_resize(tmp_path):
    """Every rule remains reachable and bounded; neither preview nor resize changes a save."""
    from pathlib import Path
    from eador.codex import CATEGORIES
    from tools.verify_eador_reading import check_page

    snapshots = [State.new(7).to_json(), (Path(__file__).parent / 'fixtures/v10_pinned_crossing.json').read_text()]
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        for snapshot in snapshots:
            state = State.from_json(snapshot)
            before = state.to_json()
            root = ShardScene(state)
            game.clear_and_push(root)
            game.push(CodexScene(root))
            game.tick(1 / 60)
            for percent in (100, 125):
                player.button('Text size')
                player.press('right' if percent == 125 else 'left')
                player.button('Apply')
                for index in range(len(CATEGORIES)):
                    player.press(str(index + 1))
                    expected = list(game.scene.entries)
                    seen = []
                    for page in range(game.scene.pages):
                        check_page(game.scene)
                        seen.extend(game.scene.visible_entries)
                        if page + 1 < game.scene.pages:
                            player.press('right')
                    assert seen == expected
                    anchor = game.scene.visible_entries[0]
                    game.backend.inject_resize(1280, 720 if percent == 125 else 800)
                    game.tick(1 / 60)
                    assert game.scene.visible_entries[0] == anchor
                    check_page(game.scene)
                assert root.state.to_json() == before
        assert not list((tmp_path / 'saves').glob('*'))
    finally:
        game._teardown()


@pytest.mark.parametrize('value', ['true', '125.0', '126', '0', 'NaN', '"125"', 'null'])
def test_invalid_reading_preference_is_reported_without_rewriting_file(tmp_path, value):
    from eador.preferences import codex_text_scale, load_preferences

    path = tmp_path / 'settings.json'
    raw = '{"codex_text_scale": ' + value + '}'
    path.write_text(raw)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        assert load_preferences(game).error
        assert codex_text_scale(game) == 100
        assert path.read_text() == raw
    finally:
        game._teardown()
