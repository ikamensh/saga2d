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
    battle_ability: str | None = None


RELICS = {
    'wayfarer_boots': RelicSpec('Wayfarer Boots', 'Your hero ignores forest and marsh movement costs.', 35),
    'oak_standard': RelicSpec('Oak Standard', 'The army recovers 3 extra health each resting turn.', 40),
    'ember_lens': RelicSpec('Ember Lens', 'Learn Arcane Bolt while equipped; it deals 6 extra damage.', 45),
    'moonstone': RelicSpec('Moonstone', 'Learn Heal while equipped; it restores 6 extra health.', 45),
    'iron_crown': RelicSpec('Iron Crown', 'Your first hero attack each battle avoids retaliation.', 40),
    'merchant_seal': RelicSpec('Merchant Seal', 'Recruitment costs 25% less while equipped.', 50),
    'watch_bell': RelicSpec('Watch Bell', 'Your hero can Brace: the first adjacent melee attacker takes a pre-emptive hit. Ranged attacks counter it.', 45, 'brace'),
    'storm_quiver': RelicSpec('Storm Quiver', 'Your hero can Pin within 3 hexes: half damage and -2 movement for the target’s next turn; skip one turn before reuse.', 45, 'pin'),
    'veil_censer': RelicSpec('Veil Censer', 'Your hero gains one Smoke charge each battle. Spend its order to screen a visible hex within 3; both teams’ ranged shots and spells are blocked until your next turn.', 45, 'smoke'),
    'porter_rune': RelicSpec('Porter’s Rune', 'Your hero gains one Repulse charge each battle. Spend its order to push an adjacent unanchored enemy into an empty hex; Guard and Brace resist it.', 45, 'repulse'),
    'mirror_badge': RelicSpec('Mirror Badge', 'Your hero can Swap with an adjacent ally: spend your order and both moves, preserving the ally’s unspent action. You take the exposed position.', 45, 'swap'),
    'vanguard_drum': RelicSpec('Vanguard Drum', 'Your hero can Rally an adjacent pinned ally. Spend your order to clear Pin, without restoring movement or an action already spent.', 45, 'rally'),
}


@dataclass(frozen=True)
class AdventureApproach:
    id: str
    title: str
    description: str
    encounter: str
    gold_cost: int = 0
    crystals_cost: int = 0
    cargo_penalty: int = 0
    bonus_gold: int = 0


