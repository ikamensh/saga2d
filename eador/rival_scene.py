"""The rival's visible orders and finite expedition, using ordinary game UI."""

from saga2d import Anchor, Button, Column, Component, Label, Row

from eador import art
from eador.model import UNITS
from eador.rival import RECRUIT_COSTS
from eador.preferences import reading_scale
from eador.reading import reading_pages
from eador.scene import Screen
from eador.style import GOLD, MUTED, RED, TEAL, TEXT


def rival_order(state):
    rival = state.rival
    if state.status == "victory":
        return "Duskspire has fallen"
    if state.status == "defeat":
        return "The rival holds the shard"
    if state.battle_kind in ("intercept", "defense"):
        return "Expedition in battle"
    target = state.provinces[rival.target].name if rival.target is not None else None
    action = {
        "march": f"March to {target}",
        "attack": f"Attack {target}",
        "return": f"Return via {target}",
        "recruit": "Recruit at Duskspire",
        "recover": "Heal at Duskspire",
        "watch": "Reassess its orders",
        "defeated": "Duskspire has fallen",
    }[rival.intent]
    when = "next turn" if rival.turns_until_action == 1 else f"in {rival.turns_until_action} turns"
    return f"{action} {when}"


class RivalScene(Screen):
    """Read the current expedition and its counterplay without advancing the campaign."""

    transparent = True
    pop_on_cancel = True
    controls = {('left', 'pageup'): 'previous_page', ('right', 'pagedown'): 'next_page'}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.page = 0
        self._page_troops = [tuple(troop.id for troop in root.state.rival.army)]

    @property
    def visible_troops(self):
        """Persistent rival troop IDs in current reading order."""
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

    def refresh(self):
        super().refresh()
        state, rival = self.root.state, self.root.state.rival
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        self.x, self.y = self.game.width / 2 - 560, (self.game.height - 740) / 2
        self._troop_art = []

        def label(text, size=13, *, width=520, color=MUTED, serif=False, scaled=True):
            return Label(text, width=width, wrap=True, font='Georgia' if serif else 'Verdana',
                         font_size=round(size * scale) if scaled else size, text_color=color)

        heading = Column(
            Row(label(f'THE DUSKSPIRE EXPEDITION · {state.rules.title.upper()}', 11, width=854, color=RED),
                Button('Text size', width=186, height=40, shortcut='T', on_click=self.open_text_settings), spacing=24),
            label(rival_order(state), 25, width=1064, color=TEXT, serif=True, scaled=False),
            label(f'At {state.provinces[rival.pos].name} · {len(rival.army)} surviving troops', 12, width=1064), spacing=10)
        footer = label(self.message, 12, width=1064, color=GOLD) if self.message else None
        self.ui.add(Column(heading, *([footer] if footer else [])))
        body_y = self.y + 24 + heading.get_preferred_size()[1] + 20
        bottom = self.y + 672
        footer_y = bottom - 18 - footer.get_preferred_size()[1] if footer else bottom
        available = footer_y - 20 - body_y

        costs = ' / '.join(f'{UNITS[kind].name} {cost}' for kind, cost in RECRUIT_COSTS.items())
        if state.encircled:
            routes = ', '.join(state.provinces[pos].name for pos in state.grid.neighbors((-2, 0)))
            advice = ('Westwatch is encircled: its gold, crystals, Marketplace and rest are blocked. '
                      f'Reclaim any of: {routes}. If gold and income cannot pay upkeep, '
                      'less experienced troops leave first.')
        else:
            advice = (f'After its defeat, the first paid replacement waits {state.rules.replacement_delay} turns. '
                      'Intercept by entering its province, or defend its target. Wounds and casualties persist; '
                      'weakened troops return to Duskspire to pay for recovery. A battle can change its orders.')
        operations = Column(label(f'{rival.gold} gold', 24, color=GOLD, serif=True, scaled=False),
                            label(f'Income +{rival.income(state)} · Upkeep −{rival.upkeep} / turn'),
                            label(f'Refits at Duskspire: {costs} gold. Healing costs 1 gold per health restored.', 11),
                            label(advice), spacing=16)
        self.ui.add(operations)
        if operations.get_preferred_size()[1] > available:
            raise ValueError(f'Rival operations do not fit at {scale:.0%}')
        if rival.army:
            force_heading = label('SURVIVING EXPEDITION', 11, color=RED)
            rows = []
            for troop in rival.army:
                portrait, bar = Component(width=56, height=56), Component(width=452, height=4)
                details = Row(label(UNITS[troop.kind].name, 16, width=274, color=TEXT, serif=True),
                              label(f'{troop.hp}/{troop.max_hp} health', 11, width=166), spacing=12)
                row = Row(portrait, Column(details, bar, spacing=6), spacing=12)
                rows.append(row)
                self._troop_art.append((portrait, bar, troop))
            self.ui.add(Column(force_heading, *rows))
            ids = [troop.id for troop in rival.army]
            anchor = ids.index(self.visible_troops[0]) if self.visible_troops else 0
            packed, self.page = reading_pages([row.get_preferred_size()[1] for row in rows],
                                              available - force_heading.get_preferred_size()[1] - 12,
                                              anchor=anchor, spacing=10)
            self._page_troops = [tuple(ids[index] for index in page) for page in packed]
            visible = packed[self.page]
            self._troop_art = [self._troop_art[index] for index in visible]
            force = Column(force_heading, *(rows[index] for index in visible), spacing=10)
        else:
            self.page, self._page_troops = 0, [()]
            force = Column(label('Its expedition is broken.', 25, color=TEAL, serif=True, scaled=False),
                           label("The rival must buy a new army. Advance on Duskspire while it remusters; "
                                 "the capital's garrison is a separate force.", 14), spacing=16)
            self.ui.add(force)
            if force.get_preferred_size()[1] > available:
                raise ValueError(f'Rival defeat advice does not fit at {scale:.0%}')
        self.ui.clear()
        self.ui.add(Column(heading, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 24))))
        self.ui.add(Column(force, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(body_y))))
        self.ui.add(Column(operations, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 572), round(body_y))))
        if footer:
            self.ui.add(Column(footer, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(footer_y))))
        self.button('Locate expedition', self.x + 28, bottom, 250, self.locate, shortcut='L')
        if self.pages > 1:
            self.button('Previous', self.x + 326, bottom, 150, self.previous_page, hotkey='←', enabled=self.page > 0)
            self.button('Next', self.x + 496, bottom, 150, self.next_page, hotkey='→', enabled=self.page + 1 < self.pages)
        self.button('Close', self.x + 942, bottom, 150, self.game.pop, shortcut='Esc')

    def locate(self):
        self.root.selected = self.root.state.rival.pos
        self.game.pop()

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 215))
        self.box(self.x, self.y, 1120, 740)
        for portrait, bar, troop in self._troop_art:
            x, y, width, height = portrait.bounds
            art.piece(self, x + width / 2, y + height / 2, troop.kind, 'enemy', scale=.72)
            x, y, width, _ = bar.bounds
            self.bar(x, y, width, troop.hp, troop.max_hp, RED)
        if self.pages > 1:
            self.text(f'Force {self.page + 1}/{self.pages}', self.x + 672, self.y + 684, size=12, color=MUTED)
