"""Playing Tribes through the scene with keyboard and mouse (mock backend)."""

import pytest

from saga2d import Game
from tribes import effects
from tribes.style import build_theme
from tribes.rules import Tech, Terrain, UnitType
from tribes.scene import HIT_TIME, START_ZOOM, GameOverScene, MapScene, PauseScene, SettingsScene, TechScene, new_game
from tribes.title import NewGameScene, TitleScene
from tribes.view import tile_center, tint


@pytest.fixture
def game(tmp_path):
    g = Game("Tribes Test", backend="mock", resolution=(1280, 800), theme=build_theme(), save_dir=tmp_path)
    yield g
    g._teardown()


@pytest.fixture
def play(game):
    scene = new_game(seed=3)
    game.push(scene)
    game.tick(1 / 60)
    return game, scene


def press(game: Game, key: str, **mods) -> None:
    game.backend.inject_key(key, **mods)
    game.tick(1 / 60)


def tick(game: Game, seconds: float) -> None:
    for _ in range(int(seconds * 60) + 1):
        game.tick(1 / 60)


def texts(game: Game) -> list[str]:
    return [t["text"] for t in game.backend.texts]


def screen_of(scene: MapScene, pos: tuple[int, int]) -> tuple[int, int]:
    sx, sy = scene.camera.world_to_screen(*tile_center(pos))
    return int(sx), int(sy)


def click_tile(game: Game, scene: MapScene, pos: tuple[int, int]) -> None:
    game.backend.inject_click(*screen_of(scene, pos))
    game.tick(1 / 60)


def hover_tile(game: Game, scene: MapScene, pos: tuple[int, int]) -> None:
    game.backend.inject_mouse_move(*screen_of(scene, pos))
    game.tick(1 / 60)


def enemy_of(scene: MapScene) -> int:
    return next(t.id for t in scene.world.tribes if t.id != scene.human)


def spawn_enemy_next_to(scene: MapScene, unit, unit_type=UnitType.WARRIOR, hp: int | None = None):
    world = scene.world
    pos = next(p for p in world.neighbors(unit.pos)
               if world.tile(p).terrain is Terrain.FIELD and world.unit_at(p) is None and world.tile(p).city_id is None)
    enemy = world.spawn_unit(enemy_of(scene), unit_type, pos)
    if hp is not None:
        enemy.hp = hp
    scene.sync()
    scene._refresh_selection()
    return enemy


# -- Existing flow -------------------------------------------------------------


