"""Bounded shared-combat presentation, replayed separately from campaign settlement."""
from dataclasses import dataclass
import hashlib
import json
from uuid import uuid4

from saga2d import CommandError
from eador.battle import Battle
from eador.battle_trace import BattleEvent, BattleFrame, BattleTrace
from eador.orders import BATTLE_ORDERS, invoke_order

MAX_RECORDS = 24
MAX_BYTES = 192 * 1024


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


class CombatJournal:
    """Ephemeral authority history; immutable encoded records keep trial copies small.

    Head counts every accepted order, including one too large to retain. A gap
    tells presentation to catch up to the authoritative state. New/restored
    authorities start fresh epochs; this history never belongs in saved realms.
    """
    def __init__(self):
        self.epoch = uuid4().hex
        self.head = 0
        self._battle_id = None
        self._records = ()
        self._bytes = 0

    def begin(self):
        """Identify a new duel without erasing unconsumed terminal records from its predecessor."""
        self._battle_id = uuid4().hex

    def record(self, before: dict, after: dict, command: dict, *, attacker: int, destination: tuple):
        if self._battle_id is None:
            self.begin()  # First order after restoring an active duel.
        self.head += 1
        encoded = _json(dict(seq=self.head, battle_id=self._battle_id, attacker=attacker,
                             destination=destination, before=before, command=command,
                             after_sha256=_digest(after)))
        self._records += (encoded,)
        self._bytes += len(encoded)
        while len(self._records) > MAX_RECORDS or self._bytes > MAX_BYTES:
            self._bytes -= len(self._records[0])
            self._records = self._records[1:]

    def snapshot(self):
        return {'epoch': self.epoch, 'head': self.head,
                'records': [json.loads(record) for record in self._records]}


@dataclass(frozen=True)
class RecordedCombat:
    battle: Battle
    trace: BattleTrace
    attacker: int
    destination: tuple[int, int]


def replay_combat(records) -> RecordedCombat:
    """Reproduce one contiguous duel segment without touching live armies or rewards.

    Digest/continuity failures indicate incompatible or missing presentation.
    The caller can discard the animation and display the authoritative snapshot.
    """
    def incompatible(reason):
        raise CommandError(f'Combat presentation {reason}. Refresh from the authoritative state.')

    if not records:
        incompatible('has no orders to replay')
    first = records[0]
    required = {'seq', 'battle_id', 'attacker', 'destination', 'before', 'command', 'after_sha256'}
    if not isinstance(first, dict) or set(first) != required:
        incompatible('uses an unsupported record version')
    if (type(first['seq']) is not int or first['seq'] < 1 or not isinstance(first['battle_id'], str)
            or type(first['attacker']) is not int or first['attacker'] not in (0, 1)
            or not isinstance(first['destination'], (tuple, list)) or len(first['destination']) != 2
            or any(type(value) is not int for value in first['destination'])):
        incompatible('has invalid encounter identity')
    if not isinstance(first['before'], dict):
        incompatible('uses an unsupported battle version')
    try:
        battle = Battle.from_dict(first['before'])
    except (KeyError, TypeError, ValueError) as error:
        raise CommandError('Combat presentation uses an unsupported battle version. '
                           'Refresh from the authoritative state.') from error
    if battle.enemy_magic is None:
        incompatible('does not describe a shared human battle')
    initial, events = BattleFrame.capture(battle), []
    for index, record in enumerate(records):
        if (not isinstance(record, dict) or set(record) != required
                or record['seq'] != first['seq'] + index
                or record['battle_id'] != first['battle_id'] or record['attacker'] != first['attacker']
                or record['destination'] != first['destination']):
            incompatible('has a missing order or a different encounter')
        if _digest(battle.to_dict()) != _digest(record['before']):
            incompatible('does not continue the previous order')
        command = record['command']
        if not isinstance(command, dict):
            incompatible('uses an unsupported order version')
        if command.get('action') == 'retreat':
            if (set(command) != {'action', 'outcome', 'reason'} or battle.outcome is not None
                    or command['outcome'] not in ('player', 'enemy') or command['reason'] != 'retreat'):
                incompatible('has an invalid retreat result')
            before = BattleFrame.capture(battle)
            battle.outcome, battle.outcome_reason = command['outcome'], command['reason']
            after = BattleFrame.capture(battle)
            trace = BattleTrace(before, (BattleEvent('result', None, None, 'Army retreats.', before, after),), after)
        else:
            if (set(command) != {'action', 'args', 'kwargs'} or not isinstance(command.get('action'), str)
                    or command['action'] not in BATTLE_ORDERS or not isinstance(command['args'], list)
                    or not isinstance(command['kwargs'], dict)):
                incompatible('uses an unsupported tactical order')
            try:
                trace = battle.trace(lambda: invoke_order(battle, command['action'], command['args'], command['kwargs']))
            except CommandError as error:
                raise CommandError('Combat presentation no longer matches these tactical rules. '
                                   'Refresh from the authoritative state.') from error
        if _digest(battle.to_dict()) != record['after_sha256']:
            incompatible('does not match the recorded rules version')
        events.extend(trace.events)
    return RecordedCombat(battle, BattleTrace(initial, tuple(events), BattleFrame.capture(battle)),
                          first['attacker'], tuple(first['destination']))
