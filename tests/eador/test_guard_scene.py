"""Players can recruit, order and restore defensive stances through actual UI input."""

from saga2d import Button

from eador.app import create_game
from eador.scene import BattleScene, TitleScene


def press(game, key):
    game.backend.inject_key(key)
    game.backend.inject_key(key, type="key_release")
    game.tick(1 / 60)


def click_button(game, label):
    control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
    assert control is not None and control.enabled
    x, y, width, height = control.bounds
    game.backend.inject_click(round(x + width / 2), round(y + height / 2))
    game.backend.inject_release(round(x + width / 2), round(y + height / 2))
    game.tick(1 / 60)


def test_guard_and_recruited_pikeman_brace_use_visible_controls_and_restore_exactly(tmp_path):
    """Keyboard Guard and mouse Brace spend the correct order, expire next turn and survive a save."""
    game = create_game("Defensive orders", backend="mock", save_dir=tmp_path)
    try:
        game.push(TitleScene(seed=7))
        for key in ("return", "b", "1", "escape", "r", "5", "escape"):
            press(game, key)
        root = game.scene
        assert root.state.hero.army[-1].kind == "pikeman"
        press(game, "tab")
        press(game, "return")
        assert isinstance(game.scene, BattleScene)
        press(game, "g")
        assert root.state.battle.unit(0).stance == "guard"
        assert root.state.battle.unit(0).acted
        press(game, "f5")
        saved = root.state.to_json()
        press(game, "e")
        assert root.state.battle.unit(0).stance is None
        press(game, "f9")
        root = game.scene.root
        assert root.state.to_json() == saved
        for _ in range(6):
            if root.state.battle.unit(game.scene.selected).kind == "pikeman":
                break
            press(game, "tab")
        assert root.state.battle.unit(game.scene.selected).kind == "pikeman"
        click_button(game, "Brace")
        assert root.state.battle.unit(game.scene.selected).stance == "brace"
        assert "Braced" in " ".join(record["text"] for record in game.backend.texts)
        saved = root.state.to_json()
        press(game, "g")
        assert root.state.to_json() == saved, "The disabled defensive order must consume its shortcut harmlessly."
        press(game, "f5")
        press(game, "e")
        assert all(unit.stance is None for unit in root.state.battle.units if unit.team == "player")
        press(game, "f9")
        assert game.scene.root.state.to_json() == saved
    finally:
        game._teardown()
