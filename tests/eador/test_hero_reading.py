"""The Hero view keeps equipment and resource decisions readable through public input."""
from pathlib import Path

import pytest
from saga2d import Button, Label
from eador.app import create_game
from eador.content import RELICS
from eador.model import State
from eador.scene import HeroScene, ShardScene
from eador.settings_scene import SettingsScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_equipment_reports_checkpoint_failure_without_hiding_or_overwriting_it(tmp_path):
    """An earned relic can be removed once; damaged autosaves remain intact and the error is visible immediately."""
    from eador.persistence import AUTO_SLOTS
    from tools.eador_campaign import finish_battle

    state = State.new(7, 'Wizard')
    state.explore()
    finish_battle(state)
    assert state.hero.relic == 'moonstone'
    saves = tmp_path / 'saves'
    saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('h')
        player.press('u')
        assert state.hero.relic is None
        assert any('All autosave slots are damaged' in label.text
                   for label in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        check_reading_layout(game.scene)
        after = state.to_json()
        player.press('u')
        assert state.to_json() == after
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
    finally:
        game._teardown()


def test_hero_reading_preserves_visible_relic_and_saved_equipment_through_reflow(tmp_path):
    """A recorded collection reflows around its current relic; its visible key equips exactly that item."""
    state = State.from_json((Path(__file__).parent / 'fixtures/v11_relic_collection.json').read_text())
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        root = ShardScene(state)
        game.push(root)
        game.push(HeroScene(root))
        player = PlayerInput(game)
        player.press('right')
        player.press('t')
        assert isinstance(game.scene, SettingsScene)
        player.press('right')
        player.press('escape')
        assert not (tmp_path / 'settings.json').exists()
        anchor = game.scene.visible_relics[0]
        for key in ('t', 'right', 'return'):
            player.press(key)
        assert isinstance(game.scene, HeroScene) and game.scene.visible_relics[0] == anchor
        assert state.to_json() == before
        check_reading_layout(game.scene)
        labels = game.scene.ui.find_all(lambda item: isinstance(item, Label))
        assert any(label.text == RELICS[anchor].description for label in labels)
        assert any(record['font_size'] == 15 and record['text']
                   and RELICS[anchor].description.startswith(record['text']) for record in game.backend.texts)
        player.press('1')
        assert state.hero.relic == anchor
        after = state.to_json()
        saves = {path.name: path.read_bytes() for path in (tmp_path / 'saves').iterdir()}
        player.press('1')
        assert state.to_json() == after
        assert {path.name: path.read_bytes() for path in (tmp_path / 'saves').iterdir()} == saves
    finally:
        game._teardown()

    restarted = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        from eador.preferences import reading_scale
        assert reading_scale(restarted) == 125
        root = ShardScene(State.from_json(after))
        restarted.push(root)
        restarted.push(HeroScene(root))
        restarted.tick(1 / 60)
        check_reading_layout(restarted.scene)
        description = RELICS[restarted.scene.visible_relics[0]].description
        assert any(record['font_size'] == 15 and record['text']
                   and description.startswith(record['text']) for record in restarted.backend.texts)
    finally:
        restarted._teardown()


@pytest.mark.parametrize('method', ['keyboard', 'mouse'])
def test_paid_tower_infusion_uses_the_visible_quote_once_and_saves_the_result(tmp_path, method):
    """Purchase the Tower and win its mana deficit; a Hero command spends crystals/action, not a turn."""
    from eador.scene import TitleScene
    from tools.eador_campaign import finish_battle

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(TitleScene(7, hero_class='Wizard'))
        player.press('return')
        player.state.build('mage_tower')
        player.state.explore()
        finish_battle(player.state)
        state = player.root.state
        before = state.to_json()
        quote = state.infusion_preview()
        assert quote.blocked_reason is None and quote.mana > 0
        expected = State.from_json(before)
        expected.infuse()
        player.press('h')
        player.press('i') if method == 'keyboard' else player.button('Infuse mana')
        assert state.to_json() == expected.to_json()
        check_reading_layout(game.scene)
        files = {path.name: path.read_bytes() for path in (tmp_path / 'saves').iterdir()}
        disabled = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Infuse mana')
        assert disabled is not None and not disabled.enabled
        x, y, width, height = disabled.bounds
        player.click(x + width / 2, y + height / 2)
        player.press('i')
        assert state.to_json() == expected.to_json()
        assert {path.name: path.read_bytes() for path in (tmp_path / 'saves').iterdir()} == files
        player.press('escape')
        player.reload(expected.to_json())
    finally:
        game._teardown()


def test_earned_hero_collections_keep_all_relics_readable_at_each_size(tmp_path):
    """Actual earned skills/relics, an old collection and an empty hero remain complete through reflow."""
    from tools.verify_eador_hero import hero_pages, prepared_heroes

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        for _, snapshot in prepared_heroes():
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for percent in (100, 125):
                    state = State.from_json(snapshot)
                    root = ShardScene(state)
                    game.clear_and_push(root)
                    game.push(HeroScene(root))
                    for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                        player.press(key)
                    hero_pages(player)
                    assert state.to_json() == snapshot
    finally:
        game._teardown()
