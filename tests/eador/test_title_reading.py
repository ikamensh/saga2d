"""Starting a realm keeps the player's choices while reading or recovering files."""

from saga2d import Label
from eador.app import create_game
from eador.model import HERO_CLASSES
from eador.preferences import reading_scale
from eador.scene import ShardScene, TitleScene
from tools.eador_ui import PlayerInput


def test_title_reading_preserves_configuration_and_starts_the_selected_realm(tmp_path):
    """Settings Cancel/Apply preserve an unstarted run; only Enter creates it."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        title = TitleScene(17, theme='ruins', hero_class='Wizard', difficulty='challenge')
        game.push(title)
        player = PlayerInput(game)
        player.press('t'); player.press('right'); player.press('escape')
        assert game.scene is title and reading_scale(game) == 100
        player.press('t'); player.press('right'); player.press('return')
        assert game.scene is title and reading_scale(game) == 125
        assert (title.seed, title.world_theme, title.hero_class, title.difficulty) == (17, 'ruins', 'Wizard', 'challenge')
        labels = [c.text for c in title.ui.walk() if isinstance(c, Label)]
        assert HERO_CLASSES['Wizard'].description in labels
        assert not (tmp_path / 'saves').exists()
        player.press('return')
        assert isinstance(game.scene, ShardScene)
        state = player.state
        assert state.seed == 17 and state.theme == 'ruins' and state.hero.hero_class == 'Wizard'
        assert state.difficulty == 'challenge' and state.campaign is None
    finally:
        game._teardown()


def test_every_title_configuration_and_failed_load_remains_readable_through_input(tmp_path):
    """The complete public journey also checks files, backups and both launch modes."""
    from tools.verify_eador_title import verify
    verify(tmp_path / 'title', backend='mock')


def test_title_keeps_complete_directory_error_readable_with_a_long_valid_save_path(tmp_path):
    """A filesystem failure must not become a layout crash or alter the next run."""
    from tools.verify_eador_guidance import check_reading_layout
    directory = tmp_path
    while len(str(directory)) < 700:
        directory /= 'a-realm-with-a-long-storage-directory'
    directory.mkdir(parents=True)
    (directory / 'save_1.json').mkdir()
    game = create_game(backend='mock', save_dir=directory)
    try:
        title = TitleScene(17, hero_class='Wizard', theme='ruins', difficulty='challenge')
        game.push(title)
        player = PlayerInput(game)
        player.press('t'); player.press('right'); player.press('return')
        player.press('f9')
        assert game.scene is title and 'directory' in title.message
        check_reading_layout(title)
        pages = title.notice_pages
        assert len(pages) > 1 and ''.join(pages) == title.message
        for index, text in enumerate(pages):
            assert title.notice_page == index
            assert any(c.text == text for c in title.ui.walk() if isinstance(c, Label))
            check_reading_layout(title)
            player.press('pagedown')
        player.press('t'); player.press('left'); player.press('escape')
        assert title.notice_page == len(pages) - 1
        assert (title.seed, title.world_theme, title.hero_class, title.difficulty) == (17, 'ruins', 'Wizard', 'challenge')
    finally:
        game._teardown()
