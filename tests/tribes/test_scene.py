"""Playing Tribes through the scene with keyboard and mouse (mock backend)."""

import pytest

from saga2d import Game
from tribes.__main__ import build_theme
from tribes.scene import GameOverScene, MapScene, PauseScene, TechScene, new_game
from tribes.textures import TILE


@pytest.fixture
def play(tmp_path):
    game = Game("Tribes Test", backend="mock", resolution=(1280, 800), theme=build_theme(), save_dir=tmp_path)
    scene = new_game(seed=3)
    game.push(scene)
    game.tick(1 / 60)
    yield game, scene
    game._teardown()


def press(game: Game, key: str, **mods) -> None:
    game.backend.inject_key(key, **mods)
    game.tick(1 / 60)


def click_tile(game: Game, scene: MapScene, pos: tuple[int, int]) -> None:
    sx, sy = scene.camera.world_to_screen(pos[0] * TILE + TILE / 2, pos[1] * TILE + TILE / 2)
    game.backend.inject_click(int(sx), int(sy))
    game.tick(1 / 60)


def test_tab_selects_the_starting_warrior_and_shows_its_moves(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    assert unit is not None and unit.tribe == scene.human
    assert scene.reachable and scene.cursor == unit.pos
    texts = [t["text"] for t in game.backend.texts]
    assert any("Warrior" in t for t in texts)


def test_clicking_a_reachable_tile_moves_the_unit(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    dest = next(iter(scene.reachable))
    click_tile(game, scene, dest)
    assert unit.pos == dest and unit.moved


def test_arrow_keys_and_enter_drive_the_cursor_without_a_mouse(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    start = unit.pos
    dest = next(p for p in scene.reachable if p[0] == start[0] + 1 and p[1] == start[1])
    press(game, "right")
    assert scene.cursor == dest
    press(game, "return")
    assert unit.pos == dest


def test_end_turn_runs_the_ai_and_returns_to_the_player(play) -> None:
    game, scene = play
    round_before = scene.world.round
    press(game, "e")
    assert scene.world.round == round_before + 1
    assert scene.world.current == scene.human
    assert all(u.can_act for u in scene.world.tribe_units(scene.human))


def test_tech_overlay_buys_a_tech_with_a_number_key(play) -> None:
    game, scene = play
    scene.tribe.stars = 20
    press(game, "t")
    assert isinstance(game.scene, TechScene)
    press(game, "1")
    assert isinstance(game.scene, MapScene)
    assert len(scene.tribe.techs) == 1


def test_city_selection_trains_a_unit_with_a_number_key(play) -> None:
    game, scene = play
    world = scene.world
    capital = world.capital_of(scene.human)
    warrior = world.unit_at(capital.pos)
    press(game, "tab")
    dest = next(iter(scene.reachable))
    click_tile(game, scene, dest)
    click_tile(game, scene, capital.pos)
    assert scene.selected_city == capital.id and scene.train_panel.visible
    stars = scene.tribe.stars
    press(game, "1")
    assert world.unit_at(capital.pos) is not None and world.unit_at(capital.pos) is not warrior
    assert scene.tribe.stars == stars - 2


def test_escape_opens_the_pause_menu_and_save_load_round_trips(play) -> None:
    game, scene = play
    press(game, "escape")
    assert isinstance(game.scene, PauseScene)
    press(game, "escape")
    assert game.scene is scene
    press(game, "f5")
    scene.tribe.stars = 999
    press(game, "f9")
    assert scene.tribe.stars != 999
    assert scene.world.capital_of(scene.human) is not None


def test_help_overlay_opens_and_closes(play) -> None:
    game, scene = play
    press(game, "f1")
    assert game.scene is not scene
    press(game, "escape")
    assert game.scene is scene


def test_game_over_overlay_appears_when_the_player_wins(play) -> None:
    game, scene = play
    world = scene.world
    for tribe in world.tribes:
        if tribe.id != scene.human:
            for city in world.tribe_cities(tribe.id):
                city.tribe = scene.human
    world._check_elimination()
    scene._check_game_over()
    game.tick(1 / 60)
    assert isinstance(game.scene, GameOverScene)
    texts = [t["text"] for t in game.backend.texts]
    assert any("Victory" in t for t in texts)
