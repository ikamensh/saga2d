"""Choose the next challenge and traveling retinue, or review a completed journey."""

from eador.campaign import CONTRACTS, FOUNDRIES
from eador.content import RELICS, SKILLS
from eador.model import RuleError, UNITS
from eador.scene import Screen, TitleScene
from eador.style import GOLD, MUTED, RED, TEAL, TEXT
from eador.worldgen import THEMES


def campaign_targets(state):
    """Ordered map labels for the game's current contract and its progress."""
    targets = []
    if state.campaign.contract == 'foundries':
        targets.extend((pos, state.provinces[pos].name, state.provinces[pos].owner == 'player') for pos in FOUNDRIES)
    elif state.campaign.contract == 'rootward':
        watch = next(p for p in state.provinces.values() if p.site_kind == 'border_watch')
        targets.append((watch.pos, f'Border Watch at {watch.name}', watch.explored))
    targets.append(((2, 0), 'Duskspire', state.provinces[(2, 0)].owner == 'player'))
    return targets


class CampaignPlanScene(Screen):
    """Read the current contract and locate its targets without changing campaign progress."""

    transparent = True
    pop_on_cancel = True

    def __init__(self, root):
        super().__init__()
        self.root = root

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def refresh(self):
        from saga2d import Anchor, Button, Column, Label, Row
        from eador.preferences import reading_scale

        super().refresh()
        state, campaign = self.root.state, self.root.state.campaign
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100

        def label(text, size=12, *, width=1064, color=MUTED):
            return Label(text, width=width, wrap=True, font='Verdana',
                         font_size=round(size * scale), text_color=color)

        heading = Column(label(f'YOUR CAMPAIGN · STAGE {campaign.stage} OF 3 · {state.rules.title.upper()}', 11, color=GOLD),
                         Label(campaign.title, width=1064, wrap=True, font='Georgia', font_size=30, text_color=TEXT),
                         label(campaign.objective.replace(' or rout ', '\nor rout '), 14, color=TEXT), spacing=12)
        rows = []
        for index, (pos, name, complete) in enumerate(campaign_targets(state)):
            rows.append(Row(label(f'{index + 1}. {name}', 16, width=600, color=TEAL if complete else TEXT),
                            label('Complete / held' if complete else 'Still required', 11, width=242,
                                  color=TEAL if complete else MUTED),
                            Button('Locate', on_click=lambda pos=pos: self.locate(pos),
                                   shortcut=str(index + 1), width=174, height=40), spacing=24))
        objectives = Column(label('NUMBERED OBJECTIVES ON YOUR MAP', 10, color=GOLD), *rows, spacing=12)
        readiness = label(state.assault_blocked_reason or
                          'Duskspire is open to assault. Prepare your army and protect Westwatch.', color=GOLD)
        travel = Column(label('The final shard' if campaign.stage == 3 else 'Between shards', 13, width=520, color=TEAL),
                        label('Victory completes this three-shard campaign. There is no further departure; '
                              'your earned skills, veterans and relics stay with the completed chronicle.' if campaign.stage == 3 else
                              'After a victory, carry your learned skills, up to two veterans and two relics. '
                              'The new expedition has three troops; unfilled places become fresh Militia. '
                              'Local buildings, holdings and remaining wealth stay on this shard.', width=520), spacing=10)
        gold, crystals = state.expedition_funding(recovery=True)
        limits = Column(label('Rank and recovery', 13, width=520, color=TEAL),
                        label(f'Rank limits this stage: hero {state.hero_level_cap} · troops {state.troop_level_cap}. '
                              'Experience pauses at the limit.', width=520, color=GOLD),
                        label('Recovery spent: another lost capital ends this campaign.' if campaign.recovery_used else
                              f'One recovery remains if Westwatch falls: restart this same world with {gold} gold and {crystals} crystals, '
                              'your learned skills and chosen surviving retinue.', 11, width=520), spacing=10)
        self.ui.add(Column(travel, limits))
        height = max(block.get_preferred_size()[1] for block in (travel, limits))
        rules = Row(*(Column(block, height=height) for block in (travel, limits)), spacing=24)
        content = Column(heading, objectives, readiness, rules, spacing=24)
        self.ui.add(content)
        self.panel_height = content.get_preferred_size()[1] + 120
        if self.panel_height > self.game.height - 40:
            raise ValueError(f'Campaign plan {campaign.title!r} does not fit at {scale:.0%}')
        self.x, self.y = (self.game.width - 1120) / 2, (self.game.height - self.panel_height) / 2
        self.ui.clear()
        self.ui.add(Column(content, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 24))))
        bottom = self.y + self.panel_height - 68
        self.button('Hero & relics', self.x + 28, bottom, 220, self.root.hero_details, shortcut='H')
        self.button('Text size', self.x + 268, bottom, 200, self.open_text_settings, shortcut='T')
        self.button('Return to shard', self.x + 812, bottom, 280, self.game.pop, shortcut='Esc')

    def locate(self, pos):
        self.root.selected = pos
        self.game.pop()

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 225))
        self.box(self.x, self.y, 1120, self.panel_height)


