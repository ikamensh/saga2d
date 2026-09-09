"""The isometric map view: projection, sprite ordering and texture registration."""

import pytest
from PIL import Image

from saga2d import Game
from tribes import textures
from tribes.style import build_theme
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
        assert scene.view.tile_sprite(tile.pos).image == textures.tile_key(tile.pos, tile.terrain)
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
    cx, cy = tile_center(dest)
    assert scene.view.unit_sprite(unit.id).position == (cx, cy + textures.DROP_UNIT)


def test_fields_use_several_shades_chosen_by_position(revealed) -> None:
    game, scene = revealed
    keys = {scene.view.tile_sprite(t.pos).image for t in scene.world.all_tiles() if t.terrain is Terrain.FIELD}
    assert len(keys) == len(textures.TERRAIN_SHADES[Terrain.FIELD])
    assert all(k.startswith("tile.field.") for k in keys)


def test_capitals_fly_a_tinted_flag_and_walled_cities_show_walls(revealed) -> None:
    game, scene = revealed
    world = scene.world
    capital = world.capital_of(scene.human)
    flags = [s for s in game.backend.sprites.values() if s["image"] == game.assets.image("flag")]
    assert len(flags) == len([c for c in world.cities.values() if c.capital])
    from tribes.view import tile_center, tint

    cx, cy = tile_center(capital.pos)
    ours = [f for f in flags if abs(f["x"] + f["width"] / 2 - cx) < 1]
    assert ours and tuple(round(v, 3) for v in ours[0]["tint"]) == tuple(round(v, 3) for v in tint(world.tribes[scene.human].color))
    assert not any(s["image"] == game.assets.image("walls") for s in game.backend.sprites.values())
    capital.walls = True
    scene.view.sync()
    game.tick(1 / 60)
    assert any(s["image"] == game.assets.image("walls") for s in game.backend.sprites.values())
    capital.tribe = next(t.id for t in world.tribes if t.id != scene.human)
    capital.capital = False
    scene.view.sync()
    game.tick(1 / 60)
    assert len([s for s in game.backend.sprites.values() if s["image"] == game.assets.image("flag")]) == len(flags) - 1


def test_a_workshop_reward_puts_a_smithy_on_the_city_tile(revealed) -> None:
    game, scene = revealed
    capital = scene.world.capital_of(scene.human)

    def smithies() -> int:
        return sum(1 for s in game.backend.sprites.values() if s["image"] == game.assets.image("workshop"))

    assert smithies() == 0
    capital.workshop = True
    scene.view.sync()
    game.tick(1 / 60)
    assert smithies() == 1


# -- Textures -----------------------------------------------------------------------


def test_textures_register_every_key_with_a_placement() -> None:
    game = Game("Textures", backend="mock")
    try:
        textures.register_all(game)
        for terrain, shades in textures.TERRAIN_SHADES.items():
            for shade in range(len(shades)):
                assert game.assets.has_image(f"tile.{terrain.value}.{shade}")
        assert game.assets.has_image("flag") and game.assets.has_image("walls")
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


# -- Unit tokens ---------------------------------------------------------------------


def _rendered(key: str) -> tuple[Image.Image, textures.Placement]:
    from tribes.rules import UnitType

    unit_type = next(u for u in UnitType if f"unit.{u.value}" == key)
    return textures._prop(key, textures._unit(unit_type), textures.DROP_UNIT, 1.0), textures.placements[key]


def test_every_unit_stands_on_a_disc_that_covers_the_tile_centre() -> None:
    """The disc lies flat on the tile top: solid pixels span most of the
    token's width on the rows just below the tile-centre reference point."""
    from tribes.rules import UnitType

    for unit_type in UnitType:
        image, placement = _rendered(f"unit.{unit_type.value}")
        alpha = image.getchannel("A")
        width, height = image.size
        centre_row = height - int(placement.drop)
        disc_half_w = textures.TOKEN_RADIUS * textures.ISO_W / 2
        for row in (centre_row + 2, centre_row + 6):
            solid = [x for x in range(width) if alpha.getpixel((x, row)) == 255]
            assert solid, unit_type
            assert max(solid) - min(solid) >= 2 * disc_half_w * 0.85, (unit_type, row)


def test_tokens_cast_a_translucent_shadow_that_does_not_punch_through_the_disc() -> None:
    image, placement = _rendered("unit.warrior")
    alpha = image.getchannel("A")
    width, height = image.size
    centre_row = height - int(placement.drop)
    front = centre_row + int(textures.TOKEN_FRONT)
    translucent = [alpha.getpixel((x, front + 2)) for x in range(width)]
    assert any(0 < a < 200 for a in translucent)  # the shadow peeks out below the disc
    assert all(alpha.getpixel((width // 2, row)) == 255 for row in range(centre_row - 2, centre_row + 6))


def test_downsampling_keeps_edge_pixels_the_colour_of_the_surface() -> None:
    from sagaforge import render3d as r3

    image = r3.render(r3.box((0, 0, 0.2), (0.6, 0.6, 0.4), (255, 255, 255)), textures.PROJECTION, scale=1.0, canvas=(80, 80), origin=(40, 50))
    pixels = image.load()
    edge = [pixels[x, y] for x in range(80) for y in range(80) if 0 < pixels[x, y][3] < 255]
    assert edge
    assert all(min(r, g, b) >= 120 for r, g, b, _ in edge), "partial-coverage pixels were dragged towards black"
