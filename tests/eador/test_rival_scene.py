"""Public input makes rival counterplay observable without consuming a turn."""

from pathlib import Path

from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.verify_eador_rival_reading import check_rival


def press(game, key):
    game.backend.inject_key(key)
    game.backend.inject_key(key, type="key_release")
    game.tick(1 / 60)


def rendered_text(game):
    return " ".join(record["text"] for record in game.backend.texts)


def test_rival_orders_show_current_forces_and_locate_them_without_advancing_play(tmp_path):
    """Inspection reveals the actual next target, resources and wounded troops, then selects their province."""
    from eador.rival_scene import RivalScene

    state = State.new(7)
    for _ in range(state.rival.turns_until_action):
        state.end_turn()
    game = create_game("Rival inspection", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        before = state.to_json()
        press(game, "v")
        assert isinstance(game.scene, RivalScene)
        visible = rendered_text(game)
        assert state.provinces[state.rival.pos].name in visible
        assert state.provinces[state.rival.target].name in visible
        check_rival(game.scene)
        press(game, "e")
        assert state.to_json() == before
        press(game, "l")
        assert game.scene is root
        assert root.selected == state.rival.pos
        assert state.to_json() == before
        assert list(tmp_path.iterdir()) == []
    finally:
        game._teardown()


def test_encirclement_and_unpaid_upkeep_are_visible_before_ending_a_turn(tmp_path):
    """An earned old save exposes the blockade, breakout routes and an unpaid army's coming losses."""
    state = State.from_json((Path(__file__).parent / "fixtures/v3_fortified_capital.json").read_text())
    for _ in range(100):
        if state.upkeep_shortfall:
            break
        state.end_turn()
    assert state.encircled and state.upkeep_shortfall > 0
    game = create_game("Supply warnings", backend="mock", save_dir=tmp_path)
    try:
        root = ShardScene(state)
        game.push(root)
        game.tick(1 / 60)
        assert "WESTWATCH ENCIRCLED" in rendered_text(game)
        assert f"{state.upkeep_shortfall} gold short" in rendered_text(game)
        before = state.to_json()
        press(game, "v")
        for neighbor in state.grid.neighbors((-2, 0)):
            assert state.provinces[neighbor].name in rendered_text(game)
        assert "Marketplace" in rendered_text(game)
        assert state.to_json() == before
        press(game, "escape")
        count = len(state.hero.army)
        press(game, "e")
        assert len(state.hero.army) < count
        assert "deserted" in rendered_text(game)
    finally:
        game._teardown()


def test_rival_reading_size_cancel_apply_and_restart_preserve_saved_forces(tmp_path):
    """The actual conquered expedition reflows through Settings and remains unchanged when located."""
    from saga2d import Label
    from eador.preferences import reading_scale
    from eador.rival_scene import RivalScene
    from tools.eador_ui import PlayerInput
    from tools.verify_eador_guidance import check_reading_layout

    state = State.new(7)
    for _ in range(state.rival.turns_until_action):
        state.end_turn()
    before = state.to_json()
    saves = tmp_path / 'saves'
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('v')
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert isinstance(game.scene, RivalScene) and reading_scale(game) == 100
        assert not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return'):
            player.press(key)
        assert isinstance(game.scene, RivalScene) and reading_scale(game) == 125
        check_reading_layout(game.scene)
        texts = [label.text for label in game.scene.ui.find_all(lambda item: isinstance(item, Label))]
        assert any(state.provinces[state.rival.target].name in text for text in texts)
        check_rival(game.scene)
        player.press('e')
        assert state.to_json() == before
        player.button('Locate expedition')
        assert player.root.selected == state.rival.pos
        player.reload(before)
    finally:
        game._teardown()
    game = create_game(backend='mock', save_dir=saves)
    try:
        root = ShardScene(State.from_json(before))
        game.push(root)
        player = PlayerInput(game)
        player.press('v')
        assert reading_scale(game) == 125
        check_reading_layout(game.scene)
        player.press('l')
        assert game.scene is root and root.selected == root.state.rival.pos
        assert root.state.to_json() == before
    finally:
        game._teardown()


def test_earned_rival_operations_and_old_rules_remain_complete_at_both_reading_sizes(tmp_path):
    """Every current order, wounded survivor, paid refit and old-rule warning is read without issuing a command."""
    from tools.verify_eador_rival_reading import verify
    verify(tmp_path, backend='mock')
