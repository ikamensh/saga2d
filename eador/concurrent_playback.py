"""Queue shared orders while readers stay open; watch them without settling a realm."""
from dataclasses import replace
import json

from eador.battle_playback_scene import CombatPlaybackScene
from eador.combat_journal import MAX_BYTES, MAX_RECORDS, replay_combat


class CombatInbox:
    """A bounded cursor over the authority's independent combat sequence.

    Joining starts at the current head. A retained viewer either receives every
    subsequent order or explicitly catches up; incomplete fragments never play.
    """

    def __init__(self, presentation):
        self.epoch = presentation['epoch']
        self.head = presentation['head']
        self.records = []
        self._bytes = 0
        self.notice = ''

    def reset(self, presentation, reason):
        self.epoch, self.head = presentation['epoch'], presentation['head']
        self.records.clear()
        self._bytes = 0
        self.notice = reason

    def observe(self, presentation):
        if presentation['epoch'] != self.epoch or presentation['head'] < self.head:
            self.reset(presentation, 'The room restarted. Caught up to the current state.')
            return
        if presentation['head'] == self.head:
            return
        new = [record for record in presentation['records'] if record['seq'] > self.head]
        if (len(new) != presentation['head'] - self.head
                or any(record['seq'] != self.head + index for index, record in enumerate(new, 1))):
            self.reset(presentation, 'Caught up to the current state after missing older animation updates.')
            return
        size = sum(len(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()) for record in new)
        if len(self.records) + len(new) > MAX_RECORDS or self._bytes + size > MAX_BYTES:
            self.reset(presentation, 'Caught up to the current state after the animation queue filled.')
            return
        self.records.extend(new)
        self._bytes += size
        self.head = presentation['head']

    @property
    def pending(self):
        return bool(self.records)

    def take(self):
        battle_id = self.records[0]['battle_id']
        end = next((i for i, record in enumerate(self.records) if record['battle_id'] != battle_id), len(self.records))
        records, self.records = self.records[:end], self.records[end:]
        self._bytes -= sum(len(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()) for record in records)
        return replay_combat(records)

    def take_notice(self):
        notice, self.notice = self.notice, ''
        return notice


class _RecordedView:
    """Freeze battle identity and local perspective; readers still belong to the live room."""
    live_match = True

    def __init__(self, owner, recording):
        self.owner = owner
        self.state = replace(owner.state, battle=recording.battle, battle_kind='army',
                             battle_province=recording.destination, encounter={'attacker': recording.attacker})
        self.battle_team = self.state.battle_team
        self.message = ''
        self.codex, self.help = owner.codex, owner.help

    def save_game(self):
        self.owner.save_game()
        self.message = self.owner.message


class RecordedCombatPlayback(CombatPlaybackScene):
    """Historical combat completion reconciles the live room, never the old result dialog."""

    def __init__(self, owner, recording):
        self.owner = owner
        super().__init__(_RecordedView(owner, recording), recording.battle, recording.trace)

    def finish(self):
        if self.finished:
            return
        self.finished = True
        self.game.pop()
        # Scene-stack mutations are deferred during input/update. Reconcile only
        # after the pop, using a timer owned by the surviving campaign scene.
        self.owner.after(0, self.owner._poll)
