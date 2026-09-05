"""Authored Shardbound adventures and build choices, independent of presentation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    hero_class: str
    max_rank: int = 3


SKILLS = {
    'quartermaster': SkillSpec('Quartermaster', 'Each rank reduces recruitment by 15% and adds 1 army recovery per turn.', 'Commander'),
    'tactician': SkillSpec('Tactician', 'Each troop makes its first attack per rank each battle without retaliation.', 'Commander'),
    'duelist': SkillSpec('Duelist', 'Your first attack per rank each battle avoids retaliation; +2 attack per rank.', 'Warrior'),
    'vigor': SkillSpec('Vigor', 'Recover 6 hero health per rank after a victory and 2 extra health per rank when resting.', 'Warrior'),
    'pathfinder': SkillSpec('Pathfinder', 'Army ignores forest and marsh movement costs; +1 hero movement per rank.', 'Scout'),
    'skirmisher': SkillSpec('Skirmisher', 'Your hero can attack before moving away; further ranks add movement.', 'Scout'),
    'channeling': SkillSpec('Channeling', 'Each rank reduces Arcane Bolt mana cost by 1, to a minimum of 1.', 'Wizard'),
    'restoration': SkillSpec('Restoration', 'Each rank reduces Heal mana cost by 1 and restores 4 extra health.', 'Wizard'),
}


@dataclass(frozen=True)
class RelicSpec:
    name: str
    description: str
    value: int


RELICS = {
    'wayfarer_boots': RelicSpec('Wayfarer Boots', 'Your hero ignores forest and marsh movement costs.', 35),
    'oak_standard': RelicSpec('Oak Standard', 'The army recovers 3 extra health each resting turn.', 40),
    'ember_lens': RelicSpec('Ember Lens', 'Learn Arcane Bolt while equipped; it deals 6 extra damage.', 45),
    'moonstone': RelicSpec('Moonstone', 'Learn Heal while equipped; it restores 6 extra health.', 45),
    'iron_crown': RelicSpec('Iron Crown', 'Your first hero attack each battle avoids retaliation.', 40),
    'merchant_seal': RelicSpec('Merchant Seal', 'Recruitment costs 25% less while equipped.', 50),
    'watch_bell': RelicSpec('Watch Bell', 'Your hero can Brace: the first adjacent melee attacker takes a pre-emptive hit. Ranged attacks counter it.', 45),
    'storm_quiver': RelicSpec('Storm Quiver', 'Your hero can Pin within 3 hexes: half damage and -2 movement for the target’s next turn; skip one turn before reuse.', 45),
}


@dataclass(frozen=True)
class SiteSpec:
    name: str
    description: str
    guards: tuple[str, ...]
    gold: int
    crystals: int
    relic: str
    encounter: str | None = None


SITES = {
    'shrine': SiteSpec('Buried Shrine', 'Outlaws hold a healing stone beneath the old altar.', ('brigand', 'goblin'), 45, 2, 'moonstone'),
    'tower': SiteSpec('Forgotten Tower', 'Goblin marksmen guard a lens of living flame.', ('goblin', 'goblin'), 40, 3, 'ember_lens'),
    'barrow': SiteSpec('Old Barrow', 'A grave robber and his hound prowl a warrior king’s tomb.', ('brigand', 'wolf'), 55, 1, 'iron_crown'),
    'den': SiteSpec('Wolf Den', 'A swift pack circles an abandoned explorer’s camp.', ('wolf', 'wolf', 'wolf'), 40, 1, 'storm_quiver'),
    'caravan': SiteSpec('Lost Caravan', 'Three raiders hold a merchant’s charter and treasury.', ('brigand', 'brigand', 'brigand'), 65, 0, 'merchant_seal'),
    'grove': SiteSpec('Elder Grove', 'An uneasy band protects a living standard among the roots.', ('goblin', 'wolf', 'brigand'), 35, 3, 'oak_standard'),
    'border_watch': SiteSpec('Border Watch', 'Secure the watched seal for two uncontested enemy turns by round 8, or rout its defenders.',
                            ('pikeman', 'archer', 'brigand'), 50, 2, 'watch_bell', 'border_watch'),
    'explorer_camp': SiteSpec('Explorer’s Camp', 'A goblin and its hound guard a pair of trail-worn boots.', ('goblin', 'wolf'), 40, 1, 'wayfarer_boots'),
}


@dataclass(frozen=True)
class ChoiceOption:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class Choice:
    title: str
    description: str
    options: tuple[ChoiceOption, ...]
    kind: str
    context: str