def test_tab_selects_the_starting_warrior_and_shows_its_moves(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    assert unit is not None and unit.tribe == scene.human
    assert scene.reachable and scene.cursor == unit.pos
    assert any("Warrior" in t for t in texts(game))


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
    press(game, "e")  # a unit can still act: the first press only asks for confirmation
    assert scene.world.round == round_before
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


def test_save_and_load_from_the_pause_menu_round_trip(play) -> None:
    """Regression: the pause menu's pop is deferred, so saving through it used to
    store the (empty) PauseScene state and loading through it did nothing."""
    game, scene = play
    press(game, "escape")
    press(game, "f5")
    assert game.scene is scene
    assert game.save_manager.load(1)["scene_class"] == "MapScene"
    scene.tribe.stars = 999
    press(game, "escape")
    press(game, "f9")
    assert game.scene is scene
    assert scene.tribe.stars != 999


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
    shown = texts(game)
    assert any("Victory" in t for t in shown)
    assert any("round" in t and "held" in t for t in shown)
    assert any("Back to title" in t for t in shown)


# -- Title screen ----------------------------------------------------------------


def test_title_new_game_flow_with_hotkeys(game) -> None:
    game.push(TitleScene())
    game.tick(1 / 60)
    assert any("TRIBES" in t for t in texts(game))
    press(game, "n")
    assert isinstance(game.scene, NewGameScene)
    press(game, "l")
    press(game, "4")
    press(game, "return")
    scene = game.scene
    assert isinstance(scene, MapScene)
    assert scene.world.size == 18 and len(scene.world.tribes) == 4


def test_title_continue_loads_slot_one_and_is_disabled_without_a_save(game) -> None:
    game.push(TitleScene())
    game.tick(1 / 60)
    press(game, "c")
    assert isinstance(game.scene, TitleScene)
    played = new_game(seed=11)
    game.clear_and_push(played)
    game.tick(1 / 60)
    played.tribe.stars = 42
    press(game, "f5")
    game.clear_and_push(TitleScene())
    game.tick(1 / 60)
    press(game, "c")
    scene = game.scene
    assert isinstance(scene, MapScene) and scene.seed == 11 and scene.tribe.stars == 42


def test_pause_menu_returns_to_the_title(play) -> None:
    game, scene = play
    press(game, "escape")
    press(game, "t")
    assert isinstance(game.scene, TitleScene)


# -- End turn confirmation -------------------------------------------------------


def test_end_turn_confirmation_can_be_switched_off(play) -> None:
    game, scene = play
    scene.settings["confirm_end_turn"] = False
    press(game, "e")
    assert scene.world.round == 2


def test_end_turn_confirmation_names_the_waiting_units_and_resets_on_other_actions(play) -> None:
    game, scene = play
    press(game, "e")
    assert any("1 unit can still act" in t for t in texts(game))
    assert any("Confirm end turn" in t for t in texts(game))
    press(game, "tab")  # doing something else disarms the confirmation
    press(game, "e")
    assert scene.world.round == 1
    press(game, "e")
    assert scene.world.round == 2


# -- Combat effects ----------------------------------------------------------------


def test_attack_shows_damage_numbers_then_cleans_up(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    enemy = spawn_enemy_next_to(scene, unit, UnitType.DEFENDER)
    sprites_before = len(game.backend.sprites)
    click_tile(game, scene, enemy.pos)
    assert enemy.hp < enemy.max_hp
    tick(game, HIT_TIME + 0.35)
    shown = texts(game)
    assert f"-{enemy.max_hp - enemy.hp}" in shown  # defender's damage
    assert f"-{unit.max_hp - unit.hp}" in shown  # retaliation on the attacker
    assert len(scene.effects) > 0
    tick(game, 2.0)
    assert len(scene.effects) == 0
    assert not any(t.startswith("-") for t in texts(game))
    assert len(game.backend.sprites) == sprites_before
    assert "attack_hit" in scene.recent_sounds


def test_kill_leaves_a_dissolving_ghost_that_is_removed(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    enemy = spawn_enemy_next_to(scene, unit, hp=1)
    enemy_tint = tint(scene.world.tribes[enemy.tribe].color)

    def enemy_sprites() -> int:
        return sum(1 for s in game.backend.sprites.values() if s["tint"] == enemy_tint)

    assert enemy_sprites() == 1
    click_tile(game, scene, enemy.pos)
    assert enemy.id not in scene.world.units
    assert enemy_sprites() == 1  # the real sprite is gone, a ghost stands in its place
    tick(game, 1.5)
    assert enemy_sprites() == 0
    tick(game, 1.0)  # the round banner outlives the fight
    assert len(scene.effects) == 0
    assert scene.stats["units_killed"] == 1
    assert "attack_kill" in scene.recent_sounds


def test_attack_button_appears_when_hovering_an_enemy_in_range(play) -> None:
    game, scene = play
    press(game, "tab")
    unit = scene.selected
    enemy = spawn_enemy_next_to(scene, unit, UnitType.DEFENDER)
    hover_tile(game, scene, enemy.pos)
    assert scene.btn_attack.visible
    assert any(t.startswith("Attack defender") for t in texts(game))
    x, y, w, h = scene.btn_attack.bounds
    game.backend.inject_click(x + w // 2, y + h // 2)
    game.tick(1 / 60)
    assert enemy.hp < enemy.max_hp


def test_mouse_over_a_panel_does_not_move_the_cursor_or_act(play) -> None:
    game, scene = play
    cursor = scene.cursor
    x, y, w, h = scene.info_panel.bounds
    game.backend.inject_mouse_move(x + 5, y + 5)
    game.backend.inject_click(x + 5, y + 5)
    game.tick(1 / 60)
    assert scene.cursor == cursor and scene.selected is None


# -- Cities, harvest, capture ----------------------------------------------------


def test_harvest_shows_growth_and_a_level_up(play) -> None:
    game, scene = play
    world = scene.world
    scene.tribe.techs.update({Tech.ORGANIZATION, Tech.HUNTING, Tech.FISHING})
    scene.tribe.stars = 20
    game.tick(1 / 60)
    harvestable = [t.pos for t in world.all_tiles() if world.can_harvest(scene.human, t.pos) is None]
    assert len(harvestable) >= 2
    assert len(game.backend.circles) >= len(harvestable)  # pulsing markers
    click_tile(game, scene, harvestable[0])
    tick(game, 0.1)
    assert "+1 pop" in texts(game)
    click_tile(game, scene, harvestable[1])
    tick(game, 0.6)
    assert "Level 2!" in texts(game)
    assert world.capital_of(scene.human).level == 2
    assert "level_up" in scene.recent_sounds


def test_city_panel_shows_growth_bar_and_why_units_cannot_be_trained(play) -> None:
    game, scene = play
    world = scene.world
    capital = world.capital_of(scene.human)
    press(game, "tab")
    click_tile(game, scene, next(iter(scene.reachable)))
    click_tile(game, scene, capital.pos)
    assert scene.city_bar_row.visible and scene.city_bar.max_value == capital.next_level_population
    shown = texts(game)
    assert "requires Archery" in shown and "requires Chivalry" in shown


def test_capture_founds_a_city_with_effects(play) -> None:
    game, scene = play
    world = scene.world
    unit = world.unit_at(world.capital_of(scene.human).pos)
    village = next(p for p in world.neighbors(unit.pos) if world.tile(p).terrain is Terrain.FIELD and world.tile(p).city_id is None)
    unit.x, unit.y = village
    world.tile(village).village = True
    scene.sync()
    scene.select_unit(unit)
    press(game, "c")
    city = world.city_at(village)
    assert city is not None and city.tribe == scene.human
    assert city.name in texts(game)
    assert scene.stats["cities_taken"] == 1 and "capture" in scene.recent_sounds
    tick(game, 2.5)  # outlasts the round banner too
    assert len(scene.effects) == 0


# -- Turn transition ---------------------------------------------------------------


def test_turn_banner_and_away_report_after_the_ai_turns(play) -> None:
    game, scene = play
    unit = scene.world.unit_at(scene.world.capital_of(scene.human).pos)
    unit.hp = 1  # heals to 5 before the AI moves, still a sure kill: the AI only takes favourable trades
    spawn_enemy_next_to(scene, unit)
    scene.settings["confirm_end_turn"] = False
    press(game, "e")
    tick(game, 0.5)
    shown = texts(game)
    assert "Round 2" in shown
    assert "While you were away" in shown
    assert any("took" in t and "damage" in t for t in shown) or any(t.startswith("Lost") for t in shown)
    assert "turn_start" in scene.recent_sounds


# -- Settings ----------------------------------------------------------------------


def test_settings_overlay_is_fully_keyboard_driven(play) -> None:
    game, scene = play
    press(game, "escape")
    press(game, "s")
    assert isinstance(game.scene, SettingsScene)
    press(game, "return")
    assert scene.settings["confirm_end_turn"] is False
    press(game, "down")
    press(game, "right")
    assert scene.settings["music"] == pytest.approx(0.8)
    press(game, "down")
    press(game, "left")
    press(game, "left")
    assert scene.settings["sfx"] == pytest.approx(0.6)
    press(game, "escape")
    press(game, "escape")
    assert game.scene is scene
    assert "80%" not in texts(game)


def test_settings_survive_save_and_load(play) -> None:
    game, scene = play
    scene.settings["confirm_end_turn"] = False
    scene.settings["music"] = 0.3
    press(game, "f5")
    scene.settings["music"] = 0.9
    press(game, "f9")
    assert scene.settings["music"] == pytest.approx(0.3) and scene.settings["confirm_end_turn"] is False


def test_sound_events_reach_the_hook_and_respect_the_volume(play, monkeypatch) -> None:
    game, scene = play
    heard: list[str] = []
    monkeypatch.setattr(effects, "sound_hook", heard.append)
    press(game, "tab")
    assert heard == ["select"]
    scene.settings["sfx"] = 0.0
    press(game, "escape")
    press(game, "tab")
    assert heard == ["select"]


# -- Zoom ------------------------------------------------------------------------


def test_a_light_trackpad_scroll_zooms_smoothly_and_a_flick_is_bounded(play) -> None:
    game, scene = play
    camera = scene.camera
    start = camera.zoom
    under_pointer = camera.screen_to_world(500, 300)
    for _ in range(10):  # ten fractional lines, as a slow two-finger scroll delivers them
        game.backend.inject_scroll(500, 300, 0, 0.3)
        game.tick(1 / 60)
    assert camera.zoom_target == pytest.approx(start * 1.06 ** 3)
    assert start < camera.zoom < camera.zoom_target  # easing, not jumping
    tick(game, 0.5)
    assert camera.zoom == pytest.approx(camera.zoom_target)
    assert camera.screen_to_world(500, 300) == pytest.approx(under_pointer, abs=1e-6)

    before = camera.zoom_target
    game.backend.inject_scroll(500, 300, 0, 40)  # one momentum event with a huge delta
    game.tick(1 / 60)
    assert camera.zoom_target == pytest.approx(min(before * 1.06 ** 4, 2.5))


def test_plus_and_minus_keys_step_the_zoom_about_the_screen_centre(play) -> None:
    game, scene = play
    camera = scene.camera
    w, h = game.resolution
    centre = camera.screen_to_world(w / 2, h / 2)
    press(game, "equal")
    assert camera.zoom_target == pytest.approx(min(camera.zoom * 1.25, 2.5), rel=0.05)
    tick(game, 0.5)
    assert camera.screen_to_world(w / 2, h / 2) == pytest.approx(centre, abs=1e-6)
    press(game, "minus")
    press(game, "minus")
    tick(game, 0.5)
    assert camera.zoom == pytest.approx(min(START_ZOOM * 1.25, 2.5) / 1.25 ** 2)
