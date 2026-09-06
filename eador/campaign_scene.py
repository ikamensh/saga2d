"""Choose the next challenge and traveling retinue, or review a completed journey."""

import textwrap

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
    transparent = True
    pop_on_cancel = True

    def __init__(self, root):
        super().__init__()
        self.root = root

    def refresh(self):
        super().refresh()
        self.x, self.y = (self.game.width - 900) / 2, (self.game.height - 660) / 2
        for index, (pos, _, _) in enumerate(campaign_targets(self.root.state)):
            self.button('Locate', self.x + 698, self.y + 188 + index * 52, 174,
                        lambda pos=pos: self.locate(pos), shortcut=str(index + 1))
        self.button('Return to shard', self.x + 592, self.y + 590, 280, self.game.pop, shortcut='Esc')
        self.button('Hero & relics', self.x + 28, self.y + 590, 220, self.root.hero_details, shortcut='H')

    def locate(self, pos):
        self.root.selected = pos
        self.game.pop()

    def draw(self):
        x, y, state = self.x, self.y, self.root.state
        campaign = state.campaign
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 225))
        self.box(x, y, 900, 660)
        self.text(f'YOUR CAMPAIGN · STAGE {campaign.stage} OF 3', x + 28, y + 24, size=11, color=GOLD)
        self.text(campaign.title, x + 28, y + 52, size=30, serif=True)
        self.paragraph(campaign.objective, x + 28, y + 104, width=844, size=14, color=TEXT)
        self.text('NUMBERED OBJECTIVES ON YOUR MAP', x + 28, y + 166, size=10, color=GOLD)
        for index, (_, label, complete) in enumerate(campaign_targets(state)):
            self.text(f'{index + 1}. {label}', x + 28, y + 192 + index * 52, size=16,
                      color=TEAL if complete else TEXT)
            self.text('Complete / held' if complete else 'Still required', x + 501, y + 198 + index * 52,
                      size=11, color=TEAL if complete else MUTED)
        self.paragraph(state.assault_blocked_reason or 'Duskspire is open to assault. Prepare your army and protect Westwatch.',
                       x + 28, y + 360, width=844, size=12, color=GOLD)
        self.rule(x + 28, y + 406, 844)
        self.paragraph('After a victory, carry your learned skills, up to two veterans and two relics. '
                       'The new expedition has three troops; unfilled places become fresh Militia. '
                       'Local buildings, holdings and remaining wealth stay on this shard.',
                       x + 28, y + 428, width=844, size=12)
        self.text(f'Rank limits this stage: hero {state.hero_level_cap} · troops {state.troop_level_cap}. '
                  'Experience pauses at the limit.', x + 28, y + 506, size=12, color=GOLD)
        self.paragraph('Recovery spent: another lost capital ends this campaign.' if campaign.recovery_used else
                       'One recovery remains if Westwatch falls: restart this same world with 60 gold and two crystals, '
                       'your learned skills and chosen surviving retinue.', x + 28, y + 538, width=844, size=11)


