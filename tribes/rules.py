"""Static game data.  Nothing here mutates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Terrain(Enum):
    WATER = "water"
    FIELD = "field"
    FOREST = "forest"
    MOUNTAIN = "mountain"


class Resource(Enum):
    FRUIT = "fruit"
    CROP = "crop"
    GAME = "game"
    FISH = "fish"
    METAL = "metal"


class Tech(Enum):
    ORGANIZATION = "organization"
    FARMING = "farming"
    SHIELDS = "shields"
    CLIMBING = "climbing"
    MINING = "mining"
    FISHING = "fishing"
    HUNTING = "hunting"
    ARCHERY = "archery"
    RIDING = "riding"
    CHIVALRY = "chivalry"


@dataclass(frozen=True)
class TechInfo:
    tier: int
    requires: Tech | None
    summary: str


TECHS: dict[Tech, TechInfo] = {
    Tech.ORGANIZATION: TechInfo(1, None, "Harvest fruit (2★, +1 pop)"),
    Tech.FARMING: TechInfo(2, Tech.ORGANIZATION, "Farm crops (5★, +2 pop)"),
    Tech.SHIELDS: TechInfo(2, Tech.ORGANIZATION, "Defender unit"),
    Tech.CLIMBING: TechInfo(1, None, "Cross mountains, see far from peaks"),
    Tech.MINING: TechInfo(2, Tech.CLIMBING, "Mine metal (5★, +2 pop)"),
    Tech.FISHING: TechInfo(1, None, "Harvest fish (2★, +1 pop)"),
    Tech.HUNTING: TechInfo(1, None, "Hunt game (2★, +1 pop)"),
    Tech.ARCHERY: TechInfo(2, Tech.HUNTING, "Archer unit"),
    Tech.RIDING: TechInfo(1, None, "Rider unit"),
    Tech.CHIVALRY: TechInfo(2, Tech.RIDING, "Knight unit"),
}


def tech_cost(tech: Tech, city_count: int) -> int:
    """Techs get pricier as an empire grows, like Polytopia."""
    tier = TECHS[tech].tier
    return 4 * tier + 1 + 2 * tier * max(0, city_count - 1)


@dataclass(frozen=True)
class HarvestInfo:
    tech: Tech
    cost: int
    population: int
    label: str


HARVEST: dict[Resource, HarvestInfo] = {
    Resource.FRUIT: HarvestInfo(Tech.ORGANIZATION, 2, 1, "Harvest fruit"),
    Resource.CROP: HarvestInfo(Tech.FARMING, 5, 2, "Build farm"),
    Resource.GAME: HarvestInfo(Tech.HUNTING, 2, 1, "Hunt game"),
    Resource.FISH: HarvestInfo(Tech.FISHING, 2, 1, "Catch fish"),
    Resource.METAL: HarvestInfo(Tech.MINING, 5, 2, "Build mine"),
}


class UnitType(Enum):
    WARRIOR = "warrior"
    ARCHER = "archer"
    RIDER = "rider"
    DEFENDER = "defender"
    KNIGHT = "knight"


@dataclass(frozen=True)
class UnitInfo:
    cost: int
    hp: int
    attack: float
    defense: float
    movement: int
    range: int
    tech: Tech | None
    escape: bool = False  # may move after attacking
    persist: bool = False  # may attack again after a kill
    hotkey: str = ""


UNITS: dict[UnitType, UnitInfo] = {
    UnitType.WARRIOR: UnitInfo(2, 10, 2, 2, 1, 1, None, hotkey="1"),
    UnitType.ARCHER: UnitInfo(3, 10, 2, 1, 1, 2, Tech.ARCHERY, hotkey="2"),
    UnitType.RIDER: UnitInfo(3, 10, 2, 1, 2, 1, Tech.RIDING, escape=True, hotkey="3"),
    UnitType.DEFENDER: UnitInfo(3, 15, 1, 3, 1, 1, Tech.SHIELDS, hotkey="4"),
    UnitType.KNIGHT: UnitInfo(8, 10, 3.5, 1, 3, 1, Tech.CHIVALRY, persist=True, hotkey="5"),
}


@dataclass(frozen=True)
class TribeInfo:
    name: str
    color: tuple[int, int, int]


TRIBES: list[TribeInfo] = [
    TribeInfo("Azure", (70, 150, 255)),
    TribeInfo("Ember", (255, 110, 70)),
    TribeInfo("Moss", (110, 210, 110)),
    TribeInfo("Amber", (250, 200, 70)),
]

STARTING_STARS = 5
MAX_ROUNDS = 30
CITY_BORDER_GROWTH_LEVEL = 3  # territory radius grows 1 → 2 at this level
CITY_WALL_LEVEL = 4  # units in the city defend at ×4 from this level
CITY_DEFENSE_BONUS = 1.5
WALL_DEFENSE_BONUS = 4.0
MOUNTAIN_DEFENSE_BONUS = 1.5
HEAL_IN_TERRITORY = 4
HEAL_OUTSIDE = 2


CITY_NAMES = [
    "Ashgrove", "Brightwater", "Cinderfall", "Dunmoor", "Elderglen", "Fenwick", "Glassmere", "Hollowreach",
    "Ironvale", "Juniper", "Kestrel", "Larkspur", "Mistral", "Northwind", "Oakhaven", "Pinecrest", "Quillmoor",
    "Ravenrock", "Silverbrook", "Thornfield", "Umberly", "Violetmere", "Wyvernhold", "Yarrow", "Zephyr",
]
