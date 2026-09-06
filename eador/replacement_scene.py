"""Review a permanent retirement and paid recruit using the model's exact quote."""
from saga2d import Anchor, Button, Column, Label, Row

from eador.model import RuleError, UNITS
from eador.preferences import reading_scale
from eador.reading import reading_pages
from eador.scene import CatalogScene, SaveScene, Screen, ShardScene
from eador.style import GOLD, MUTED, RED, TEXT


class ReplacementScene(Screen):
    """Choose the outgoing troop, or review one quoted replacement before spending."""

    transparent = True
    pop_on_cancel = True
    controls = {'f5': 'save_game', 'f9': 'load_game', 'f6': 'browse_saves',
                ('left', 'pageup'): 'previous_page', ('right', 'pagedown'): 'next_page'}

    def __init__(self, root, *, outgoing_id=None, kind=None, description=''):
        super().__init__()
        self.root, self.outgoing_id, self.kind = root, outgoing_id, kind
        self.description = description
        self.applied = False
        self.quote = None
        self.page = 0
        self._page_troops = [tuple(troop.id for troop in root.state.hero.army)]

    @property
    def visible_troops(self):
        return self._page_troops[self.page]

    @property
    def pages(self):
        return len(self._page_troops)

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

    def select(self, outgoing_id):
        self.game.replace(CatalogScene(self.root, 'recruit', outgoing_id=outgoing_id))

    def refresh(self):
        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        state = self.root.state

        def label(text, size=13, *, width=1064, color=MUTED):
            return Label(text, width=width, wrap=True, font='Verdana',
                         font_size=round(size * scale), text_color=color)

        if self.kind is None:
            self.title = 'Choose a veteran to retire'
            introduction = label('Choose a fresh recruit next, then review. Nothing is spent until you confirm Replace.')
            summaries = [label(f'{UNITS[troop.kind].name} #{troop.id} · army slot {index}\n'
                               f'Rank {troop.level} · {troop.xp} XP · {troop.hp}/{troop.max_hp} HP', width=800, color=TEXT)
                         for index, troop in enumerate(state.hero.army, 1)]
            footer = [label(self.message, 12, color=GOLD)] if self.message else []
            self.ui.add(Column(introduction, *summaries, *footer))
            ids = [troop.id for troop in state.hero.army]
            anchor = ids.index(self.visible_troops[0]) if self.visible_troops else 0
            available = self.game.height - 40 - 194 - introduction.get_preferred_size()[1] - 18
            if footer:
                available -= footer[0].get_preferred_size()[1] + 18
            pages, self.page = reading_pages([max(40, item.get_preferred_size()[1]) for item in summaries],
                                             available, anchor=anchor, spacing=18, max_items=9)
            self._page_troops = [tuple(ids[index] for index in page) for page in pages]
            rows = []
            for number, ident in enumerate(self.visible_troops, 1):
                rows.append(Row(summaries[ids.index(ident)], Button('Choose', width=240, height=40, shortcut=str(number),
                                                                  on_click=lambda ident=ident: self.select(ident)), spacing=24))
            content = Column(introduction, *rows, *footer, spacing=18)
        else:
            if not self.applied:
                self.quote = state.replacement_preview(self.outgoing_id, self.kind)
            quote = self.quote
            old, new = quote.outgoing, quote.incoming
            self.title = 'Replacement completed' if self.applied else 'Review the replacement'
            old_text = Column(label('RETIRE PERMANENTLY', 11, width=520, color=RED),
                              label(f'{UNITS[old.kind].name} #{old.id}', 20, width=520, color=TEXT),
                              label(f'Rank {old.level} · {old.xp} XP · {old.hp}/{old.max_hp} HP', width=520), spacing=10)
            new_text = Column(label('FRESH RECRUIT', 11, width=520, color=GOLD),
                              label(f'{UNITS[new.kind].name} #{new.id}', 20, width=520, color=TEXT),
                              label(f'Rank {new.level} · {new.xp} XP · {new.hp}/{new.max_hp} HP', width=520), spacing=10)
            price = f'{quote.gold} gold · {quote.crystals} crystals · {quote.actions} campaign action'
            content = Column(Row(old_text, new_text, spacing=24), label(self.description),
                             label('No refund, no reserve and no experience transfers. The recruit takes the same army slot.'),
                             label(('Paid: ' if self.applied else 'Cost: ') + price, 15, color=GOLD),
                             label(f'Army upkeep: {quote.upkeep_before} → {quote.upkeep_after} gold per turn.\n'
                                   f'Available: {state.gold} gold · {state.crystals} crystals · {state.actions_left} actions.'),
                             *([label(quote.blocked_reason, 12, color=RED)] if not self.applied and quote.blocked_reason else []),
                             *([label(self.message, 12, color=GOLD)] if self.message else []), spacing=16)
            if not self.applied and not self.message and not quote.blocked_reason:
                content.add(label('Keeping your veteran and resting remains available. Replacing spends an action even with an empty army slot.', 12))
        self.ui.add(content)
        self.panel_height = content.get_preferred_size()[1] + 194
        if self.panel_height > self.game.height - 40:
            raise ValueError(f'Replacement does not fit at {scale:.0%}')
        self.x, self.y = self.game.width / 2 - 560, (self.game.height - self.panel_height) / 2
        self.ui.clear()
        self.ui.add(Column(content, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 94))))
        bottom = self.y + self.panel_height - 68
        self.button('Text size', self.x + 886, self.y + 28, 206, self.open_text_settings, shortcut='T')
        self.button('Codex', self.x + 248, bottom, 176, self.root.codex, shortcut='C')
        self.button('Saves', self.x + 444, bottom, 176, self.browse_saves, hotkey='F6')
        if self.kind is None and self.pages > 1:
            self.button('Previous', self.x + 640, bottom, 150, self.previous_page, hotkey='←', enabled=self.page > 0)
            self.button('Next', self.x + 810, bottom, 150, self.next_page, hotkey='→', enabled=self.page + 1 < self.pages)
        if self.applied:
            self.button('Return to shard', self.x + 28, bottom, 200, self.finish, shortcut=('Enter', 'Esc'), primary=True)
        else:
            self.button('Cancel', self.x + 28, bottom, 200, self.game.pop, shortcut='Esc')
            if self.kind is not None:
                self.button('Replace veteran', self.x + 792, bottom, 300, self.replace_troop,
                            shortcut='Enter', danger=True, enabled=self.quote.blocked_reason is None)

    def replace_troop(self):
        if self.applied:
            return
        try:
            self.root.state.replace_troop(self.outgoing_id, self.kind)
        except RuleError as error:
            self.message = str(error)
            self.game.audio.play_sound('refuse')
        else:
            self.applied = True
            self.game.audio.play_sound('confirm')
            self.message = ''
            self.checkpoint(self.root.state)
        self.refresh()

    def finish(self):
        self.game.clear_and_push(ShardScene(self.root.state))

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message
        self.refresh()

    def load_game(self, slot=1, *, backup=False):
        loaded = super().load_game(slot, backup=backup)
        if not loaded:
            self.refresh()
        return loaded

    def browse_saves(self):
        self.game.push(SaveScene(self.root, mode='save'))

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 210))
        self.box(self.x, self.y, 1120, self.panel_height)
        self.text(self.title, self.x + 28, self.y + 30, size=30, serif=True)
        if self.kind is None and self.pages > 1:
            self.text(f'{self.page + 1}/{self.pages}', self.x + 992, self.y + self.panel_height - 56, size=12, color=MUTED)
