"""Two campaign seats share a day, while each keeps its own screen and PvE battle."""
from saga2d import Anchor, Column, Label, Row, CommandError
from eador import art
from eador.concurrent_view import ConcurrentView
from eador.model import UNITS, RuleError
from eador.preferences import load_preferences, reading_scale
from eador.scene import ShardScene, Screen, OrderPending, CatalogScene, HeroScene, BattleScene, ChoiceScene
from eador.style import GOLD, INK, LINE, MUTED, PANEL, RED, TEAL, TEXT
from eador.ui import metric


class ConcurrentShardScene(ShardScene):
    live_match = True

    def __init__(self, session, match=None):
        self.session = session
        self._revision = session.revision
        self._pending = None
        super().__init__(ConcurrentView.from_snapshot(session.state))

    @property
    def battle_team(self):
        return self.state.battle_team

    def on_enter(self):
        self.preferences = load_preferences(self.game)
        Screen.on_enter(self)
        self.every(1 / 30, self._poll)
        self.follow_state()

    def on_close(self):
        self.session.close()

    def on_reveal(self):
        self.refresh()
        self.follow_state()

    def follow_state(self):
        from eador.sound import set_music
        if self.game.scene is not self:
            return
        s = self.state
        set_music(self.game, 'battle' if s.battle and not s.battle.outcome else
                  None if s.battle or s.status != 'playing' else 'campaign')
        if s.battle is not None:
            self.game.push(BattleScene(self))
        elif s.choice is not None:
            self.game.push(ChoiceScene(self))
        elif s.status != 'playing':
            self.game.push(CampaignOutcome(self))

    def show_battle_result(self):
        if not isinstance(self.game.scene, CampaignOutcome):
            self.game.push(CampaignOutcome(self, battle=True))

    def _return_to_map(self):
        self.game.pop_to(self)
        self.follow_state()

    def _reconcile(self, trace):
        from eador.encounter_scene import EncounterScene
        from eador.replacement_scene import ReplacementScene
        top, s = self.game.scene, self.state
        if s.battle is not None:
            if isinstance(top, BattleScene):
                top.message = ''
                top.refresh()
                if trace and trace.events:
                    top.begin_playback(trace)
                elif s.battle.outcome:
                    self.show_battle_result()
            elif not isinstance(top, CampaignOutcome) or not s.battle.outcome:
                self._return_to_map()
        elif s.choice is not None:
            if isinstance(top, ChoiceScene):
                top.message = ''
                top.refresh()
            else:
                self._return_to_map()
        elif isinstance(top, (BattleScene, ChoiceScene, CampaignOutcome, EncounterScene)):
            self._return_to_map()
        elif s.status != 'playing':
            self._return_to_map()
        elif isinstance(top, ReplacementScene):
            if top.outgoing_id is not None and not any(t.id == top.outgoing_id for t in s.hero.army):
                self._return_to_map()
            else:
                top.message = ''
                top.refresh()
        elif isinstance(top, (CatalogScene, HeroScene)):
            top.message = ''
            top.refresh()

    def _poll(self):
        from eador.battle_playback_scene import BattlePlaybackScene
        from eador.encounter_scene import EncounterScene
        from eador.replacement_scene import ReplacementScene
        self.session.poll()
        if self.session.error:
            self.message = self.session.error
            self.session.error = ''
            self._pending = None
            if isinstance(self.game.scene, (BattleScene, CatalogScene, HeroScene, ChoiceScene,
                                            CampaignOutcome, EncounterScene, ReplacementScene)):
                self.game.scene.message = self.message
                self.game.scene.refresh()
        if self._revision == self.session.revision:
            return
        previous = self.state
        changed = self.session.state['realm']['revision'] != previous.revision
        # Keep Help/settings and accepted playback intact. The socket continues
        # receiving; a later tick applies its latest state when the reader returns.
        if changed and (isinstance(self.game.scene, BattlePlaybackScene) or not isinstance(
                self.game.scene, (ConcurrentShardScene, BattleScene, CatalogScene, HeroScene,
                                  ChoiceScene, CampaignOutcome, EncounterScene, ReplacementScene))):
            return
        next_state = ConcurrentView.from_snapshot(self.session.state)
        trace = None
        if not changed:
            if (next_state.provinces == previous.provinces and next_state.opponent == previous.opponent
                    and next_state.claims == previous.claims and next_state.encounter == previous.encounter):
                self._revision = self.session.revision
                return
            next_state.battle = previous.battle
        elif self._pending:
            command, preview, proposed_trace = self._pending
            if (next_state.battle and next_state.revision == command['realm_revision'] + 1
                    and preview == next_state.battle.to_dict()):
                trace = proposed_trace
        self.state = next_state
        self._revision = self.session.revision
        if changed:
            self._pending = None
            self.message = ''
            if previous.hero.pos != self.state.hero.pos:
                self.selected = self.state.hero.pos
        self.refresh()
        if changed:
            self._reconcile(trace)

    def order(self, action, *args, target='state', **kwargs):
        if self._pending is not None:
            raise RuleError('Wait for the previous order to arrive.')
        command = {'day': self.state.day, 'realm_revision': self.state.revision,
                   'action': 'battle.' + action if target == 'battle' else action,
                   'args': list(args), 'kwargs': kwargs}
        preview, trace = None, None
        try:
            if target == 'battle' and self.state.battle:
                from eador.battle import Battle
                from eador.orders import invoke_order
                detached = Battle.from_dict(self.state.battle.to_dict())
                trace = detached.trace(lambda: invoke_order(detached, action, list(args), kwargs))
                preview = detached.to_dict()
            self.session.submit(command)
        except CommandError as error:
            raise RuleError(str(error)) from error
        self._pending = command, preview, trace
        raise OrderPending('Order sent.')

    def help(self):
        from eador.diagnostics import DiagnosticScene
        self.game.push(DiagnosticScene(
            'Two realms, one shard. Capture the opposing capital while protecting your own.\n\n'
            'Build and recruit independently. Travel and exploration spend your campaign actions. '
            'Both players can fight their own ordinary PvE battles at the same time.\n\n'
            'Ready (E) commits your day. Income, upkeep and recovery happen once both realms are ready. '
            'Finish your battle and reward choices first.\n\n'
            'When armies meet, each player takes an ordinary tactical turn. '
            'A province already in combat can be challenged: pay one travel action and wait for its '
            'battle and choices to finish. Withdrawing does not refund that action.\n\n'
            'Tab selects nearby provinces; Enter travels; X explores; B builds; R recruits; H opens your hero.\n\n'
            'In battle, Tab selects an ally; click a hex to move or attack. G guards; 1 and 2 prepare spells; '
            'F cycles targets and Enter acts. E ends your tactical phase; L reads the battle log; T retreats. '
            'Space finishes an animation. Human battles have no autoplay.\n\n'
            'Online rooms can be rejoined from Multiplayer. LAN play lasts while its host stays open.',
            title='Campaign PvP', return_label='Return to game', body_color=TEXT))

    def save_game(self):
        self.message = ('The online authority saves this room. Rejoin through Multiplayer.'
                        if getattr(self.session, 'online', False) else
                        'This LAN shard stays on its host. Keep the host open to continue.')

    def load_game(self, slot=1, *, backup=False):
        self.save_game()
        return False

    def browse_saves(self, mode='load'):
        self.save_game()
        self.refresh()

    def end_turn(self):
        self.command(lambda: self.order('ready'))

    def travel(self):
        self.command(lambda: self.order('challenge' if self.contested else 'travel', self.selected))

    @property
    def contested(self):
        s = self.state
        return (s.claims.get(self.selected) == 1 - s.seat
                or self.selected == tuple(s.opponent['hero_pos'])
                and (s.opponent['in_battle'] or s.opponent['choosing']))

    def withdraw(self):
        self.command(lambda: self.order('withdraw'))

    def refresh(self):
        Screen.refresh(self)
        s, h, x, width = self.state, self.game.height, self.edge + 22, 356
        scale = reading_scale(self.game) / 100
        self._display = self.game.window_size, reading_scale(self.game), self.message

        def label(text, width=width, size=12, color=TEXT, serif=False):
            return Label(text, width=width, wrap=True, font='Georgia' if serif else 'Verdana',
                         font_size=round(size * scale), text_color=color)

        def block(content, left, top, width=width, *, spacing=8):
            column = Column(*content, width=width, spacing=spacing, anchor=Anchor.TOP_LEFT,
                            margin=(round(left), round(top)))
            height = self.measure(column)[1]
            self.ui.add(column)
            return top + height

        from eador.worldgen import THEMES
        block([label(f'CAMPAIGN PvP · {THEMES[s.theme].name.upper()} · SHARD {s.seed}', 700, 11, GOLD)], 26, 65, 700)
        for index, (icon, title, action, key) in enumerate((
                ('guide', 'Guide', self.help, 'F1'), ('hero', 'Hero', self.hero_details, 'H'),
                ('codex', 'Codex', self.codex, 'C'), ('text_size', 'Text size', self.open_text_settings, 'F2'))):
            self.icon_button(icon, title, 878 + index * 90, 26, action, shortcut=key)
        production = s.production
        economy_bottom = block([
            label('YOUR REALM' if not production.encircled else 'CAPITAL ENCIRCLED', 402, 10, MUTED),
            Row(metric('gold', s.gold, width=110, size=16 * scale, color=GOLD),
                metric('crystals', s.crystals, width=80, size=16 * scale, color=TEAL),
                metric('income', f'+{production.gold}', width=92, size=12 * scale),
                metric('upkeep', f'−{s.upkeep}', width=92, size=12 * scale), spacing=8),
            label(f'Day {s.day} · ' + ('Ready' if s.ready else 'Orders open'), 402, 11, GOLD),
        ], 26, 108, 402)
        hero_bottom = block([
            label(f'{s.hero.name}, the {s.hero.hero_class}', 402, 16, TEXT, True),
            Row(metric('health', f'{s.hero.hp}/{s.hero.max_hp}', width=142, size=12 * scale, color=TEAL),
                metric('mana', f'{s.hero.mana}/{s.hero.max_mana}', width=142, size=12 * scale),
                metric('actions', s.actions_left, width=100, size=12 * scale, color=GOLD), spacing=8),
            label('At ' + s.provinces[s.hero.pos].name, 402, 11, MUTED),
        ], 452, 108, 402)
        self._summary_bottom = max(economy_bottom, hero_bottom) + 18
        province = s.provinces[self.selected]
        owners = {'player': 'YOUR PROVINCE', 'rival': 'OPPOSING PROVINCE', 'neutral': 'UNCLAIMED PROVINCE'}
        details = [label(owners[province.owner], size=10, color=art.OWNERS[province.owner]),
                   label(province.name, size=22, serif=True),
                   Row(label(province.terrain.title(), 206, 11, MUTED),
                       metric('income', f'+{province.income}', width=138, size=11 * scale), spacing=12)]
        if province.guards and province.owner != 'player':
            from collections import Counter
            defenders = ', '.join(f'{count} {UNITS[kind].name}' for kind, count in Counter(province.guards).items())
            details.append(label('Defenders: ' + defenders, size=11, color=RED))
        if province.site:
            details.append(label(province.site + (' · cleared' if province.explored else ''), size=11,
                                 color=MUTED if province.explored else GOLD))
        claim = s.claims.get(self.selected)
        if claim is not None:
            details.append(label('Your battle here' if claim == s.seat else 'Opponent is fighting here', color=RED))
        y = block(details, x, 108) + 18
        active = s.status == 'playing' and not s.ready and not s.waiting
        adjacent = self.selected in s.grid.neighbors(s.hero.pos)
        self._travel_destination = self.selected if active and s.actions_left and adjacent else None
        if self.selected != s.hero.pos:
            self.button('Wait and attack' if self.contested else
                        'Attack opposing army' if self.selected == tuple(s.opponent['hero_pos']) else
                        'Travel here' if province.owner == 'player' else 'Invade province', x, y, width,
                        self.travel, hotkey='Enter', primary=True, icon='travel',
                        enabled=bool(self._travel_destination),
                        tooltip='Commit one travel action; fight after the incumbent finishes its battle and choices.'
                        if self.contested else 'Travel to the selected adjacent province. Spends one action.')
            y += 54
        current = s.provinces[s.hero.pos]
        self.button('Explore current province', x, y, width, self.explore, hotkey='X', icon='explore',
                    enabled=active and s.actions_left > 0 and current.owner == 'player'
                    and current.site is not None and not current.explored)
        y += 60
        self.button('Build stronghold', x, y, 170, self.buildings, hotkey='B', icon='build',
                    show_text=False, enabled=active)
        self.button('Recruit troops', x + 186, y, 170, self.recruitment, hotkey='R', icon='recruit',
                    show_text=False, enabled=active)
        y += 64
        peer = s.opponent
        status = ('Ready' if peer['ready'] else 'In battle' if peer['in_battle'] else
                  'Choosing a reward' if peer['choosing'] else 'Planning')
        details = [label('OPPOSING REALM', size=10, color=MUTED), label(status, color=RED),
               label('Capture ' + s.provinces[tuple(peer['capital'])].name, size=14, color=GOLD, serif=True),
               label('Protect ' + s.provinces[s.capital].name, size=11, color=MUTED)]
        if s.waiting:
            destination = s.provinces[tuple(s.encounter['destination'])].name
            details.append(label('Waiting to enter ' + destination + '. Your travel action is already paid.', size=11, color=GOLD))
        block(details, x, y)
        if s.waiting:
            self.button('Withdraw challenge', x, h - 66, width, self.withdraw, shortcut='W',
                        icon='retreat', tooltip='Release the challenge. The committed travel action is not refunded.')
        else:
            self.button('Ready' if not s.ready else 'Waiting for opponent', x, h - 66, width,
                        self.end_turn, hotkey='E', primary=True, icon='end_turn', enabled=active,
                        tooltip='Commit your day. Both players must be ready before income, upkeep and rest.')
        army_top = h - 158
        from saga2d import HexGrid
        self.grid = HexGrid(s.provinces, size=min(59, (army_top - self._summary_bottom - 24) / 8),
                            origin=(self.edge / 2, (self._summary_bottom + army_top) / 2))
        self._territory_borders = art.territory_borders(self.grid, s.provinces)
        self._province_name_boxes = []
        for pos in (s.capital, tuple(peer['capital'])):
            cx, cy = self.grid.center(pos)
            name = Label(s.provinces[pos].name, font='Verdana', font_size=9, text_color=TEXT)
            name_width, name_height = self.measure(name)
            left, top = round(cx - name_width / 2), round(cy + self.grid.size * .60 - name_height)
            self.ui.add(Column(name, anchor=Anchor.TOP_LEFT, enabled=False, margin=(left, top)))
            self._province_name_boxes.append((left - 5, top - 1, name_width + 10, name_height + 2))
        self._hover_name = None
        self._update_hover_label()
        block([label(f'YOUR ARMY · {len(s.hero.army)}/{s.hero.max_army}', self.edge - 52, 10, MUTED)],
              26, army_top, self.edge - 52)
        self._army_art, self._army_cards = [], []
        army_y = army_top + round(22 * scale)
        for index, troop in enumerate(s.hero.army):
            xx = 30 + index * 128
            name_bottom = block([label(UNITS[troop.kind].name, 112, 11)], xx, army_y, 112)
            bottom = block([metric('level', troop.level, width=76, size=10 * scale, color=MUTED),
                            metric('health', f'{troop.hp}/{troop.max_hp}', width=76, size=10 * scale, color=TEAL)],
                           xx + 36, name_bottom + 4, 76, spacing=3)
            self._army_art.append((xx, name_bottom + 38, bottom + 3))
            self._army_cards.append((xx - 5, army_y - 5, 122, bottom - army_y + 17))
        notice = self.message or ('Connection paused — waiting for the other player.' if not self.session.ready else s.log[-1])
        self._notice = notice
        reading = label(notice, self.edge - 52, 10, GOLD if self.message else MUTED)
        if self.measure(reading)[1] > 26:
            reading = label('New campaign message', self.edge - 250, 10, GOLD)
            self.button('Read message', self.edge - 212, h - 49, 186, self.read_message, shortcut='D')
        block([reading], 26, h - 30, self.measure(reading)[0])

    def draw_content(self):
        s, h = self.state, self.game.height
        art.backdrop(self, self.edge, h)
        self.draw_rect(self.edge, 91, self.game.width - self.edge, h - 91, PANEL)
        self.draw_line(self.edge, 91, self.edge, h, LINE)
        self.draw_rect(0, 0, self.game.width, 91, INK)
        self.rule(24, 90, self.game.width - 48)
        self.text('SHARDBOUND', 26, 22, size=27, serif=True)
        self.rule(26, self._summary_bottom - 4, self.edge - 52)
        for pos in sorted(s.provinces, key=lambda cell: self.grid.center(cell)[1]):
            art.province(self, self.grid, pos, s.provinces[pos], selected=pos == self.selected,
                         hero=pos == s.hero.pos, hover=pos == self.hover, name_label=False)
        for start, end, color in self._territory_borders:
            self.draw_line(*start, *end, color, 1.5)
        if self._travel_destination is not None:
            art.travel_arrow(self, self.grid, s.hero.pos, self._travel_destination)
        for box in self._province_name_boxes:
            self.draw_rect(*box, (23, 37, 33, 235), radius=3)
        pos = tuple(s.opponent['hero_pos'])
        art.hero_banner(self, self.grid, pos, color=RED)
        art.compass(self, 75, self._summary_bottom + 60)
        for box in self._army_cards:
            self.draw_rect(*box, (17, 29, 33, 220), border_color=LINE, border_width=.5, radius=4)
        for troop, (x, y, bar_y) in zip(s.hero.army, self._army_art):
            art.piece(self, x + 19, y, troop.kind, 'player', scale=.53)
            self.bar(x + 42, bar_y, 66, troop.hp, troop.max_hp)
        self.rule(26, h - 168, self.edge - 52)


