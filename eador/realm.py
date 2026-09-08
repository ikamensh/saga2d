"""One realm's resources, army and choices; spatial purchases receive their real province."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from eador.content import AdventureAttempt, Choice, ChoiceOption, RELICS, SKILLS
from eador.difficulty import RULESETS, DifficultySpec
from eador.entities import (BUILDINGS, RECRUITABLE, UNITS, Hero, InfusionPreview, Pos,
                            Province, ReplacementPreview, RuleError, Troop, TroopSnapshot)

if TYPE_CHECKING:
    from eador.battle import Battle


@dataclass(kw_only=True)
class Realm:
    hero: Hero
    gold: int = 100
    crystals: int = 4
    buildings: set[str] = field(default_factory=set)
    actions_left: int = 2
    status: str = 'playing'
    log: list[str] = field(default_factory=list)
    battle: Battle | None = None
    battle_province: Pos | None = None
    battle_kind: str | None = None
    next_troop_id: int = 4
    inventory: list[str] = field(default_factory=list)
    _choices: list[Choice] = field(default_factory=list, repr=False)
    battle_adventure: AdventureAttempt | None = None
    rules_id: str = 'standard-1'

    @property
    def rules(self) -> DifficultySpec:
        return RULESETS[self.rules_id]

    @property
    def difficulty(self) -> str:
        return self.rules_id.rsplit('-', 1)[0]

    @property
    def upkeep(self) -> int:
        return sum(UNITS[t.kind].upkeep for t in self.hero.army)

    @property
    def spells(self) -> set[str]:
        spells = {'bolt', 'heal'} if self.hero.hero_class == 'Wizard' else set()
        if 'temple' in self.buildings:
            spells.add('heal')
        if 'mage_tower' in self.buildings or self.hero.relic == 'ember_lens':
            spells.add('bolt')
        if self.hero.relic == 'moonstone':
            spells.add('heal')
        return spells

    @property
    def choice(self) -> Choice | None:
        return self._choices[0] if self._choices else None

    def recruit_cost(self, kind: str) -> int:
        if kind not in RECRUITABLE:
            raise RuleError('That unit cannot be recruited.')
        discount = 15 * self.hero.skill_ranks.get('quartermaster', 0)
        if self.hero.relic == 'merchant_seal':
            discount += 25
        return max(1, (UNITS[kind].cost * (100 - discount) + 99) // 100)

    def _skill_choice(self) -> Choice | None:
        options = tuple(ChoiceOption(key, f'{spec.name} {self.hero.skill_ranks.get(key, 0) + 1}', spec.description)
                        for key, spec in SKILLS.items() if spec.hero_class == self.hero.hero_class
                        and self.hero.skill_ranks.get(key, 0) < spec.max_rank)
        if not options:
            return None
        return Choice('Shape your hero', 'Master your current path or learn a different discipline.', options, 'skill', self.hero.hero_class)

    def _relic_choice(self, relic: str) -> Choice:
        spec = RELICS[relic]
        first = (ChoiceOption('distill', 'Distill the duplicate', 'Gain 4 crystals instead of another copy.')
                 if relic in self.inventory else ChoiceOption('take', f'Keep {spec.name}', spec.description))
        return Choice(f'Discovered {spec.name}', 'Keep its power or fund your realm. Only one relic can be equipped.',
                      (first, ChoiceOption('sell', f'Sell for {spec.value} gold', 'Trade the relic for immediate resources.')),
                      'relic', relic)

    def choose(self, option_id: str) -> None:
        choice = self.choice
        if choice is None:
            raise RuleError('There is no pending choice.')
        if option_id not in {option.id for option in choice.options}:
            raise RuleError('Choose one of the offered options.')
        if choice.kind == 'skill':
            self.hero.skill_ranks[option_id] = self.hero.skill_ranks.get(option_id, 0) + 1
            self.log.append(f'Learned {SKILLS[option_id].name} {self.hero.skill_ranks[option_id]}.')
        elif option_id == 'take':
            self.inventory.append(choice.context)
            self.log.append(f'Kept {RELICS[choice.context].name}. Equip it in the hero panel.')
        elif option_id == 'sell':
            self.gold += RELICS[choice.context].value
            self.log.append(f'Sold {RELICS[choice.context].name}.')
        else:
            self.crystals += 4
            self.log.append('Distilled a duplicate relic into 4 crystals.')
        self._choices.pop(0)
        # Several levels from one reward must offer the newly learned rank next.
        for i, pending in enumerate(self._choices):
            if pending.kind == 'skill':
                self._choices[i] = self._skill_choice()

    def equip(self, relic_id: str | None) -> None:
        if self.battle is not None:
            raise RuleError('Change equipment between battles.')
        if relic_id is not None and relic_id not in self.inventory:
            raise RuleError('You do not own that relic.')
        self.hero.relic = relic_id
        self.log.append(f'Equipped {RELICS[relic_id].name}.' if relic_id else 'Unequipped the relic.')

    def _ready(self, action: bool = False) -> None:
        if self.status != 'playing':
            raise RuleError('This campaign has ended. Start a new shard.')
        if self.battle is not None:
            raise RuleError('Finish or retreat from the battle first.')
        if self.choice is not None:
            raise RuleError('Resolve the pending choice first.')
        if action and self.actions_left <= 0:
            raise RuleError('No campaign actions remain. End the turn.')

    def build(self, kind: str) -> None:
        self._ready()
        if kind not in BUILDINGS:
            raise RuleError('Unknown building.')
        if kind in self.buildings:
            raise RuleError('That building is already built.')
        spec = BUILDINGS[kind]
        if self.gold < spec.cost or self.crystals < spec.crystals:
            raise RuleError('Not enough gold or crystals.')
        self.gold -= spec.cost
        self.crystals -= spec.crystals
        self.buildings.add(kind)
        if kind == 'mage_tower':
            self.hero.max_mana += 4
            self.hero.mana += 4
        self.log.append(f'Built {spec.name}.')

    def recruit_crystal_cost(self, kind: str) -> int:
        if kind not in RECRUITABLE:
            raise RuleError('That unit cannot be recruited.')
        return UNITS[kind].crystals

    def _fresh_troop(self, kind: str) -> Troop:
        return Troop(self.next_troop_id, kind, UNITS[kind].hp, UNITS[kind].hp)

    def _purchase_troop(self, kind: str) -> Troop:
        troop = self._fresh_troop(kind)
        self.gold -= self.recruit_cost(kind)
        self.crystals -= self.recruit_crystal_cost(kind)
        self.next_troop_id += 1
        return troop

    def quote_infusion(self, *, province: Province, owner: str, encircled: bool) -> InfusionPreview:
        """Quote an optional Tower infusion without spending mana, currency or an action."""
        mana = min(8, self.hero.max_mana - self.hero.mana)
        try:
            self._ready(action=True)
        except RuleError as error:
            reason = str(error)
        else:
            if province.owner != owner:
                reason = 'Infuse in one of your provinces.'
            elif encircled:
                reason = f'Encirclement blocks infusion at {province.name}.'
            elif 'mage_tower' not in self.buildings:
                reason = 'Build a Mage Tower to infuse mana.'
            elif not mana:
                reason = 'Mana is already full.'
            elif self.crystals < 3:
                reason = 'Infusion requires 3 crystals.'
            else:
                reason = None
        return InfusionPreview(mana, 3, 1, reason)

    def purchase_infusion(self, *, province: Province, owner: str, encircled: bool) -> None:
        """Trade crystals and one campaign action for up to eight mana in a supplied camp."""
        quote = self.quote_infusion(province=province, owner=owner, encircled=encircled)
        if quote.blocked_reason:
            raise RuleError(quote.blocked_reason)
        self.crystals -= quote.crystals
        self.actions_left -= quote.actions
        self.hero.mana += quote.mana
        self.log.append(f'Infused {quote.mana} mana for {quote.crystals} crystals and one action.')

    def _check_purchase(self, kind: str, *, province: Province, owner: str, replacing: bool = False) -> None:
        self._ready(action=replacing)
        if kind not in RECRUITABLE:
            raise RuleError('That unit cannot be recruited.')
        if province.owner != owner:
            raise RuleError('Recruit in one of your provinces.')
        spec = UNITS[kind]
        if spec.building and spec.building not in self.buildings:
            raise RuleError(f'Build {BUILDINGS[spec.building].name} first.')
        if not replacing and len(self.hero.army) >= self.hero.max_army:
            raise RuleError('Your army is full.')
        cost = self.recruit_cost(kind)
        if self.gold < cost or self.crystals < self.recruit_crystal_cost(kind):
            raise RuleError('Not enough gold or crystals.')

    def purchase_recruit(self, kind: str, *, province: Province, owner: str) -> None:
        self._check_purchase(kind, province=province, owner=owner)
        self.hero.army.append(self._purchase_troop(kind))
        self.log.append(f'Recruited {UNITS[kind].name}.')

    def quote_replacement(self, outgoing_id: int, kind: str, *, province: Province, owner: str) -> ReplacementPreview:
        """Quote permanent retirement and a fresh paid role without changing the army."""
        outgoing = next((troop for troop in self.hero.army if troop.id == outgoing_id), None)
        if outgoing is None:
            raise RuleError('Choose a living troop to retire.')
        gold, crystals = self.recruit_cost(kind), self.recruit_crystal_cost(kind)
        incoming = self._fresh_troop(kind)
        try:
            self._check_purchase(kind, province=province, owner=owner, replacing=True)
        except RuleError as error:
            reason = str(error)
        else:
            reason = None
        upkeep = self.upkeep
        return ReplacementPreview(TroopSnapshot(**asdict(outgoing)), TroopSnapshot(**asdict(incoming)),
                                  gold, crystals, 1, upkeep,
                                  upkeep - UNITS[outgoing.kind].upkeep + UNITS[kind].upkeep, reason)

    def purchase_replacement(self, outgoing_id: int, kind: str, *, province: Province, owner: str) -> None:
        """Retire one troop and buy a fresh recruit in its slot for one campaign action."""
        quote = self.quote_replacement(outgoing_id, kind, province=province, owner=owner)
        if quote.blocked_reason:
            raise RuleError(quote.blocked_reason)
        index = next(i for i, troop in enumerate(self.hero.army) if troop.id == outgoing_id)
        self.hero.army[index] = self._purchase_troop(kind)
        self.actions_left -= quote.actions
        self.log.append(f'Retired {UNITS[quote.outgoing.kind].name} #{outgoing_id} '
                        f'(rank {quote.outgoing.level}, XP {quote.outgoing.xp}); '
                        f'recruited {UNITS[kind].name} #{quote.incoming.id} for '
                        f'{quote.gold} gold and {quote.crystals} crystals; spent one action.')
