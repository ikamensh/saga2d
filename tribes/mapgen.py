"""Procedural maps: one connected landmass, scattered villages, resources."""

from __future__ import annotations

import random
from collections import deque
from itertools import combinations

from tribes.model import Pos, Tile, World
from tribes.rules import Resource, Terrain, UnitType

_VILLAGE_SPACING = 3
_CAPITAL_OPEN_NEIGHBOURS = 4  # walkable tiles around a capital, so nobody starts boxed in
_CAPITAL_RESOURCES = ((1, 2), (2, 4))  # (radius, at least this many resources within it)


def generate(seed: int, size: int = 14, tribe_count: int = 2, human: int | None = 0) -> World:
    rng = random.Random(seed)
    for _attempt in range(50):
        tiles = _terrain(rng, size)
        world = World(size, tiles, tribe_count, human=human)
        land = _largest_landmass(world)
        for tile in world.all_tiles():
            if tile.terrain is not Terrain.WATER and tile.pos not in land:
                tile.terrain = Terrain.WATER
        villages = _place_villages(rng, world, land, tribe_count)
        if len(villages) < tribe_count + 2:
            continue
        capitals = _pick_capitals(rng, world, villages, tribe_count)
        if capitals is None:
            continue
        for i, pos in enumerate(capitals):
            city = world.found_city(i, pos, world._city_name(), capital=True)
            world.spawn_unit(i, UnitType.WARRIOR, city.pos)
        for pos in villages:
            if pos not in capitals:
                world.tile(pos).village = True
        _place_resources(rng, world)
        _stock_capitals(rng, world)
        world._start_turn(0)
        return world
    raise RuntimeError(f"could not generate a playable map for seed {seed}")


def _terrain(rng: random.Random, size: int) -> list[list[Tile]]:
    """Smoothed value noise → water/field/forest/mountain by height band."""
    coarse = [[rng.random() for _ in range(size + 2)] for _ in range(size + 2)]
    heights = [[0.0] * size for _ in range(size)]
    for y in range(size):
        for x in range(size):
            total = sum(coarse[y + dy][x + dx] for dy in range(3) for dx in range(3))
            edge = min(x, y, size - 1 - x, size - 1 - y)
            heights[y][x] = total / 9 - (0.22 if edge == 0 else 0.1 if edge == 1 else 0.0)
    tiles: list[list[Tile]] = []
    for y in range(size):
        row: list[Tile] = []
        for x in range(size):
            h = heights[y][x]
            if h < 0.36:
                terrain = Terrain.WATER
            elif h > 0.66:
                terrain = Terrain.MOUNTAIN
            elif rng.random() < 0.32:
                terrain = Terrain.FOREST
            else:
                terrain = Terrain.FIELD
            row.append(Tile(x, y, terrain))
        tiles.append(row)
    return tiles


def _largest_landmass(world: World) -> set[Pos]:
    seen: set[Pos] = set()
    best: set[Pos] = set()
    for tile in world.all_tiles():
        if tile.terrain is Terrain.WATER or tile.pos in seen:
            continue
        region: set[Pos] = set()
        queue = deque([tile.pos])
        seen.add(tile.pos)
        while queue:
            pos = queue.popleft()
            region.add(pos)
            for n in world.neighbors(pos):
                if n not in seen and world.tile(n).terrain is not Terrain.WATER:
                    seen.add(n)
                    queue.append(n)
        if len(region) > len(best):
            best = region
    return best


def _place_villages(rng: random.Random, world: World, land: set[Pos], tribe_count: int) -> list[Pos]:
    candidates = [p for p in land if world.tile(p).terrain is Terrain.FIELD]
    rng.shuffle(candidates)
    target = max(tribe_count + 2, world.size * world.size // 22)
    villages: list[Pos] = []
    for pos in candidates:
        if all(World.distance(pos, v) >= _VILLAGE_SPACING for v in villages):
            villages.append(pos)
            if len(villages) >= target:
                break
    return villages


def _pick_capitals(rng: random.Random, world: World, villages: list[Pos], tribe_count: int) -> list[Pos] | None:
    """The set of open villages that keeps tribes farthest apart, dealt out in random order.

    Dealing them out randomly matters: growing the set greedily from a random
    first pick left tribe 0 central and pushed everyone else to the coast.
    """
    open_villages = [v for v in villages if _walkable_neighbours(world, v) >= _CAPITAL_OPEN_NEIGHBOURS]
    if len(open_villages) < tribe_count:
        return None

    def spread(combo: tuple[Pos, ...]) -> int:
        return min((World.distance(a, b) for a, b in combinations(combo, 2)), default=world.size)

    best = max(combinations(open_villages, tribe_count), key=spread)
    if spread(best) < world.size // 3 + 1:
        return None
    capitals = list(best)
    rng.shuffle(capitals)
    return capitals


def _walkable_neighbours(world: World, pos: Pos) -> int:
    return sum(1 for n in world.neighbors(pos) if world.tile(n).terrain in (Terrain.FIELD, Terrain.FOREST))


_RESOURCE_CHANCE = {Terrain.FIELD: 0.25, Terrain.FOREST: 0.35, Terrain.MOUNTAIN: 0.5, Terrain.WATER: 0.25}


def _place_resources(rng: random.Random, world: World) -> None:
    near_village = {n for tile in world.all_tiles() if tile.village or tile.city_id is not None for n in world.neighbors(tile.pos)}
    for tile in world.all_tiles():
        if tile.village or tile.city_id is not None:
            continue
        boost = 0.35 if tile.pos in near_village and tile.terrain is not Terrain.MOUNTAIN else 0.0
        if rng.random() < _RESOURCE_CHANCE[tile.terrain] + boost:
            tile.resource = _resource_for(rng, world, tile.pos)


def _stock_capitals(rng: random.Random, world: World) -> None:
    """Every capital starts with something to harvest, and more to grow into."""
    for city in world.cities.values():
        for radius, wanted in _CAPITAL_RESOURCES:
            ring = world.neighbors(city.pos, radius)
            have = sum(1 for p in ring if world.tile(p).resource is not None)
            spots = [p for p in ring if world.tile(p).resource is None and not world.tile(p).village and world.tile(p).city_id is None]
            rng.shuffle(spots)
            for pos in spots:
                if have >= wanted:
                    break
                resource = _resource_for(rng, world, pos)
                if resource is not None:
                    world.tile(pos).resource = resource
                    have += 1


def _resource_for(rng: random.Random, world: World, pos: Pos) -> Resource | None:
    """What could grow at *pos* given its terrain (fish only along the shore)."""
    terrain = world.tile(pos).terrain
    if terrain is Terrain.FIELD:
        return Resource.CROP if rng.random() < 0.3 else Resource.FRUIT
    if terrain is Terrain.FOREST:
        return Resource.GAME
    if terrain is Terrain.MOUNTAIN:
        return Resource.METAL
    if any(world.tile(n).terrain is not Terrain.WATER for n in world.neighbors(pos)):
        return Resource.FISH
    return None
