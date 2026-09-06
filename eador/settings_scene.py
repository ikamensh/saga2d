"""Presentation settings with live preview and explicit Apply/Cancel ownership."""

import os
from copy import deepcopy

from saga2d import Anchor, Label, Settings, SettingsError

from eador.preferences import (DEFAULTS, WINDOW_SIZES, apply_display_preferences,
                               apply_preferences, reading_scale, reduced_motion, validate_preferences)
from eador.scene import Screen
from eador.style import GOLD, MUTED, RED, TEAL


SOUND_ROWS = (("master", "Master volume", "Overall level for all sound."),
              ("music", "Music volume", "Music and ambience."),
              ("sfx", "Sound effects", "Interface and action sounds."),
              ("muted", "Mute all audio", "Silence sound without changing your levels."))
DISPLAY_ROWS = (("window_size", "Window size", "Resize the window; the game canvas stays fixed."),
                ("fullscreen", "Fullscreen", "Use the desktop's current resolution."),
                ("reduced_motion", "Reduced motion", "Keep damage numbers still."),
                ("codex_text_scale", "Reading size", "Read guidance at this size."))


class SettingsScene(Screen):
    transparent = True
    controls = {"up": "previous_row", "down": "next_row", "left": "decrease", "right": "increase",
                "tab": "next_page"}

    def __init__(self, *, focus=None):
        super().__init__()
        self.page, self.selected = "sound", 0
        if focus is not None:
            matches = [(page, index) for page, rows in (("sound", SOUND_ROWS), ("display", DISPLAY_ROWS))
                       for index, row in enumerate(rows) if row[0] == focus]
            if not matches:
                raise ValueError(f"Unknown settings row: {focus}")
            self.page, self.selected = matches[0]
        self.committed = False
        self.recover = False
        self.last_error = None

    @property
    def rows(self):
        return SOUND_ROWS if self.page == "sound" else DISPLAY_ROWS

    def on_enter(self):
        self.preferences = self.game.settings(DEFAULTS, validator=validate_preferences)
        self.preferences.load()
        self.entry = deepcopy(DEFAULTS)
        self.entry.update({channel: self.game.audio.get_volume(channel) for channel in ("master", "music", "sfx")})
        self.entry.update(muted=self.game.audio.muted, reduced_motion=reduced_motion(self.game),
                          codex_text_scale=reading_scale(self.game),
                          window_size=list(self.game.windowed_size), fullscreen=self.game.fullscreen)
        self.draft = {key: deepcopy(self.preferences[key]) for key in DEFAULTS}
        # The native window may have been resized or launched with an explicit override.
        for key in ("window_size", "fullscreen", "reduced_motion", "codex_text_scale"):
            self.draft[key] = self.entry[key]
        self.load_error = self.preferences.error
        self.message = self.load_error.replace(str(self.preferences.path), "settings.json") if self.load_error else ""
        super().on_enter()

    def update(self, dt):
        size, fullscreen = list(self.game.windowed_size), self.game.fullscreen
        if self.draft["window_size"] != size or self.draft["fullscreen"] != fullscreen:
            self.draft.update(window_size=size, fullscreen=fullscreen)
            self.refresh()

    def on_exit(self):
        if not self.committed:
            apply_preferences(self.game, self.entry)
            apply_display_preferences(self.game, self.entry)

    def select_page(self, page):
        self.page = page
        self.selected = 0
        self.refresh()

    def next_page(self):
        self.select_page("display" if self.page == "sound" else "sound")

    def previous_row(self):
        self.selected = (self.selected - 1) % len(self.rows)
        self.refresh()

    def next_row(self):
        self.selected = (self.selected + 1) % len(self.rows)
        self.refresh()

    def decrease(self):
        self.adjust(self.selected, -1)

    def increase(self):
        self.adjust(self.selected, 1)

    def next_size(self, direction):
        current = self.game.windowed_size
        candidates = [size for size in WINDOW_SIZES if (size > current if direction > 0 else size < current)]
        return (min(candidates) if direction > 0 else max(candidates)) if candidates else current

    def adjust(self, index, direction):
        self.selected = index
        key = self.rows[index][0]
        if key == "window_size":
            size = self.next_size(direction)
            if size != self.game.windowed_size:
                self.game.set_window_size(size)
                self.draft[key] = list(self.game.windowed_size)
                self.draft["fullscreen"] = False
        elif key == "fullscreen":
            if not self.game.fullscreen and os.environ.get("SAGA2D_HEADLESS", "").strip() not in ("", "0"):
                self.message = "Fullscreen is unavailable while SAGA2D_HEADLESS is set."
            else:
                self.game.set_fullscreen(not self.game.fullscreen)
                self.draft[key] = self.game.fullscreen
        elif key == "codex_text_scale":
            self.draft[key] = 125 if direction > 0 else 100
        elif type(self.draft[key]) is bool:
            self.draft[key] = not self.draft[key]
        else:
            self.draft[key] = round(max(0, min(1, self.draft[key] + direction * .1)), 2)
        apply_preferences(self.game, self.draft)
        self.refresh()

    def apply(self):
        # A native OS resize during editing is also a deliberate display choice.
        self.draft.update(window_size=list(self.game.windowed_size), fullscreen=self.game.fullscreen)
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
        self.draft = deepcopy(DEFAULTS)
        apply_preferences(self.game, self.draft)
        apply_display_preferences(self.game, self.draft)
        self.message = "Defaults previewed. Apply will retain the damaged file before saving."
        self.refresh()

    @property
    def panel(self):
        return ((self.game.width - 840) / 2, (self.game.height - 700) / 2, 840, 700)

    def refresh(self):
        super().refresh()
        x, y, w, h = self.panel
        self.button("Sound", x + 488, y + 36, 136, lambda: self.select_page("sound"),
                    shortcut="S", enabled=self.page != "sound")
        self.button("Display", x + 644, y + 36, 136, lambda: self.select_page("display"),
                    shortcut="D", enabled=self.page != "display")
        toggles = {"muted": ("Unmute", "Mute"), "fullscreen": ("Go windowed", "Go fullscreen"),
                   "reduced_motion": ("Full motion", "Reduce motion")}
        for index, (key, label, hint) in enumerate(self.rows):
            ry = y + 154 + index * 72
            if key in toggles:
                on, off = toggles[key]
                self.button(on if self.draft[key] else off, x + 628, ry, 152,
                            lambda index=index: self.adjust(index, 1))
            else:
                if key == "codex_text_scale":
                    lower, higher = self.draft[key] > 100, self.draft[key] < 125
                    self.ui.add(Label(hint, width=360, wrap=True, font="Verdana", font_size=round(13 * self.draft[key] / 100),
                                      text_color=MUTED, anchor=Anchor.TOP_LEFT, margin=(round(x + 52), round(ry + 27))))
                else:
                    lower = self.next_size(-1) != self.game.windowed_size if key == "window_size" else self.draft[key] > 0
                    higher = self.next_size(1) != self.game.windowed_size if key == "window_size" else self.draft[key] < 1
                self.button("−", x + 628, ry, 60, lambda index=index: self.adjust(index, -1), enabled=lower)
                self.button("+", x + 720, ry, 60, lambda index=index: self.adjust(index, 1), enabled=higher)
        if self.load_error:
            self.button("Preserve damaged file & use defaults", x + 36, y + 538, 490,
                        self.restore_defaults, shortcut="R", enabled=not self.recover)
        self.button("Cancel", x + 466, y + h - 62, 144, self.cancel, shortcut="Esc")
        self.button("Apply", x + 628, y + h - 62, 152, self.apply, shortcut="Enter", primary=True)

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (0, 0, 0, 205))
        x, y, w, h = self.panel
        self.box(x, y, w, h)
        self.text("SETTINGS", x + 36, y + 27, size=12, color=GOLD)
        self.text("Sound & music" if self.page == "sound" else "Display & motion", x + 36, y + 53, size=31, serif=True)
        self.text("Changes preview live. Apply saves both tabs; Cancel restores your previous settings.", x + 36, y + 104, size=13)
        self.rule(x + 36, y + 134, w - 72)
        for index, (key, label, hint) in enumerate(self.rows):
            ry = y + 154 + index * 72
            if index == self.selected:
                self.draw_rect(x + 20, ry - 8, w - 40, 63, (37, 60, 65, 220), border_color=TEAL, border_width=1, radius=4)
                self.text("›", x + 26, ry + 7, size=22, color=GOLD)
            self.text(label, x + 52, ry + 1, size=17)
            if key != "codex_text_scale":
                self.text(hint, x + 52, ry + 27, size=11, color=MUTED)
            if key == "window_size":
                value = " × ".join(map(str, self.game.windowed_size))
            elif key == "codex_text_scale":
                value = f'{self.draft[key]}%'
            elif type(self.draft[key]) is bool:
                value = "On" if self.draft[key] else "Off"
            else:
                value = f"{self.draft[key]:.0%}"
            self.text(value, x + 454, ry + 9, size=17 if key == "window_size" else 19, color=GOLD)
        if self.page == "display":
            actual = " × ".join(map(str, self.game.window_size))
            canvas = " × ".join(map(str, self.game.resolution))
            mode = "fullscreen" if self.game.fullscreen else "windowed"
            self.text(f"Now {actual} {mode} · Game canvas {canvas} (fixed).", x + 52, y + 446, size=12, color=MUTED)
        self.rule(x + 36, y + 477, w - 72)
        notice = "A saved settings file could not be read. It is still intact." if self.load_error else "Tab switches pages · Up/Down selects a row · Left/Right changes its value."
        if self.page == "display" and not self.load_error:
            notice = "Reading size: Codex, Field Guide, briefings, Build and Recruit. Other screens keep their sizes.\nTab: page · Up/Down: row · Left/Right: value."
        self.paragraph(notice, x + 36, y + 494, width=w - 72, size=12, color=RED if self.load_error else MUTED)
        if self.message:
            self.paragraph(self.message, x + 36, y + 586, width=w - 72, size=11,
                           color=TEAL if self.recover and not self.message.startswith("Could not") else RED)
        else:
            self.text("Settings apply to every shard and stay separate from your progress.", x + 36, y + 596, size=11, color=MUTED)
