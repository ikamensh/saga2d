"""Audio settings with live preview and explicit Apply/Cancel ownership."""

from saga2d import Settings, SettingsError

from eador.preferences import DEFAULTS, apply_preferences, validate_preferences
from eador.scene import Screen
from eador.style import GOLD, MUTED, RED, TEAL


ROWS = (("master", "Master volume", "Overall level for all sound."),
        ("music", "Music volume", "Music and ambience."),
        ("sfx", "Sound effects", "Interface and action sounds."),
        ("muted", "Mute all audio", "Silence sound without changing your levels."))


class SettingsScene(Screen):
    transparent = True
    controls = {"up": "previous_row", "down": "next_row", "left": "decrease", "right": "increase"}

    def __init__(self):
        super().__init__()
        self.selected = 0
        self.committed = False
        self.recover = False
        self.last_error = None

    def on_enter(self):
        self.preferences = self.game.settings(DEFAULTS, validator=validate_preferences)
        self.preferences.load()
        self.draft = {key: self.preferences[key] for key in DEFAULTS}
        self.entry_audio = {channel: self.game.audio.get_volume(channel) for channel in ("master", "music", "sfx")}
        self.entry_audio["muted"] = self.game.audio.muted
        self.load_error = self.preferences.error
        self.message = self.load_error.replace(str(self.preferences.path), "settings.json") if self.load_error else ""
        super().on_enter()

    def on_exit(self):
        if not self.committed:
            apply_preferences(self.game, self.entry_audio)

    def previous_row(self):
        self.selected = (self.selected - 1) % len(ROWS)
        self.refresh()

    def next_row(self):
        self.selected = (self.selected + 1) % len(ROWS)
        self.refresh()

    def decrease(self):
        self.adjust(self.selected, -1)

    def increase(self):
        self.adjust(self.selected, 1)

    def adjust(self, index, direction):
        self.selected = index
        key = ROWS[index][0]
        self.draft[key] = not self.draft[key] if key == "muted" else round(max(0, min(1, self.draft[key] + direction * .1)), 2)
        apply_preferences(self.game, self.draft)
        self.refresh()

    def apply(self):
        candidate = Settings(self.preferences.path, DEFAULTS, validator=validate_preferences)
        self.load_error = candidate.error
        try:
            if self.recover:
                candidate.reset()
            candidate.update(self.draft)
            candidate.save()
        except SettingsError as error:
            self.last_error = error
            cause = error.__cause__
            reason = cause.strerror if isinstance(cause, OSError) and cause.strerror else str(cause or error)
            self.message = f"Could not apply settings: {reason}. Your edits are still open."
            self.refresh()
            return
        self.preferences.load()
        if self.preferences.error is not None:
            self.message = "Settings were written but could not be reloaded. Reopen Settings to retry."
            self.refresh()
            return
        apply_preferences(self.game, self.draft)
        self.committed = True
        self.game.pop()

    def cancel(self):
        self.game.pop()

    def restore_defaults(self):
        self.recover = True
        self.draft = dict(DEFAULTS)
        apply_preferences(self.game, self.draft)
        self.message = "Defaults previewed. Apply will retain the damaged file before saving."
        self.refresh()

    @property
    def panel(self):
        return ((self.game.width - 840) / 2, (self.game.height - 660) / 2, 840, 660)

    def refresh(self):
        super().refresh()
        x, y, w, h = self.panel
        for index, (key, label, _) in enumerate(ROWS):
            ry = y + 154 + index * 72
            if key == "muted":
                self.button("Unmute" if self.draft[key] else "Mute", x + 628, ry, 152,
                            lambda: self.adjust(3, 1))
            else:
                self.button("−", x + 628, ry, 60, lambda index=index: self.adjust(index, -1),
                            enabled=self.draft[key] > 0)
                self.button("+", x + 720, ry, 60, lambda index=index: self.adjust(index, 1),
                            enabled=self.draft[key] < 1)
        if self.load_error:
            self.button("Preserve damaged file & use defaults", x + 36, y + 505, 490,
                        self.restore_defaults, shortcut="R", enabled=not self.recover)
        self.button("Cancel", x + 466, y + h - 62, 144, self.cancel, shortcut="Esc")
        self.button("Apply", x + 628, y + h - 62, 152, self.apply, shortcut="Enter", primary=True)

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (0, 0, 0, 205))
        x, y, w, h = self.panel
        self.box(x, y, w, h)
        self.text("SETTINGS", x + 36, y + 27, size=12, color=GOLD)
        self.text("Sound & music", x + 36, y + 53, size=31, serif=True)
        self.text("Changes preview live. Apply saves; Cancel restores your previous sound.", x + 36, y + 104, size=13)
        self.rule(x + 36, y + 134, w - 72)
        for index, (key, label, hint) in enumerate(ROWS):
            ry = y + 154 + index * 72
            if index == self.selected:
                self.draw_rect(x + 20, ry - 8, w - 40, 63, (37, 60, 65, 220), border_color=TEAL, border_width=1, radius=4)
                self.text("›", x + 26, ry + 7, size=22, color=GOLD)
            self.text(label, x + 52, ry + 1, size=17)
            self.text(hint, x + 52, ry + 27, size=11, color=MUTED)
            value = ("On" if self.draft[key] else "Off") if key == "muted" else f"{self.draft[key]:.0%}"
            self.text(value, x + 454, ry + 9, size=19, color=GOLD)
        self.rule(x + 36, y + 445, w - 72)
        notice = "A saved settings file could not be read. It is still intact." if self.load_error else "Up/Down selects a row · Left/Right changes its value."
        self.paragraph(notice, x + 36, y + 462, width=w - 72, size=12, color=RED if self.load_error else MUTED)
        if self.message:
            self.paragraph(self.message, x + 36, y + 553, width=w - 72, size=11,
                           color=TEAL if self.recover and not self.message.startswith("Could not") else RED)
        else:
            self.text("Sound settings apply to every shard and stay separate from your progress.", x + 36, y + 563, size=11, color=MUTED)
