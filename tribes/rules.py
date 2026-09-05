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
    CONSTRUCTION = "construction"
    SHIELDS = "shields"
    CLIMBING = "climbing"
    MINING = "mining"
    SMITHERY = "smithery"
    MEDITATION = "meditation"
    FISHING = "fishing"
    AQUACULTURE = "aquaculture"
    NAVIGATION = "navigation"
    CARTOGRAPHY = "cartography"
    HUNTING = "hunting"
    ARCHERY = "archery"
    FORESTRY = "forestry"
    MATHEMATICS = "mathematics"
    RIDING = "riding"
    CHIVALRY = "chivalry"
    ROADS = "roads"
    TRADE = "trade"


@dataclass(frozen=True)
class TechInfo:
    tier: int
    requires: Tech | None
    summary: str


#: Five branches, each a root with two children and one deeper leaf.  Roots
#: are listed in the order they sit around the research wheel, from the top.
TECHS: dict[Tech, TechInfo] = {
    Tech.ORGANIZATION: TechInfo(1, None, "Harvest fruit (2★, +1 pop)"),
    Tech.FARMING: TechInfo(2, Tech.ORGANIZATION, "Farm crops (5★, +2 pop)"),
    Tech.CONSTRUCTION: TechInfo(3, Tech.FARMING, "Every harvest costs 1★ less"),
    Tech.SHIELDS: TechInfo(2, Tech.ORGANIZATION, "Defender unit"),
    Tech.CLIMBING: TechInfo(1, None, "Cross mountains, see far from peaks"),
    Tech.MINING: TechInfo(2, Tech.CLIMBING, "Mine metal (5★, +2 pop)"),
    Tech.SMITHERY: TechInfo(3, Tech.MINING, "Swordsman unit"),
    Tech.MEDITATION: TechInfo(2, Tech.CLIMBING, "Idle units heal 2 more"),
    Tech.FISHING: TechInfo(1, None, "Catch fish (2★, +1 pop)"),
    Tech.AQUACULTURE: TechInfo(2, Tech.FISHING, "Fish give +2 pop"),
    Tech.NAVIGATION: TechInfo(2, Tech.FISHING, "Coastal cities earn +1★"),
    Tech.CARTOGRAPHY: TechInfo(3, Tech.NAVIGATION, "Reveals every coastline"),
    Tech.HUNTING: TechInfo(1, None, "Hunt game (2★, +1 pop)"),
    Tech.ARCHERY: TechInfo(2, Tech.HUNTING, "Archer unit"),
    Tech.FORESTRY: TechInfo(2, Tech.HUNTING, "Forests no longer end a move"),
    Tech.MATHEMATICS: TechInfo(3, Tech.FORESTRY, "Catapult unit"),
    Tech.RIDING: TechInfo(1, None, "Rider unit"),
    Tech.CHIVALRY: TechInfo(2, Tech.RIDING, "Knight unit"),
    Tech.ROADS: TechInfo(2, Tech.RIDING, "+1 move when starting on your land"),
    Tech.TRADE: TechInfo(3, Tech.ROADS, "Every city earns +1★"),
}
MEDITATION_HEAL = 2


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
    SWORDSMAN = "swordsman"
    CATAPULT = "catapult"


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
    UnitType.SWORDSMAN: UnitInfo(5, 15, 3, 3, 1, 1, Tech.SMITHERY, hotkey="6"),
    UnitType.CATAPULT: UnitInfo(8, 10, 4, 0, 1, 3, Tech.MATHEMATICS, hotkey="7"),
}


@dataclass(frozen=True)
class TribeInfo:
    name: str
    color: tuple[int, int, int]
    tech: Tech  # known from the start; the tribe's flavour


TRIBES: list[TribeInfo] = [
    TribeInfo("Azure", (70, 150, 255), Tech.FISHING),
    TribeInfo("Ember", (255, 110, 70), Tech.HUNTING),
    TribeInfo("Moss", (110, 210, 110), Tech.ORGANIZATION),
    TribeInfo("Amber", (250, 200, 70), Tech.CLIMBING),
]


class Reward(Enum):
    """What a city may pick when it reaches a new level."""

    WORKSHOP = "workshop"
    EXPLORER = "explorer"
    WALLS = "walls"
    RESOURCES = "resources"
    BORDER = "border"
    POPULATION = "population"
    PARK = "park"


@dataclass(frozen=True)
class RewardInfo:
    name: str
    summary: str


REWARDS: dict[Reward, RewardInfo] = {
    Reward.WORKSHOP: RewardInfo("Workshop", "+1★ income every turn"),
    Reward.EXPLORER: RewardInfo("Explorer", "Reveals the land around the city"),
    Reward.WALLS: RewardInfo("City walls", "Units in the city defend at ×4"),
    Reward.RESOURCES: RewardInfo("Resources", "+5★ now"),
    Reward.BORDER: RewardInfo("Border growth", "Territory radius +1"),
    Reward.POPULATION: RewardInfo("Population", "+3 population"),
    Reward.PARK: RewardInfo("Park", "+250 score"),
}

#: The pair of rewards offered at a level; higher levels repeat the last pair.
LEVEL_REWARDS: dict[int, tuple[Reward, Reward]] = {
    2: (Reward.WORKSHOP, Reward.EXPLORER),
    3: (Reward.WALLS, Reward.RESOURCES),
    4: (Reward.BORDER, Reward.POPULATION),
    5: (Reward.PARK, Reward.RESOURCES),
}
REWARD_STARS = 5
REWARD_POPULATION = 3
REWARD_PARK_SCORE = 250
EXPLORER_RADIUS = 4


class Discovery(Enum):
    """What a unit finds when it walks onto ruins."""

    TREASURE = "treasure"
    KNOWLEDGE = "knowledge"
    GROWTH = "growth"
    VISION = "vision"


RUIN_TREASURE = 6
RUIN_POPULATION = 2
RUIN_VISION_RADIUS = 3

STARTING_STARS = 5
MAX_ROUNDS = 30
CITY_BORDER_GROWTH_LEVEL = 3  # territory radius grows 1 → 2 at this level
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