class CampaignOutcome(Screen):
    """Accept one authoritative result; the pending command cannot pay it twice."""
    transparent = True

    def __init__(self, root, *, battle=False):
        super().__init__()
        self.root, self.tactical = root, battle

    def refresh(self):
        super().refresh()
        s, width = self.root.state, 680
        victory = s.battle.outcome == self.root.battle_team if self.tactical else s.status == 'victory'
        title = ('Battle won' if victory else 'Army defeated') if self.tactical else ('Shard won' if victory else 'Capital lost')
        detail = ('Accept the result to apply wounds, experience and any earned rewards.' if self.tactical else
                  'Your army captured the opposing capital.' if victory else 'The opposing realm captured your capital.')
        content = Column(Label(title, width=width, font='Georgia', font_size=32, text_color=GOLD),
                         Label(detail, width=width, wrap=True, font='Verdana',
                               font_size=round(13 * reading_scale(self.game) / 100), text_color=TEXT),
                         Label(self.message, width=width, wrap=True, text_color=MUTED), spacing=22)
        height = self.measure(content)[1]
        self.x, self.y = (self.game.width - 736) / 2, (self.game.height - height - 140) / 2
        self.height = height + 140
        self.ui.add(Column(content, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 32))))
        self.button('Accept result' if self.tactical else 'Return to title', self.x + 28,
                    self.y + self.height - 68, width, self.accept, shortcut='Enter', primary=True)

    def accept(self):
        if self.tactical:
            self.command(lambda: self.root.order('resolve_battle'))
        else:
            from eador.scene import TitleScene
            self.game.clear_and_push(TitleScene())

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 230))
        self.box(self.x, self.y, 736, self.height)
