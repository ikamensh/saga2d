"""Read a complete diagnostic; the originating screen retains all retry/confirmation policy."""

from saga2d import Anchor, Column, Label

from eador.preferences import reading_scale
from eador.reading import reading_text_pages
from eador.scene import Screen
from eador.style import MUTED, RED, TEXT


class DiagnosticScene(Screen):
    """A read-only error snapshot with measured pages and ordinary scene-stack input isolation."""

    transparent = True
    controls = {('left', 'pageup'): 'previous_page', ('right', 'pagedown'): 'next_page'}

    def __init__(self, message, *, return_label='Return'):
        super().__init__()
        self.message, self.return_label = message, return_label
        self.page = 0
        self._pages = ('',)

    @property
    def pages(self):
        return len(self._pages)

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.refresh()

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def refresh(self):
        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        self.x, self.y = (self.game.width - 1120) / 2, (self.game.height - 760) / 2
        x, y = self.x + 28, self.y + 28

        def label(text, *, width=1064, color=RED):
            return Label(text, width=width, wrap=True, font='Verdana', font_size=round(12 * scale), text_color=color)

        title = Label('Complete save/load diagnostic', width=800, wrap=True,
                      font='Georgia', font_size=30, text_color=TEXT)
        body_y = y + self.measure(title)[1] + 24
        bottom = self.y + 692
        self._pages = reading_text_pages(self.message, bottom - body_y - 24,
                                        measure=lambda text: self.measure(label(text))[1])
        self.page = min(self.page, self.pages - 1)
        for component, top in ((title, y), (label(self._pages[self.page]), body_y)):
            self.ui.add(Column(component, anchor=Anchor.TOP_LEFT, margin=(round(x), round(top))))
        self.button('Text size', self.x + 886, y, 206, self.open_text_settings, shortcut='T')
        self.button('Previous', x, bottom, 160, self.previous_page, hotkey='PageUp', enabled=self.page > 0)
        self.button('Next', x + 178, bottom, 160, self.next_page, hotkey='PageDown', enabled=self.page + 1 < self.pages)
        page = label(f'Page {self.page + 1} / {self.pages}', width=200, color=MUTED)
        self.ui.add(Column(page, anchor=Anchor.TOP_LEFT, margin=(round(x + 362), round(bottom + 10))))
        self.button(self.return_label, self.x + 770, bottom, 322, self.game.pop, shortcut=('Enter', 'Esc'))

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 240))
        self.box(self.x, self.y, 1120, 760)
