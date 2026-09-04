"""The isometric map view: projection, sprite ordering and texture registration."""

import pytest

from saga2d import Game
from tribes import textures
from tribes.__main__ import build_theme
from tribes.rules import Resource, Terrain, UnitType
from tribes.scene import new_game
from tribes.view import tile_at, tile_center


@pytest.fixture
def revealed():
    """A mock-backend game with the whole map explored by the human player."""
    game = Game("Tribes View", backend="mock", resolution=(1280, 800), theme=build_theme())
    scene = new_game(seed=5)
    game.push(scene)
    game.tick(1 / 60)
    scene.world.tribes[scene.human].explored.update(t.pos for t in scene.world.all_tiles())
    scene.view.sync()
    game.tick(1 / 60)
    yield game, scene
    game._teardown()


def order_of(game: Game, sprite) -> int:
    return game.backend.sprites[sprite.sprite_id]["order"]


# -- Projection ---------------------------------------------------------------------


def test_tile_at_inverts_tile_center_for_every_tile() -> None:
    for x in range(20):
        for y in range(20):
            assert tile_at(*tile_center((x, y))) == (x, y)


def test_points_inside_the_diamond_pick_their_tile_and_points_outside_do_not() -> None:
    cx, cy = tile_center((3, 4))
    hw, hh = textures.ISO_W / 2, textures.ISO_H / 2
    assert tile_at(cx + hw * 0.45, cy) == (3, 4)
    assert tile_at(cx, cy - hh * 0.45) == (3, 4)
    assert tile_at(cx + hw * 0.6, cy + hh * 0.6) == (4, 4)  # past the lower-right edge
    assert tile_at(cx - hw * 0.6, cy + hh * 0.6) == (3, 5)  # past the lower-left edge


def test_rows_of_constant_x_plus_y_share_a_screen_height_and_nearer_rows_are_lower() -> None:
    assert tile_center((2, 5))[1] == tile_center((5, 2))[1]
    assert tile_center((3, 3))[1] > tile_center((2, 3))[1] > tile_center((2, 2))[1]
    assert tile_center((1, 0))[0] > tile_center((0, 0))[0] > tile_center((0, 1))[0]


def test_world_bounds_enclose_every_tile_centre_with_a_margin(revealed) -> None:
    _game, scene = revealed
    left, top, right, bottom = scene.view.world_bounds
    for tile in scene.world.all_tiles():
        cx, cy = tile_center(tile.pos)
        assert left + textures.TILE / 2 < cx < right - textures.TILE / 2
        assert top + textures.TILE / 2 < cy < bottom - textures.TILE / 2


# -- Draw order ---------------------------------------------------------------------


def test_nearer_rows_of_tiles_draw_after_farther_rows(revealed) -> None:
    game, scene = revealed
    view = scene.view
    for tile in scene.world.all_tiles():
        x, y = tile.pos
        order = order_of(game, view.tile_sprite(tile.pos))
        if scene.world.in_bounds((x + 1, y)):
            assert order_of(game, view.tile_sprite((x + 1, y))) > order
        if scene.world.in_bounds((x, y + 1)):
            assert order_of(game, view.tile_sprite((x, y + 1))) > order
        if scene.world.in_bounds((x + 1, y - 1)):
            assert order_of(game, view.tile_sprite((x + 1, y - 1))) == order


def test_units_draw_above_their_tile_and_below_the_next_row(revealed) -> None:
    game, scene = revealed
    view = scene.view
    for unit in scene.world.units.values():
        x, y = unit.pos
        unit_order = order_of(game, view.unit_sprite(unit.id))
        assert unit_order > order_of(game, view.tile_sprite(unit.pos))
        for other in scene.world.units.values():
            if other.x + other.y > x + y:
                assert order_of(game, view.unit_sprite(other.id)) > unit_order


def test_every_explored_tile_shows_its_terrain_and_props(revealed) -> None:
    game, scene = revealed
    world = scene.world
    images = {s["image"] for s in game.backend.sprites.values()}
    for tile in world.all_tiles():
        assert scene.view.tile_sprite(tile.pos).image == f"tile.{tile.terrain.value}"
    assert game.assets.image("prop.forest.0") in images
    assert any(t.terrain is Terrain.MOUNTAIN for t in world.all_tiles())
    assert any(game.assets.image(f"prop.mountain.{i}") in images for i in range(textures.MOUNTAIN_VARIANTS))
    resources = {t.resource for t in world.all_tiles() if t.resource is not None}
    for resource in resources:
        assert game.assets.image(f"resource.{resource.value}") in images
    assert game.assets.image("village") in images
    assert game.assets.image("city.1") in images and game.assets.image("city.1.base") in images


def test_moving_a_unit_re_sorts_it_into_its_new_row(revealed) -> None:
    game, scene = revealed
    world = scene.world
    unit = next(u for u in world.units.values() if u.tribe == scene.human)
    before = order_of(game, scene.view.unit_sprite(unit.id))
    dest = max(world.reachable(unit), key=lambda p: p[0] + p[1])
    path = world.move(unit, dest)
    scene.view.animate_move(unit, path)
    for _ in range(90):
        game.tick(1 / 60)
    after = order_of(game, scene.view.unit_sprite(unit.id))
    assert (after > before) == (dest[0] + dest[1] > path[0][0] + path[0][1])
    assert scene.view.unit_sprite(unit.id).position == scene.view._anchor(dest, textures.DROP_UNIT)


# -- Textures -----------------------------------------------------------------------


def test_textures_register_every_key_with_a_placement() -> None:
    game = Game("Textures", backend="mock")
    try:
        textures.register_all(game)
        for terrain in Terrain:
            assert game.assets.has_image(f"tile.{terrain.value}")
        assert game.assets.has_image("tile.fog")
        for key in [f"resource.{r.value}" for r in Resource] + [f"unit.{u.value}" for u in UnitType] + ["village"]:
            assert game.assets.has_image(key)
            assert textures.placements[key].size[0] > 0
        for size in range(1, textures.CITY_SIZES + 1):
            assert game.assets.has_image(f"city.{size}") and game.assets.has_image(f"city.{size}.base")
            assert textures.placements[f"city.{size}"].drop > textures.placements[f"city.{size}.base"].drop
        for key in ("glow", "glow.soft", "ring", "blank", "spark"):
            assert game.assets.has_image(key)
    finally:
        game._teardown()


def test_prop_drops_stay_within_one_row_spacing() -> None:
    drops = [p.drop for p in textures.placements.values()]
    assert max(drops) - min(drops) < textures.ISO_H / 2
    assert textures.DROP_TERRAIN < textures.DROP_RESOURCE <= textures.DROP_SITE < textures.DROP_UNIT