@dataclass(frozen=True)
class SiteSpec:
    name: str
    description: str
    guards: tuple[str, ...]
    gold: int
    crystals: int
    relic: str | None
    encounter: str | None = None
    approaches: tuple[AdventureApproach, ...] = ()


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
    'courier_crossing': SiteSpec('Courier’s Crossing', 'Carry recovered dispatches to either exit by round 8, or rout the roadblock.',
        ('pikeman', 'archer', 'brigand'), 50, 2, 'veil_censer', 'courier_direct', (
            AdventureApproach('direct', 'Take the open road', 'Free. Cross the exposed western approach; keep the full reward.', 'courier_direct'),
            AdventureApproach('guided', 'Hire a guide', 'Pay 20 gold for covered southern deployment. The fee is lost if you retreat.', 'courier_guided', gold_cost=20),
        )),
    'supply_cache': SiteSpec('Supply Cache', 'Break out of the surrounding pack with recovered supplies by round 8, or rout the guardians.',
        ('wolf', 'wolf', 'wolf', 'goblin'), 40, 2, 'porter_rune', 'supply_cache', (
            AdventureApproach('light', 'Travel light', 'Carry the normal supplies at full movement speed.', 'supply_cache'),
            AdventureApproach('full', 'Carry the full cache', 'Gain 40 extra gold on success; your hero has 1 less movement this battle, minimum 1.',
                              'supply_cache', cargo_penalty=1, bonus_gold=40),
        )),
    'sealed_vault': SiteSpec('Sealed Vault', 'Extract the regalia through the eastern crossfire by round 8, or rout its watchful guards.',
        ('warden', 'archer', 'archer', 'guard'), 60, 1, 'mirror_badge', 'vault_crossfire', (
            AdventureApproach('crossfire', 'Face the crossfire', 'Keep your crystals. Only the guarded eastern exit is open.', 'vault_crossfire'),
            AdventureApproach('unseal', 'Unseal the floodgate', 'Spend 2 crystals to open a second, southern exit. The cost is lost on retreat.',
                              'vault_unsealed', crystals_cost=2),
        )),
    'muster_yard': SiteSpec('Muster Yard', 'An outlaw bowman and two deserters hold a drum that steadies wavering troops.',
        ('archer', 'brigand', 'brigand'), 50, 1, 'vanguard_drum'),
    'pack_hunt': SiteSpec('Pack Hunt', 'Rout the wolves closing from both sides of the wooded divide.',
        ('wolf',) * 6, 55, 1, 'storm_quiver', 'hunt_compact', (
            AdventureApproach('compact', 'Stand together', 'Free. Keep the compact central formation against pressure from both flanks.', 'hunt_compact'),
            AdventureApproach('lure', 'Lure the pack north', 'Pay 20 gold to deploy north of the forest divider. The same pack remains; the fee is lost on retreat.',
                              'hunt_lured', gold_cost=20),
        )),
    'broken_observatory': SiteSpec('Broken Observatory', 'Secure the hill seal for two uncontested enemy turns by round 8, or rout the separated marksmen.',
        ('guard', 'archer', 'archer', 'archer'), 55, 3, 'ember_lens', 'observatory_covered', (
            AdventureApproach('covered', 'Use the covered approach', 'Free. Forest divides the firing lanes and slows movement through the central approach.', 'observatory_covered'),
            AdventureApproach('clear', 'Clear the central lane', 'Spend 2 crystals to clear the central forest. Both armies gain the open firing lane; the cost is lost on retreat.',
                              'observatory_clear', crystals_cost=2),
        )),
    'smuggler_screen': SiteSpec('Smuggler Screen', 'Rout the smugglers. Their Sapper screens firing lanes once per battle; their Warden can rescue a wounded ally.',
        ('sapper', 'archer', 'archer', 'warden', 'guard'), 60, 2, 'veil_censer', 'screen_western', (
            AdventureApproach('western', 'Form the western column', 'Free. Assemble west of the forest. The southern Guard can press a screened front line.', 'screen_western'),
            AdventureApproach('northern', 'Assemble to the north', 'Free. Challenge the northern bowmen earlier, with less distance between your support and their crossfire.', 'screen_northern'),
        )),
    'aerie_raid': SiteSpec('Aerie Raid', 'Rout the airborne raiders. Their Skyriders cross marsh and occupied ground, but must land before striking.',
        ('skyrider', 'skyrider', 'archer', 'pikeman'), 60, 2, 'watch_bell', 'aerie_western', (
            AdventureApproach('western', 'Form the western reserve', 'Free. Hold the dry western ground; flyers can cross the marsh to attack your rear.', 'aerie_western'),
            AdventureApproach('northern', 'Challenge the northern perch', 'Free. Assemble closer to the northern raider and the eastern firing lane.', 'aerie_northern'),
        )),
    'stranded_explorer': SiteSpec('Stranded Explorer', 'Recover a trail kit beyond the marsh, then regroup at the western exit by round 6, or rout the patrol.',
        ('pikeman', 'archer', 'guard', 'warden'), 55, 1, 'wayfarer_boots', 'explorer_north', (
            AdventureApproach('north', 'Assemble to the north', 'Free. The main force begins north of the return exit. Your hero and fifth troop, if present, start isolated east of the marsh.', 'explorer_north'),
            AdventureApproach('south', 'Assemble to the south', 'Free. The main force begins near the southern patrol. Your hero and fifth troop, if present, start isolated east of the marsh.', 'explorer_south'),
        )),
    # The generated province retains its displaced ordinary site's exact reward.
    'relief_column': SiteSpec('Relief Column', 'Hold the signal for two uncontested enemy turns by round 4, or rout the relief force. Its Militia can Rally a pinned Skyrider.',
        ('skyrider', 'militia', 'archer', 'guard'), 0, 0, None, 'relief_forward', (
            AdventureApproach('forward', 'Intercept the support', 'Free. Deploy near the signal and the approaching support. A living Militia can clear Pin before its Skyrider lands.', 'relief_forward'),
            AdventureApproach('western', 'Receive the relief column', 'Free. Assemble west of the signal. Absorb the landing, then clear contesters before the final scoring turns.', 'relief_western'),
        )),
    'runebound_causeway': SiteSpec('Runebound Causeway', 'Extract the recovered cargo through a guarded causeway by round 5, or rout the defenders. Prioritize the Rune Adept, anchor against Repulse, or block its landing.',
        ('adept', 'pikeman', 'ranger', 'guard'), 0, 0, None, 'runebound_causeway', (
            AdventureApproach('western', 'Assemble west of the causeway', 'Free. Keep the party together west of the marsh. Your cargo slows the hero by 1; clear the guarded northeastern exit.',
                              'runebound_causeway', cargo_penalty=1),
        )),

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


@dataclass(frozen=True)
class AdventureAttempt:
    """An entered approach keeps its actual reward and burden across later saves."""
    approach: str
    encounter: str
    gold: int
    crystals: int
    relic: str | None
    cargo_penalty: int = 0
