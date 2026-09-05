"""Public input makes rival counterplay observable without consuming a turn."""

from pathlib import Path

from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene


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
        assert f"{state.rival.gold} gold" in visible
        for troop in state.rival.army:
            assert f"{troop.hp}/{troop.max_hp} health" in visible
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
