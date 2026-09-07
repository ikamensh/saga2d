"""Bounded, skippable viewing of orders whose authoritative rules already resolved."""
from dataclasses import asdict, replace
import math

from saga2d import Column, Label

from eador.battle import Battle, SmokeCloud
from eador.battle_audio import event_cues
from eador.preferences import reading_scale, reduced_motion
from eador.scene import BattleScene, Screen
from eador.style import GOLD, MUTED, TEAL, TEXT


class BattlePlayback:
    """An isolated visual battle plus a clock; never writes to its source battle."""
    MAX_SECONDS = 8.0

    def __init__(self, battle, trace):
        self.trace = trace
        self.view = Battle.from_dict(battle.to_dict())
        self.view.log = []
        self.index = 0
        self.elapsed = 0.0
        self.duration = min(.8, self.MAX_SECONDS / len(trace.events))
        self._apply(trace.before)

    @property
    def done(self):
        return self.index >= len(self.trace.events)

    @property
    def event(self):
        return self.trace.events[min(self.index, len(self.trace.events) - 1)]

    @property
    def fraction(self):
        return min(1.0, self.elapsed / self.duration)

    @property
    def applied(self):
        return self.fraction >= .5

    def _apply(self, frame):
        self.view.units = [replace(self.view.unit(unit.id), **asdict(unit)) for unit in frame.units]
        self.view.mana, self.view.round = frame.mana, frame.round
        self.view.objective.progress = frame.progress
        self.view.outcome, self.view.outcome_reason = frame.outcome, frame.outcome_reason
        self.view.smoke_clouds = [SmokeCloud(*cloud) for cloud in frame.smoke]

    def advance(self, dt):
        self.elapsed += dt
        while not self.done and self.elapsed >= self.duration:
            self.elapsed -= self.duration
            self.index += 1
        self._apply(self.trace.after if self.done else self.event.after if self.applied else self.event.before)
        completed = len(self.trace.events) if self.done else self.index + self.applied
        self.view.log = [event.text for event in self.trace.events[:completed]]

    def position(self, unit, grid, *, still=False):
        event = self.event
        moved = event.before.unit(unit.id).pos != event.after.unit(unit.id).pos
        if still or self.done or not moved:
            return grid.center(unit.pos)
        path = event.path if event.kind == 'move' and unit.id == event.actor_id else (
            event.before.unit(unit.id).pos, event.after.unit(unit.id).pos)
        progress = self.fraction * (len(path) - 1)
        segment = min(int(progress), len(path) - 2)
        amount = progress - segment
        a, b = grid.center(path[segment]), grid.center(path[segment + 1])
        x, y = a[0] + (b[0] - a[0]) * amount, a[1] + (b[1] - a[1]) * amount
        if event.kind == 'swap':
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            bend = math.sin(self.fraction * math.pi) * grid.size * .28
            x -= (b[1] - a[1]) / length * bend
            y += (b[0] - a[0]) / length * bend
        elif unit.can_fly:
            y -= math.sin(self.fraction * math.pi) * 10
        return x, y


class BattlePlaybackScene(BattleScene):
    """Reuse the battle HUD in a modal scene that owns all playback input."""
    controls = {'space': 'finish', 'return': 'finish', 'escape': 'finish',
                'f5': 'save_game', 'f9': 'load_game', 'f6': 'browse_saves',
                'f1': 'help', 'f2': 'open_text_settings'}
    accepts_orders = False

    def __init__(self, parent, trace, *, finish_contacts_on_skip=False):
        self.parent = parent
        self.playback = BattlePlayback(parent.battle, trace)
        self.finished = False
        # A decisive manual hit keeps its short contact sequence when skipped;
        # skipping a whole enemy/autoplay turn must not burst every omitted cue.
        self.finish_contacts_on_skip = finish_contacts_on_skip
        self._contact_cursor = 0
        super().__init__(parent.root)
        self.selected = parent.selected
        self.message = parent.message
        self._shown = None

    @property
    def battle(self):
        return self.playback.view

    def on_enter(self):
        Screen.on_enter(self)
        self._announce()

    def _phase_button(self, x, y):
        self.button('Finish playback', x, y, 300, self.finish, hotkey='Space', primary=True)

    def _command_content(self):
        scale = reading_scale(self.game) / 100
        def label(text, size=12, color=MUTED):
            return Label(text, width=300, wrap=True, font='Verdana', font_size=round(size * scale), text_color=color)
        event = self.playback.event
        lines = [label(f'Action {self.playback.index + 1} of {len(self.playback.trace.events)}', color=GOLD),
                 label(event.text, 15, TEXT)]
        if event.actor_id is not None:
            unit = self.battle.unit(event.actor_id)
            side = "Enemy" if unit.team == "enemy" else "Your"
            lines.append(label(f'{side} {unit.name}: {unit.hp}/{unit.max_hp} HP', color=TEAL))
        lines.extend([label('Watch each move, ability and reaction in order.'),
                      label('Space, Enter or Esc finishes playback.'),
                      label('Saving records the outcome of these orders. Loading skips their animation.', 11)])
        return Column(*lines, spacing=18)

    def order_hint(self):
        return 'Watching resolved actions. Space finishes playback; L opens the complete battle log.'

    def action_targets(self):
        return []

    def act(self, callback, **options):
        """The modal owns input; no battle command is accepted during playback."""
        return None

    def handle_input(self, event):
        return False

    def read_log(self):
        self.parent.read_log()

    def _unit_center(self, unit):
        return self.playback.position(unit, self.grid, still=reduced_motion(self.game))

    def _unit_layer(self, unit):
        event = self.playback.event
        if not reduced_motion(self.game) and event.before.unit(unit.id).pos != event.after.unit(unit.id).pos:
            return 5
        return 3

    def _play_contacts(self, stop):
        for event in self.playback.trace.events[self._contact_cursor:stop]:
            _, contact = event_cues(self.battle, event, self.root.state.hero.hero_class)
            if contact:
                self.game.audio.play_sound(contact)
        self._contact_cursor = stop

    def _announce(self):
        shown = self.playback.index, self.playback.applied
        if shown == self._shown:
            return
        self._play_contacts(self.playback.index)
        event = self.playback.event
        release, _ = event_cues(self.battle, event, self.root.state.hero.hero_class)
        if self._shown is None or self._shown[0] != shown[0]:
            if release:
                self.game.audio.play_sound(release)
        self.floats = []
        if self.playback.applied:
            self._play_contacts(self.playback.index + 1)
            for unit in event.after.units:
                amount = unit.hp - event.before.unit(unit.id).hp
                if amount:
                    self.floats.append((self.clock, unit.pos, amount))
        self._shown = shown
        self.refresh()

    def update(self, dt):
        self.clock += dt
        self.playback.advance(dt)
        if self.playback.done:
            self._play_contacts(len(self.playback.trace.events))
            self.finish()
            return
        self._announce()
        if self._reading_view != (self.hover, self.message, self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def _feedback_event(self):
        return (None, 0) if self.playback.done else (self.playback.event, self.playback.fraction)

    def finish(self):
        if not self.finished:
            self.finished = True
            if self.finish_contacts_on_skip:
                self._play_contacts(len(self.playback.trace.events))
            self.parent.message = self.message
            self.game.pop()
            self.parent.finish_phase()