class CampaignScene(Screen):
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

    @property
    def campaign(self):
        return self.root.state.campaign

    def refresh(self):
        super().refresh()
        self.x, self.y = (self.game.width - 1080) / 2, (self.game.height - 700) / 2
        x, y = self.x, self.y
        self.button('Saves', x + 896, y + 22, 156, self.browse_saves, hotkey='F6')
        if self.step == 'offers':
            for index, offer in enumerate(self.campaign.offers):
                self.button('Choose challenge', x + 36 + index * 522, y + 347, 486,
                            lambda ident=offer.id: self.choose_offer(ident), shortcut=str(index + 1), primary=True)
        elif self.step == 'retinue':
            for column in (0, 1):
                items = self.items(column)
                start = self.cursors[column] // 6 * 6
                for index in range(start, min(len(items), start + 6)):
                    item = items[index]
                    selected = item.id in self.troop_ids if column == 0 else item in self.relic_ids
                    name = f'{UNITS[item.kind].name} · Lv{item.level} · {item.hp}/{item.max_hp} HP' if column == 0 else RELICS[item].name
                    self.button(('Keep · ' if selected else 'Leave · ') + name,
                                x + 36 + column * 522, y + 172 + (index - start) * 50, 486,
                                lambda column=column, index=index: self.toggle(column, index), primary=selected)
                if len(items) > 6:
                    self.button('Previous', x + 258 + column * 522, y + 465, 142,
                                lambda column=column: self.page(column, -1), enabled=start > 0)
                    self.button('Next', x + 411 + column * 522, y + 465, 111,
                                lambda column=column: self.page(column, 1), enabled=start + 6 < len(items))
            if self.phase == 'departure':
                self.button('Other challenge', x + 36, y + 634, 236, self.back, shortcut='Esc')
            else:
                self.button('End this campaign', x + 36, y + 634, 282, self.abandon, shortcut='Q', danger=True)
            self.button('Launch recovery' if self.phase == 'recovery' else 'Depart for the next shard',
                        x + 638, y + 634, 406, self.depart, shortcut='Enter', primary=True)
        else:
            self.button('Return to title', x + 638, y + 634, 406, self.to_title, shortcut='Enter', primary=True)

    def choose_offer(self, ident):
        self.offer_id, self.step = ident, 'retinue'
        self.message = ''
        self.refresh()

    def back(self):
        self.step = 'offers'
        self.refresh()

    def items(self, column):
        return self.root.state.hero.army if column == 0 else self.root.state.inventory

    def left(self):
        self.column = 0
        self.refresh()

    def right(self):
        self.column = 1
        self.refresh()

    def shift(self, direction):
        items = self.items(self.column)
        if self.step == 'retinue' and items:
            self.cursors[self.column] = (self.cursors[self.column] + direction) % len(items)
            self.refresh()

    def up(self):
        self.shift(-1)

    def down(self):
        self.shift(1)

    def toggle_focused(self):
        if self.step == 'retinue' and self.items(self.column):
            self.toggle(self.column, self.cursors[self.column])

    def page(self, column, direction):
        self.column = column
        self.cursors[column] = min(len(self.items(column)) - 1, max(0, self.cursors[column] + direction * 6))
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
            return
        self.message = ''
        self.refresh()

    def depart(self):
        state = self.root.state
        if not self.checkpoint(state):
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
            return
        self.game.audio.play_sound('confirm')
        if not self.checkpoint(state):
            self.root.message = self.message + ' Your pre-departure snapshot remains available in Saves.'
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

    def browse_saves(self):
        self.root.browse_saves()

    def to_title(self):
        state = self.root.state
        self.game.clear_and_push(TitleScene(state.campaign.seed + 1, hero_class=state.hero.hero_class))

    def draw(self):
        x, y, state, campaign = self.x, self.y, self.root.state, self.campaign
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 232))
        self.box(x, y, 1080, 700)
        self.text(f'LINKED CAMPAIGN · STAGE {campaign.stage} OF 3', x + 36, y + 25, size=11, color=GOLD)
        title = ('Choose the next challenge' if self.step == 'offers' else
                 'Choose your recovery expedition' if self.phase == 'recovery' else
                 'Choose who travels with you' if self.step == 'retinue' else
                 'The three shards are free' if self.phase == 'completed' else 'The expedition has ended')
        self.text(title, x + 36, y + 54, size=29, serif=True)
        if self.step == 'offers':
            self.paragraph(f'{campaign.title} is liberated. Your learned skills and selected veterans can cross to the next world.',
                           x + 36, y + 105, width=1008, size=12)
            for index, offer in enumerate(campaign.offers):
                left = x + 36 + index * 522
                self.box(left, y + 150, 486, 182)
                self.text(offer.title, left + 20, y + 168, size=23, serif=True, color=TEAL)
                self.text(f'{THEMES[offer.theme].name} · Shard {offer.seed}', left + 20, y + 204, size=11, color=GOLD)
                self.paragraph(offer.description, left + 20, y + 233, width=446, size=13, color=TEXT)
            next_stage = campaign.stage + 1
            army = 'four Dread Guards and two Archers' if next_stage == 3 else 'the usual six-soldier expedition'
            self.paragraph(f'The next rival begins with {army}, {90 if next_stage == 3 else 80} gold, and a two-turn first warning. '
                           'It still pays for healing and replacements. Inspect its plan after arrival.',
                           x + 36, y + 421, width=1008, size=14)
            self.paragraph('Next, choose up to two veterans and two relics. Bring your hero’s skills; build a new local realm. '
                           'Your unselected army stays behind as the liberated shard’s garrison.',
                           x + 36, y + 510, width=1008, size=14)
            self.text('1 / 2 chooses a challenge. You can return to compare before departing.', x + 36, y + 641, size=12, color=MUTED)
        elif self.step == 'retinue':
            self.paragraph('Keep up to two veterans and two relics. Unfilled starting troop places become fresh Militia. '
                           'Left/Right changes column; Up/Down browses; Space toggles the focused choice.',
                           x + 36, y + 101, width=1008, size=12)
            for column, label in ((0, f'VETERANS · {len(self.troop_ids)}/2 KEPT'), (1, f'RELICS · {len(self.relic_ids)}/2 KEPT')):
                left = x + 36 + column * 522
                self.text(label, left, y + 145, size=11, color=GOLD)
                items = self.items(column)
                if not items:
                    self.text('No survivors available.' if column == 0 else 'No relics owned.', left + 16, y + 190, color=MUTED)
                if column == self.column and items:
                    self.text('›', left - 21, y + 175 + (self.cursors[column] % 6) * 50, size=21, color=GOLD)
                if len(items) > 6:
                    self.text(f'Page {self.cursors[column] // 6 + 1} / {(len(items) + 5) // 6}',
                              left, y + 479, size=10, color=MUTED)
            items = self.items(self.column)
            if items:
                item = items[self.cursors[self.column]]
                detail = (f'{UNITS[item.kind].name}: level {item.level}, {item.xp} XP. Returns at full health; '
                          f'{UNITS[item.kind].upkeep} gold upkeep per turn.' if self.column == 0 else RELICS[item].description)
                self.paragraph(detail, x + 36, y + 516, width=1008, size=12, color=TEAL)
            recovery = self.phase == 'recovery'
            gold, crystals = (60, 2) if recovery else (100 + min(40, state.gold), 4 + min(2, state.crystals))
            offer = next((offer for offer in campaign.offers if offer.id == self.offer_id), None)
            destination = campaign.title if recovery else offer.title
            self.text(f'{destination} · {gold} gold · {crystals} crystals · {len(self.troop_ids)} veterans + {3 - len(self.troop_ids)} new Militia',
                      x + 36, y + 553, size=13, color=GOLD)
            self.paragraph(('One recovery for the whole campaign. Same initial world; buildings and holdings reset. Another capital loss ends the run. '
                            if recovery else 'Buildings, holdings and remaining wealth stay here. ') +
                           'Hero skills survive; traveling health and mana are restored.',
                           x + 36, y + 581, width=1008, size=11)
        else:
            self.paragraph(('You rebuilt after a lost realm and returned to liberate the worlds.' if campaign.recovery_used else
                            'Your expedition held together from Westwatch to the final stronghold.') if self.phase == 'completed' else
                           'The rival holds Westwatch. This journey ends here; your manual saves remain available.',
                           x + 36, y + 111, width=1008, size=14)
            for index, record in enumerate(campaign.completed):
                top = y + 196 + index * 94
                self.text(f'{record.stage}. {CONTRACTS[record.contract].title} · {THEMES[record.theme].name}', x + 36, top, size=22, serif=True, color=TEAL)
                self.text(f'{record.turns} turns · Hero level {record.hero_level} · {record.casualties} troops lost · {len(record.garrison)} left as garrison',
                          x + 36, top + 37, size=12, color=MUTED)
            build = ', '.join(f'{SKILLS[ident].name} {rank}' for ident, rank in state.hero.skill_ranks.items()) or 'No disciplines learned'
            self.paragraph(f'Level {state.hero.level} {state.hero.hero_class} · {build}', x + 36, y + 500, width=1008, size=14)
            self.text('Recovery used' if campaign.recovery_used else 'Recovery declined' if self.phase == 'lost' else 'No recovery needed',
                      x + 36, y + 550, size=12, color=GOLD)
        if self.message:
            self.text(textwrap.shorten(self.message, width=133, placeholder='…'),
                      x + 36, y + 611, size=10, color=RED)