class CampaignScene(Screen):
    """Review a saved transition; reading and retinue selection never spend campaign state."""

    transparent = True
    controls = {'f5': 'save_game', 'f9': 'load_game', 'f6': 'browse_saves',
                'left': 'left', 'right': 'right', 'up': 'up', 'down': 'down', 'space': 'toggle_focused'}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.phase = root.state.campaign.phase
        self.step = 'offers' if self.phase == 'departure' else 'retinue' if self.phase == 'recovery' else 'ending'
        self.offer_id = None
        self.troop_ids, self.relic_ids = set(), set()
        self.column, self.cursors = 0, [0, 0]
        self.visible_items = [(), ()]
        self._item_pages = [[()], [()]]
        self.pages = [0, 0]
        self._prose_anchor = self.prose_page = 0
        self.prose_pages = 1
        self._prose_indices = ((),)
        self._reading_error = False
        self._dismissed_error = None
        self._error_page = 0
        self._error_pages = ()

    @property
    def campaign(self):
        return self.root.state.campaign

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def refresh(self, *, follow_cursor=False):
        from dataclasses import replace
        from saga2d import Anchor, Button, Column, Label, Row, Style
        from eador.preferences import reading_scale
        from eador.reading import reading_pages, reading_text_pages
        from eador.style import PRIMARY

        super().refresh()
        state, campaign = self.root.state, self.campaign
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        self.x, self.y = (self.game.width - 1120) / 2, (self.game.height - 760) / 2
        x, y = self.x + 28, self.y + 24
        bottom = self.y + 696

        def label(text, size=12, *, width=1064, color=MUTED, serif=False, scaled=True):
            return Label(text, width=width, wrap=True, font='Georgia' if serif else 'Verdana',
                         font_size=round(size * scale) if scaled else size, text_color=color)

        def place(block, left, top):
            self.ui.add(Column(block, anchor=Anchor.TOP_LEFT, margin=(round(left), round(top))))

        title = ('Choose the next challenge' if self.step == 'offers' else
                 'Choose your recovery expedition' if self.step == 'retinue' and self.phase == 'recovery' else
                 'Choose who travels with you' if self.step == 'retinue' else
                 'The three shards are free' if self.phase == 'completed' else 'The expedition has ended')
        if self._reading_error:
            title = 'Complete save/load diagnostic'
        heading = Column(label(f'LINKED CAMPAIGN · STAGE {campaign.stage} OF 3 · {state.rules.title.upper()}',
                               10, width=700, color=GOLD),
                         label(title, 29, width=700, serif=True, scaled=False, color=TEXT), spacing=12)
        body_y = y + self.measure(heading)[1] + 20
        place(heading, x, y)
        self.button('Text size', self.x + 754, y, 170, self.open_text_settings, shortcut='T')
        self.button('Saves', self.x + 942, y, 150, self.browse_saves, hotkey='F6')
        if self._reading_error:
            self._error_pages = reading_text_pages(self.message, bottom - body_y - 24,
                                                  measure=lambda text: self.measure(label(text, color=RED))[1])
            self._error_page = min(self._error_page, len(self._error_pages) - 1)
            place(label(self._error_pages[self._error_page], color=RED), x, body_y)
            self.button('Previous', x, bottom, 160, lambda: self.turn_error(-1), shortcut='PageUp', enabled=self._error_page > 0)
            self.button('Next', x + 176, bottom, 160, lambda: self.turn_error(1), shortcut='PageDown',
                        enabled=self._error_page + 1 < len(self._error_pages))
            place(label(f'Page {self._error_page + 1} / {len(self._error_pages)}', 10, width=140), x + 354, bottom + 12)
            self.button('Return to review', self.x + 686, bottom, 406, self.close_error, shortcut=('Enter', 'Esc'))
            return
        shortened_error = self.message and self._dismissed_error == self.message
        error = label('The last save/load attempt failed. Read the complete diagnostic before retrying.'
                      if shortened_error else self.message, 12, color=RED) if self.message else None
        content_bottom = bottom - 18
        if error:
            content_bottom -= self.measure(error)[1] + 16
        blocks = []
        if self.step == 'offers':
            intro = label(f'{campaign.title} is liberated. Your learned skills and selected veterans can cross to the next world.')
            cards = []
            for index, offer in enumerate(campaign.offers):
                cards.append(Column(label(offer.title, 23, width=520, color=TEAL, serif=True, scaled=False),
                                    label(f'{THEMES[offer.theme].name} · Shard {offer.seed}', 11, width=520, color=GOLD),
                                    label(offer.description, 13, width=520, color=TEXT),
                                    Button('Choose challenge', width=520, height=40, style=PRIMARY,
                                           on_click=lambda ident=offer.id: self.choose_offer(ident), shortcut=str(index + 1)), spacing=16))
            height = max(self.measure(card)[1] for card in cards)
            offers = Row(*(Column(card, height=height) for card in cards), spacing=24)
            next_stage = campaign.stage + 1
            army = 'four Dread Guards and two Archers' if next_stage == 3 else 'the usual six-soldier expedition'
            arrival = label(f'The next rival begins with {army}, {90 if next_stage == 3 else 80} gold, '
                            f'and its first operation in {state.rules.arrival_delay} turns. '
                            'It still pays for healing and replacements. Inspect its plan after arrival.', 14)
            carryover = label('Next, choose up to two veterans and two relics. Bring your hero’s skills; build a new local realm. '
                              'Your unselected army stays behind as the liberated shard’s garrison.', 14)
            sections = [intro, offers, arrival, carryover,
                        label('Choose a visible challenge with 1 / 2. You can return to compare before departing.', 12)]
        elif self.step == 'retinue':
            intro = label('Keep up to two veterans and two relics. Unfilled starting troop places become fresh Militia. '
                          'Left/Right changes column; Up/Down browses; Space toggles the focused choice.')
            row_y = body_y + self.measure(intro)[1] + 16
            items = self.items(self.column)
            detail = None
            if items:
                item = items[self.cursors[self.column]]
                detail = label((f'{UNITS[item.kind].name}: level {item.level}, {item.xp} XP. Returns at full health; '
                                f'{UNITS[item.kind].upkeep} gold upkeep per turn.' if self.column == 0 else RELICS[item].description),
                               color=TEAL)
            recovery = self.phase == 'recovery'
            gold, crystals = state.expedition_funding(recovery=recovery)
            offer = next((offer for offer in campaign.offers if offer.id == self.offer_id), None)
            destination = campaign.title if recovery else offer.title
            funding = label(f'{destination} · {gold} gold · {crystals} crystals · '
                            f'{len(self.troop_ids)} veterans + {3 - len(self.troop_ids)} new Militia', 13, color=GOLD)
            rules = label(('One recovery for the whole campaign. Same initial world; buildings and holdings reset. '
                           'Another capital loss ends the run. ' if recovery else 'Buildings, holdings and remaining wealth stay here. ') +
                          'Hero skills survive; traveling health and mana are restored.', 11)
            footer = Column(*([detail] if detail else []), funding, rules, spacing=12)
            footer_y = content_bottom - self.measure(footer)[1]
            blocks.extend(((intro, x, body_y), (footer, x, footer_y)))
            for column in (0, 1):
                items = self.items(column)
                selected = self.troop_ids if column == 0 else self.relic_ids
                ids = [item.id for item in items] if column == 0 else list(items)
                heading_text = ('VETERANS' if column == 0 else 'RELICS') + f' · {len(selected)}/2 KEPT'
                column_heading = label(('› ' if column == self.column else '') + heading_text, 11, width=520, color=GOLD)
                rows = []
                for index, item in enumerate(items):
                    name = (f'{UNITS[item.kind].name} · Lv{item.level} · {item.hp}/{item.max_hp} HP'
                            if column == 0 else RELICS[item].name)
                    style = replace(PRIMARY if ids[index] in selected else Style(), font_size=round(13 * scale))
                    if column == self.column and index == self.cursors[column]:
                        style = replace(style, border_color=GOLD, border_width=2)
                    rows.append(Button(('Keep · ' if ids[index] in selected else 'Leave · ') + name,
                                       width=520, style=style,
                                       on_click=lambda column=column, index=index: self.toggle(column, index)))
                available = footer_y - row_y - self.measure(column_heading)[1] - 12 - 56
                anchor = ids.index(self.visible_items[column][0]) if self.visible_items[column] else 0
                heights = [self.measure(row)[1] for row in rows]
                if error and (available <= 0 or any(height > available for height in heights)):
                    self.open_error()
                    return
                packed, current = reading_pages(heights, available,
                                                anchor=anchor, spacing=10)
                self._item_pages[column] = [tuple(ids[index] for index in page) for page in packed]
                self.pages[column] = current
                visible = packed[current]
                self.visible_items[column] = self._item_pages[column][current]
                if items and self.cursors[column] not in visible:
                    # A larger font or complete error may shorten the anchored page.
                    # Keep Space on a visible row, then measure its actual detail.
                    if follow_cursor and column == self.column:
                        self.visible_items[column] = (ids[self.cursors[column]],)
                    else:
                        self.cursors[column] = visible[0]
                    self.refresh()
                    return
                column_rows = ([rows[index] for index in visible] if items else
                               [label('No survivors available.' if column == 0 else 'No relics owned.', width=520)])
                list_block = Column(column_heading, *column_rows, spacing=10)
                blocks.append((list_block, x + column * 544, row_y))
                if len(packed) > 1:
                    navigation = Row(label(f'Page {current + 1} / {len(packed)}', 10, width=174),
                                     Button('Previous', width=166, height=40, enabled=current > 0,
                                            on_click=lambda column=column: self.page(column, -1)),
                                     Button('Next', width=156, height=40, enabled=current + 1 < len(packed),
                                            on_click=lambda column=column: self.page(column, 1)), spacing=12)
                    blocks.append((navigation, x + column * 544, footer_y - 56))
            sections = None
        else:
            intro = label((('You rebuilt after a lost realm and returned to liberate the worlds.' if campaign.recovery_used else
                            'Your expedition held together from Westwatch to the final stronghold.') if self.phase == 'completed' else
                           'The rival holds Westwatch. This journey ends here; your manual saves remain available.'), 14)
            records = [Column(label(f'{record.stage}. {CONTRACTS[record.contract].title} · {THEMES[record.theme].name}',
                                    22, serif=True, scaled=False, color=TEAL),
                              label(f'{record.turns} turns · Hero level {record.hero_level} · {record.casualties} troops lost · '
                                    f'{len(record.garrison)} left as garrison'), spacing=10) for record in campaign.completed]
            build = ', '.join(f'{SKILLS[ident].name} {rank}' for ident, rank in state.hero.skill_ranks.items()) or 'No disciplines learned'
            sections = [intro, *records,
                        label(f'Level {state.hero.level} {state.hero.hero_class} · {build}', 14),
                        label('Recovery used' if campaign.recovery_used else 'Recovery declined' if self.phase == 'lost'
                                   else 'No recovery needed', color=GOLD)]
        if sections is not None:
            heights = [self.measure(section)[1] for section in sections]
            if error and any(height > content_bottom - body_y for height in heights):
                self.open_error()
                return
            self._prose_indices, self.prose_page = reading_pages(
                heights, content_bottom - body_y,
                anchor=self._prose_anchor, spacing=24)
            self.prose_pages = len(self._prose_indices)
            self._prose_anchor = self._prose_indices[self.prose_page][0]
            blocks.append((Column(*(sections[index] for index in self._prose_indices[self.prose_page]), spacing=24), x, body_y))
        for block, left, top in blocks:
            place(block, left, top)
        if error:
            place(error, x, content_bottom + 16)
        if shortened_error:
            self.button('Read error', self.x + 540, bottom, 130, self.open_error, shortcut='D')
        if self.step != 'retinue' and self.prose_pages > 1:
            self.button('Previous', x, bottom, 160, lambda: self.turn_prose(-1), shortcut='PageUp', enabled=self.prose_page > 0)
            self.button('Next', x + 176, bottom, 160, lambda: self.turn_prose(1), shortcut='PageDown',
                        enabled=self.prose_page + 1 < self.prose_pages)
            place(label(f'Page {self.prose_page + 1} / {self.prose_pages}', 10, width=140), x + 354, bottom + 12)
        if self.step == 'retinue':
            if self.phase == 'departure':
                self.button('Other challenge', x, bottom, 236, self.back, shortcut='Esc')
            else:
                self.button('End this campaign', x, bottom, 282, self.abandon, shortcut='Q', danger=True)
            self.button('Launch recovery' if self.phase == 'recovery' else 'Depart for the next shard',
                        self.x + 686, bottom, 406, self.depart, shortcut='Enter', primary=True)
        elif self.step == 'ending':
            self.button('Return to title', self.x + 686, bottom, 406, self.to_title, shortcut='Enter', primary=True)

    def open_error(self):
        self._reading_error = True
        self._error_page = 0
        self.refresh()

    def turn_error(self, direction):
        page = self._error_page + direction
        if 0 <= page < len(self._error_pages):
            self._error_page = page
            self.refresh()

    def close_error(self):
        self._reading_error = False
        self._dismissed_error = self.message
        self.refresh()

    def turn_prose(self, direction):
        page = self.prose_page + direction
        if 0 <= page < self.prose_pages:
            self._prose_anchor = self._prose_indices[page][0]
            self.refresh()

    def choose_offer(self, ident):
        self.offer_id, self.step = ident, 'retinue'
        self.message = ''
        self.refresh()

    def back(self):
        self.step = 'offers'
        self._prose_anchor = 0
        self.refresh()

    def items(self, column):
        return self.root.state.hero.army if column == 0 else self.root.state.inventory

    def left(self):
        if self._reading_error:
            self.turn_error(-1)
            return
        self.column = 0
        self.refresh()

    def right(self):
        if self._reading_error:
            self.turn_error(1)
            return
        self.column = 1
        self.refresh()

    def shift(self, direction):
        items = self.items(self.column)
        if self.step == 'retinue' and not self._reading_error and items:
            self.cursors[self.column] = (self.cursors[self.column] + direction) % len(items)
            item = items[self.cursors[self.column]]
            ident = item.id if self.column == 0 else item
            if ident not in self.visible_items[self.column]:
                self.visible_items[self.column] = (ident,)
            self.refresh(follow_cursor=True)

    def up(self):
        self.shift(-1)

    def down(self):
        self.shift(1)

    def toggle_focused(self):
        if self.step == 'retinue' and not self._reading_error and self.items(self.column):
            self.toggle(self.column, self.cursors[self.column])

    def page(self, column, direction):
        page = self.pages[column] + direction
        if 0 <= page < len(self._item_pages[column]):
            self.column = column
            self.visible_items[column] = self._item_pages[column][page]
            ids = [item.id for item in self.items(column)] if column == 0 else self.items(column)
            self.cursors[column] = ids.index(self.visible_items[column][0])
            self.refresh()

    def toggle(self, column, index):
        self.column, self.cursors[column] = column, index
        item = self.items(column)[index]
        selected, ident = (self.troop_ids, item.id) if column == 0 else (self.relic_ids, item)
        if ident in selected:
            selected.remove(ident)
        elif len(selected) < 2:
            selected.add(ident)
        else:
            self.message = 'Choose at most two veterans and two relics. Remove one before selecting another.'
            self.game.audio.play_sound('refuse')
            self.refresh()
            return
        self.message = ''
        self.refresh(follow_cursor=True)

    def depart(self):
        state = self.root.state
        if not self.checkpoint(state):
            self.refresh()
            return
        # Preserve roster/inventory order so equipment fallback and saved travel are deterministic.
        selection = dict(troop_ids=tuple(t.id for t in state.hero.army if t.id in self.troop_ids),
                         relic_ids=tuple(rid for rid in state.inventory if rid in self.relic_ids))
        try:
            if self.phase == 'recovery':
                state.recover(**selection)
            else:
                state.advance(self.offer_id, **selection)
        except RuleError as error:
            self.message = str(error)
            self.game.audio.play_sound('refuse')
            self.refresh()
            return
        self.game.audio.play_sound('confirm')
        if not self.checkpoint(state):
            self.root.message = 'Arrived. Pre-departure save is intact; autosave failed. F5 or F6 saves this new shard.'
        self.game.pop()

    def abandon(self):
        if self.checkpoint(self.root.state):
            self.root.state.abandon_campaign()
            self.checkpoint(self.root.state)
            self.phase, self.step = 'lost', 'ending'
            self.game.audio.play_sound('defeat')
        self.refresh()

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message
        self.refresh()

    def load_game(self, slot=1, *, backup=False):
        if super().load_game(slot, backup=backup):
            return True
        self.refresh()
        return False

    def browse_saves(self):
        self.root.browse_saves()

    def to_title(self):
        state = self.root.state
        self.game.clear_and_push(TitleScene(state.campaign.seed + 1, hero_class=state.hero.hero_class,
                                           difficulty=state.difficulty))

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 232))
        self.box(self.x, self.y, 1120, 760)
