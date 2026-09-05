"""Public input makes rival counterplay observable without consuming a turn."""

from saga2d import Game
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
    game = Game("Rival inspection", backend="mock", save_dir=tmp_path)
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
