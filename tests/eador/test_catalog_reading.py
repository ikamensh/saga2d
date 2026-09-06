"""Larger purchase catalogs preserve real commands and the shared preference."""

from saga2d import Button

from eador.app import create_game
from eador.model import BUILDINGS, State
from eador.scene import CatalogScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_catalog_reading_preview_purchase_and_restart(tmp_path):
    """Settings reflows complete rows; disabled repeat purchases do not spend or checkpoint again."""
    state = State.new(7)
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('b')
        assert isinstance(game.scene, CatalogScene)
        first = game.scene.visible_items[0]
        before = state.to_json()
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert game.scene.visible_items[0] == first
        assert state.to_json() == before
        assert not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return'):
            player.press(key)
        assert game.scene.visible_items[0] == first
        assert any(row['text'] == 'Barracks' and row['font_size'] == 24 for row in game.backend.texts)
        check_reading_layout(game.scene)
        gold = state.gold
        player.button(f"{BUILDINGS['barracks'].cost} gold")
        assert 'barracks' in state.buildings and state.gold == gold - BUILDINGS['barracks'].cost
        built = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Built')
        assert built is not None and not built.enabled
        checkpoint = {path.name: path.read_bytes() for path in (tmp_path / 'saves').iterdir()}
        purchased = state.to_json()
        player.press('1')
        x, y, w, h = built.bounds
        player.click(x + w / 2, y + h / 2)
        assert state.to_json() == purchased
        assert {path.name: path.read_bytes() for path in (tmp_path / 'saves').iterdir()} == checkpoint
    finally:
        game._teardown()

    restarted = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        restarted.push(ShardScene(State.from_json(purchased)))
        player = PlayerInput(restarted)
        player.state.recruit('swordsman')
        player.press('r')
        assert any(row['text'] == 'Swordsman' and row['font_size'] == 24 for row in restarted.backend.texts)
        check_reading_layout(restarted.scene)
    finally:
        restarted._teardown()


def test_catalog_pages_keep_every_item_and_the_reading_anchor(tmp_path):
    """Reflow preserves the first visible item and all entries without spending through navigation keys."""
    from tools.verify_eador_catalog import catalog_pages

    state = State.new(7)
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        for size in ((1280, 720), (1280, 800), (1920, 1080)):
            game.set_window_size(size)
            for kind, shortcut in (('build', 'b'), ('recruit', 'r')):
                game.clear_and_push(ShardScene(state))
                player.press(shortcut)
                for percent in (100, 125):
                    for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                        player.press(key)
                    while game.scene.page:
                        player.press('left')
                    catalog_pages(player, kind)
                    anchor = game.scene.visible_items[0]
                    for key in ('t', 'right' if percent == 100 else 'left', 'return'):
                        player.press(key)
                    assert game.scene.visible_items[0] == anchor
                    check_reading_layout(game.scene)
                    for key in ('t', 'left' if percent == 100 else 'right', 'escape'):
                        player.press(key)
                    assert game.scene.visible_items[0] == anchor
                    assert state.to_json() == before
    finally:
        game._teardown()


def test_catalog_disabled_reasons_match_real_economy_without_purchasing(tmp_path):
    """A publicly filled army and spent gold show concrete blockers and disable each visible order."""
    from saga2d import Label

    state = State.new(7)
    while len(state.hero.army) < state.hero.max_army:
        state.recruit('militia')
    before = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('r')
        for key in ('t', 'right', 'return'):
            player.press(key)
        all_text = []
        while True:
            all_text.extend(item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
            check_reading_layout(game.scene)
            for index in range(len(game.scene.visible_items)):
                player.press(str(index + 1))
                assert state.to_json() == before
            if game.scene.page + 1 == game.scene.pages:
                break
            player.button('Next')
        assert any(f'Army full ({state.hero.max_army}/{state.hero.max_army}).' in text for text in all_text)
        assert any('Requires Archery Range.' in text for text in all_text)
        assert any('gold more.' in text for text in all_text)
        assert not list((tmp_path / 'saves').glob('*.json'))
    finally:
        game._teardown()


def test_catalog_keeps_a_successful_purchase_and_readable_checkpoint_error(tmp_path):
    """Damaged autosaves stay intact; a purchase succeeds once and reports its unsaved result in full."""
    from saga2d import Label
    from eador.persistence import AUTO_SLOTS

    saves = tmp_path / 'saves'
    saves.mkdir()
    for slot in AUTO_SLOTS:
        (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
    (tmp_path / 'settings.json').write_text('{"codex_text_scale": 125}')
    state = State.new(7)
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('b')
        player.press('1')
        assert 'barracks' in state.buildings
        assert state.gold == 100 - BUILDINGS['barracks'].cost
        assert any('All autosave slots are damaged' in item.text
                   for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        check_reading_layout(game.scene)
        after = state.to_json()
        player.press('1')
        assert state.to_json() == after
        assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
    finally:
        game._teardown()
