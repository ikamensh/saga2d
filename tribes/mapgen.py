"""Procedural maps: one connected landmass, scattered villages, resources."""

from __future__ import annotations

import random
from collections import deque

from tribes.model import Pos, Tile, World
from tribes.rules import Resource, Terrain, UnitType

_VILLAGE_SPACING = 3


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
        capitals = _pick_capitals(rng, villages, tribe_count)
        for i, pos in enumerate(capitals):
            city = world.found_city(i, pos, world._city_name(), capital=True)
            world.spawn_unit(i, UnitType.WARRIOR, city.pos)
        for pos in villages:
            if pos not in capitals:
                world.tile(pos).village = True
        _place_resources(rng, world, land)
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


def _pick_capitals(rng: random.Random, villages: list[Pos], tribe_count: int) -> list[Pos]:
    """Greedy farthest-point choice so tribes start far apart."""
    capitals = [rng.choice(villages)]
    while len(capitals) < tribe_count:
        capitals.append(max(villages, key=lambda v: min(World.distance(v, c) for c in capitals)))
    return capitals


def _place_resources(rng: random.Random, world: World, land: set[Pos]) -> None:
    near_village = {n for tile in world.all_tiles() if tile.village or tile.city_id is not None for n in world.neighbors(tile.pos)}
    for tile in world.all_tiles():
        if tile.village or tile.city_id is not None:
            continue
        boost = 0.35 if tile.pos in near_village else 0.0
        if tile.terrain is Terrain.FIELD and rng.random() < 0.25 + boost:
            tile.resource = Resource.CROP if rng.random() < 0.3 else Resource.FRUIT
        elif tile.terrain is Terrain.FOREST and rng.random() < 0.35 + boost:
            tile.resource = Resource.GAME
        elif tile.terrain is Terrain.MOUNTAIN and rng.random() < 0.5:
            tile.resource = Resource.METAL
        elif tile.terrain is Terrain.WATER and rng.random() < 0.25 + boost:
            if any(world.tile(n).terrain is not Terrain.WATER for n in world.neighbors(tile.pos)):
                tile.resource = Resource.FISH
