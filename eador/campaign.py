"""A bounded three-shard journey. All progression and contract rules are game-owned."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eador.model import State


@dataclass(frozen=True)
class Contract:
    title: str
    objective: str


CONTRACTS = {
    'westwatch': Contract('Westwatch', 'Capture Duskspire and choose your next challenge.'),
    'rootward': Contract('Rootward', 'Clear the Border Watch, then capture Duskspire.'),
    'foundries': Contract('The Foundries', 'Control both marked foundries when beginning the assault on Duskspire.'),
    'throne': Contract('Break the Throne', 'Rout the final stronghold. There is no short battle deadline.'),
    'gate': Contract('Seal the Gate', 'Hold the capital seal for two uncontested enemy phases or rout its defenders by round 8.'),
}
FOUNDRIES = ((0, -1), (0, 1))


@dataclass(frozen=True)
class Offer:
    id: str
    title: str
    description: str
    seed: int
    theme: str
    contract: str


@dataclass(frozen=True)
class ShardRecord:
    stage: int
    theme: str
    contract: str
    turns: int
    hero_level: int
    casualties: int
    garrison: tuple[str, ...] = ()


@dataclass
class Campaign:
    seed: int
    stage: int = 1
    contract: str = 'westwatch'
    phase: str = 'playing'
    recovery_used: bool = False
    casualties: int = 0
    completed: list[ShardRecord] = field(default_factory=list)
    offers: tuple[Offer, ...] = ()
    entry: dict = field(default_factory=dict, repr=False)

    @property
    def title(self) -> str:
        return CONTRACTS[self.contract].title

    @property
    def objective(self) -> str:
        return CONTRACTS[self.contract].objective

    def checkpoint(self, state: State) -> None:
        self.entry = {'provinces': [asdict(p) for p in state.provinces.values()],
                      'rival': asdict(state.rival)}

    def sync(self, state: State) -> None:
        if state.battle or state.choice:
            return
        if state.status == 'defeat':
            self.phase = 'lost' if self.recovery_used else 'recovery'
        elif state.status == 'victory' and self.phase == 'playing':
            self.completed.append(ShardRecord(self.stage, state.theme, self.contract,
                                  state.turn, state.hero.level, self.casualties))
            self.phase = 'completed' if self.stage == 3 else 'departure'
            if self.stage == 1:
                destinations = (('rootward', 'elderwild'), ('foundries', 'ruins'))
            elif self.stage == 2:
                theme = 'ruins' if state.theme == 'elderwild' else 'elderwild'
                destinations = (('throne', theme), ('gate', theme))
            else:
                destinations = ()
            self.offers = tuple(Offer(contract, CONTRACTS[contract].title, CONTRACTS[contract].objective,
                                random.Random(f'{self.seed}:{self.stage}:{contract}').randrange(1_000_000), theme, contract)
                                for contract, theme in destinations)

    @classmethod
    def from_dict(cls, data: dict) -> Campaign:
        return cls(**{**data, 'offers': tuple(Offer(**offer) for offer in data['offers']),
                      'completed': [ShardRecord(**{**record, 'garrison': tuple(record['garrison'])})
                                    for record in data['completed']]})


def validate_campaign(data: dict) -> None:
    """Validate a single bounded campaign object, including its recorded entry world."""
    from eador.model import RECRUITABLE, SaveFormatError, _validate_save

    def require(condition, message):
        if not condition:
            raise SaveFormatError(message)

    campaign = data['campaign']
    if campaign is None:
        return
    require(isinstance(campaign, dict) and campaign.keys() == Campaign.__dataclass_fields__.keys(),
            'Linked campaign has missing or unsupported fields.')
    require(type(campaign['seed']) is int, 'Invalid linked campaign seed.')
    require(type(campaign['stage']) is int and 1 <= campaign['stage'] <= 3, 'Invalid linked campaign stage.')
    require(isinstance(campaign['contract'], str) and campaign['contract'] in CONTRACTS, 'Unknown linked campaign contract.')
    require(campaign['phase'] in ('playing', 'departure', 'recovery', 'completed', 'lost'), 'Unknown linked campaign phase.')
    require(type(campaign['recovery_used']) is bool, 'Invalid campaign recovery flag.')
    require(type(campaign['casualties']) is int and campaign['casualties'] >= 0, 'Invalid campaign casualty count.')
    require(isinstance(campaign['completed'], list) and len(campaign['completed']) <= 3, 'Invalid completed shard records.')
    require(isinstance(campaign['offers'], list) and len(campaign['offers']) <= 2, 'Invalid campaign offers.')
    stage, phase, contract = campaign['stage'], campaign['phase'], campaign['contract']
    require((stage == 1 and contract == 'westwatch' and data['theme'] == 'frontier')
            or (stage == 2 and (contract, data['theme']) in (('rootward', 'elderwild'), ('foundries', 'ruins')))
            or (stage == 3 and contract in ('throne', 'gate') and data['theme'] in ('elderwild', 'ruins')),
            'The stage, theme and contract do not agree.')
    finished = phase in ('departure', 'completed')
    require(len(campaign['completed']) == stage - 1 + finished, 'Completed shard history does not match the stage.')
    require(data['hero']['level'] <= stage + 2 and all(troop['level'] <= 3 for troop in data['hero']['army']),
            'Linked progression exceeds the announced rank limits.')
    if phase == 'playing':
        require(data['status'] == 'playing' or data['status'] == 'victory' and bool(data['choices']),
                'A playing campaign has an inconsistent shard result.')
    else:
        require(data['battle'] is None and not data['choices'], 'Resolve combat and rewards before a campaign transition.')
        require(data['status'] == ('victory' if finished else 'defeat'), 'Campaign phase has the wrong shard result.')
        require(phase != 'departure' or stage < 3, 'The third shard has no next destination.')
        require(phase != 'completed' or stage == 3, 'Campaign completion requires three shards.')
        require(phase != 'recovery' or not campaign['recovery_used'], 'The single recovery is already spent.')
    expected_offers = ({'rootward', 'foundries'} if stage == 1 else {'throne', 'gate'}) if phase == 'departure' else set()
    require(len(campaign['offers']) == len(expected_offers), 'Missing or unexpected campaign offers.')
    offer_ids = set()
    for offer in campaign['offers']:
        require(isinstance(offer, dict) and offer.keys() == Offer.__dataclass_fields__.keys(), 'Invalid offered challenge.')
        require(all(isinstance(offer[key], str) for key in ('id', 'title', 'description', 'theme', 'contract')),
                'Offered challenge contains invalid text.')
        require(type(offer['seed']) is int and offer['id'] == offer['contract'] and offer['contract'] in CONTRACTS,
                'Offered challenge contains an unknown contract or seed.')
        require(offer['id'] not in offer_ids, 'Duplicate offered challenge.')
        offer_ids.add(offer['id'])
        theme = ('elderwild' if offer['id'] == 'rootward' else 'ruins') if stage == 1 else ('ruins' if data['theme'] == 'elderwild' else 'elderwild')
        require(offer['theme'] == theme, 'Offered challenge has the wrong theme.')
    require(offer_ids == expected_offers, 'The campaign offers the wrong next challenges.')
    for index, record in enumerate(campaign['completed'], 1):
        require(isinstance(record, dict) and record.keys() == ShardRecord.__dataclass_fields__.keys(), 'Invalid shard record.')
        require(all(type(record[key]) is int and record[key] >= 0 for key in ('stage', 'turns', 'hero_level', 'casualties')),
                'Shard record contains an invalid count.')
        require(record['stage'] == index and record['turns'] >= 1 and 1 <= record['hero_level'] <= index + 2,
                'Shard history contains an impossible stage or rank.')
        require((index == 1 and (record['theme'], record['contract']) == ('frontier', 'westwatch'))
                or (index == 2 and (record['theme'], record['contract']) in (('elderwild', 'rootward'), ('ruins', 'foundries')))
                or (index == 3 and record['theme'] in ('elderwild', 'ruins') and record['contract'] in ('throne', 'gate')),
                'Shard history contains an unknown or inconsistent contract.')
        require(isinstance(record['garrison'], list) and len(record['garrison']) <= 6
                and all(isinstance(kind, str) and kind in RECRUITABLE for kind in record['garrison']),
                'Shard garrison contains invalid troop kinds.')
    if stage == 3:
        require(data['theme'] != campaign['completed'][1]['theme'], 'The finale must visit the remaining theme.')
    if finished:
        latest = campaign['completed'][-1]
        require((latest['theme'], latest['contract'], latest['turns']) == (data['theme'], contract, data['turn']),
                'The completed shard record differs from its result.')
    entry = campaign['entry']
    require(isinstance(entry, dict) and entry.keys() == {'provinces', 'rival'}, 'Invalid entry-world checkpoint.')
    checkpoint = deepcopy(data)
    checkpoint.update(campaign=None, battle=None, battle_kind=None, battle_province=None,
                      choices=[], status='playing', turn=1, provinces=entry['provinces'], rival=entry['rival'])
    checkpoint['hero']['pos'] = [-2, 0]
    _validate_save(checkpoint, 8)
    require(all(not p['explored'] and p['owner'] == ('player' if p['pos'] == [-2, 0] else 'rival' if p['pos'][0] == 2 else 'neutral')
                for p in entry['provinces']), 'Entry checkpoint is not an initial world.')


def _retinue(state: State, troop_ids, relic_ids):
    from eador.model import RuleError
    if not isinstance(troop_ids, (tuple, list)) or not all(type(uid) is int for uid in troop_ids):
        raise RuleError('Choose up to two living troop IDs.')
    if not isinstance(relic_ids, (tuple, list)) or not all(isinstance(rid, str) for rid in relic_ids):
        raise RuleError('Choose up to two owned relics.')
    if len(troop_ids) > 2 or len(set(troop_ids)) != len(troop_ids):
        raise RuleError('Choose at most two different troops.')
    if len(relic_ids) > 2 or len(set(relic_ids)) != len(relic_ids):
        raise RuleError('Choose at most two different relics.')
    by_id = {troop.id: troop for troop in state.hero.army}
    if any(uid not in by_id for uid in troop_ids) or any(rid not in state.inventory for rid in relic_ids):
        raise RuleError('Only surviving troops and owned relics can travel.')
    return [deepcopy(by_id[uid]) for uid in troop_ids], list(relic_ids)


def _arrive(state: State, candidate: State, troops, relics) -> None:
    from eador.model import Troop, UNITS
    hero = deepcopy(state.hero)
    hero.pos = (-2, 0)
    hero.max_hp = (48 if hero.hero_class == 'Warrior' else 36) + 4 * (hero.level - 1)
    hero.max_mana = (16 if hero.hero_class == 'Wizard' else 10) + 2 * (hero.level - 1)
    hero.hp, hero.mana = hero.max_hp, hero.max_mana
    hero.army = troops
    candidate.next_troop_id = state.next_troop_id
    while len(hero.army) < 3:
        spec = UNITS['militia']
        hero.army.append(Troop(candidate.next_troop_id, 'militia', spec.hp, spec.hp))
        candidate.next_troop_id += 1
    for troop in hero.army:
        troop.hp = troop.max_hp
    hero.relic = hero.relic if hero.relic in relics else next(iter(relics), None)
    candidate.hero, candidate.inventory = hero, relics
    candidate.rival.plan(candidate, delay=2 if candidate.campaign.stage > 1 else 3)
    candidate.log = [f'Stage {candidate.campaign.stage}: {candidate.campaign.title}.', candidate.campaign.objective,
                     f'Hero rank limit {candidate.hero_level_cap}; troop rank limit {candidate.troop_level_cap}.']


def advance(state: State, offer_id: str, troop_ids, relic_ids) -> None:
    from dataclasses import replace
    from eador.model import RuleError, State
    if state.campaign is None or state.campaign.phase != 'departure' or state.battle or state.choice:
        raise RuleError('Finish this linked shard and its rewards before departing.')
    offer = next((offer for offer in state.campaign.offers if offer.id == offer_id), None)
    if offer is None:
        raise RuleError('Choose one of the offered challenges.')
    troops, relics = _retinue(state, troop_ids, relic_ids)
    candidate = State.new(offer.seed, state.hero.hero_class, theme=offer.theme)
    candidate.campaign = deepcopy(state.campaign)
    campaign = candidate.campaign
    campaign.completed[-1] = replace(campaign.completed[-1], garrison=tuple(
        troop.kind for troop in state.hero.army if troop.id not in troop_ids))
    campaign.stage += 1
    campaign.contract, campaign.phase, campaign.offers = offer.contract, 'playing', ()
    campaign.casualties = 0
    candidate.gold, candidate.crystals = 100 + min(40, state.gold), 4 + min(2, state.crystals)
    candidate.rival.gold = 80 if campaign.stage == 2 else 90
    _arrive(state, candidate, troops, relics)
    campaign.checkpoint(candidate)
    state.__dict__.update(candidate.__dict__)
