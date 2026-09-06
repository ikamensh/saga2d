"""Drive the shipped controls with a public-command policy; never mutate its model.

The same driver works against mock input and native pyglet event dispatch. Reads
come from the current saved game; every changing command goes through its UI.
"""
from eador.model import BUILDINGS, RECRUITABLE
from eador.scene import BattleScene, CatalogScene, ChoiceScene, HeroScene, ResultScene, ShardScene
from eador.encounter_scene import EncounterScene
from saga2d import Button


class PlayerInput:
    def __init__(self, game, *, native=False, output=None):
        self.game, self.native, self.output = game, native, output
        self.events = []
        self.briefings = []
        self.reloads = 0
        self.state = PlayerState(self)

    @property
    def root(self):
        return next(scene for scene in self.game.scenes if isinstance(scene, ShardScene))

    def press(self, name):
        self.events.append((type(self.game.scene).__name__, 'key', name))
        if self.native:
            from pyglet.window import key
            symbol = getattr(key, 'ENTER' if name == 'return' else '_' + name if name.isdigit() else name.upper())
            self.game.backend.window.dispatch_event('on_key_press', symbol, 0)
            self.game.backend.window.dispatch_event('on_key_release', symbol, 0)
        else:
            self.game.backend.inject_key(name)
            self.game.backend.inject_key(name, type='key_release')
        self.game.tick(1 / 60)

    def click(self, x, y):
        self.events.append((type(self.game.scene).__name__, 'click', (round(x), round(y))))
        if self.native:
            from pyglet.window import mouse
            window = self.game.backend.window
            scale = min(window.width / self.game.width, window.height / self.game.height)
            px = (window.width - self.game.width * scale) / 2 + x * scale
            py = (window.height - self.game.height * scale) / 2 + (self.game.height - y) * scale
            window.dispatch_event('on_mouse_press', round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event('on_mouse_release', round(px), round(py), mouse.LEFT, 0)
        else:
            self.game.backend.inject_click(round(x), round(y))
            self.game.backend.inject_release(round(x), round(y))
        self.game.tick(1 / 60)

    def capture(self, name, *, settle=True):
        for _ in range(110 if settle and isinstance(self.game.scene, BattleScene) else 1):
            self.game.tick(1 / 60)
        if self.native and self.output is not None:
            self.output.mkdir(parents=True, exist_ok=True)
            self.game.backend.capture_frame().save(self.output / f'{name}.png')

    def button(self, label):
        control = self.game.scene.ui.find(lambda control: isinstance(control, Button) and control.text == label)
        assert control is not None and control.enabled, f'{type(self.game.scene).__name__} has no enabled {label}'
        x, y, width, height = control.bounds
        self.click(x + width / 2, y + height / 2)

    def reload(self, expected):
        self.press('f5')
        self.press('f9')
        assert self.root.state.to_json() == expected, 'UI quicksave/load changed the campaign'
        self.reloads += 1
        return self.state

    def choose_retinue(self, selection):
        from eador.campaign_scene import CampaignScene
        assert isinstance(self.game.scene, CampaignScene) and self.game.scene.step == 'retinue'
        before = self.state.to_json()
        for column, choices in ((0, selection['troop_ids']), (1, selection['relic_ids'])):
            self.press('left' if column == 0 else 'right')
            items = self.state.hero.army if column == 0 else self.state.inventory
            for index, item in enumerate(items):
                if (item.id if column == 0 else item) in choices:
                    self.press('space')
                if index + 1 < len(items):
                    self.press('down')
        assert self.state.to_json() == before, 'Choosing a retinue changed the campaign before departure'
        return selection


class PlayerBattle:
    def __init__(self, player, battle):
        self.player, self.battle = player, battle

    def __getattr__(self, name):
        return getattr(self.battle, name)

    def auto_turn(self):
        assert isinstance(self.player.game.scene, BattleScene)
        self.player.press('a')


class PlayerState:
    def __init__(self, player):
        self.player = player

    def __getattr__(self, name):
        return getattr(self.player.root.state, name)

    @property
    def battle(self):
        battle = self.player.root.state.battle
        return PlayerBattle(self.player, battle) if battle else None

    def travel(self, destination):
        assert isinstance(self.player.game.scene, ShardScene)
        self.player.click(*self.player.root.grid.center(destination))
        self.player.press('return')
        self.enter_briefing('return')

    def explore(self, *, approach=None):
        assert isinstance(self.player.game.scene, ShardScene)
        self.player.press('x')
        self.enter_briefing('x', approach=approach)

    def enter_briefing(self, shortcut, *, approach=None):
        if isinstance(self.player.game.scene, EncounterScene):
            if approach is not None:
                index = next(index for index, choice in enumerate(self.player.game.scene.approaches) if choice.id == approach)
                self.player.press(str(index + 1))
            self.player.briefings.append(self.player.game.scene.definition.name)
            before = self.to_json()
            self.player.capture('briefing-' + self.player.game.scene.definition.name.lower().replace(' ', '-'))
            self.player.press('escape')
            assert self.to_json() == before, 'Canceling a briefing spent campaign resources'
            # Repeat the visible action that opened it, before accepting.
            self.player.press(shortcut)
            assert isinstance(self.player.game.scene, EncounterScene)
            if approach is not None:
                self.player.press(str(index + 1))
            self.player.press('return')
            assert isinstance(self.player.game.scene, BattleScene)

    def end_turn(self):
        assert isinstance(self.player.game.scene, ShardScene)
        self.player.press('e')

    def build(self, name):
        self.catalog('b', list(BUILDINGS).index(name))
        assert name in self.buildings

    def recruit(self, name):
        before = len(self.hero.army)
        self.catalog('r', list(RECRUITABLE).index(name))
        assert len(self.hero.army) == before + 1 and self.hero.army[-1].kind == name

    def catalog(self, shortcut, index):
        assert isinstance(self.player.game.scene, ShardScene)
        self.player.press(shortcut)
        assert isinstance(self.player.game.scene, CatalogScene)
        for _ in range(index // 5):
            self.player.press('right')
        self.player.press(str(index % 5 + 1))
        self.player.press('escape')

    def choose(self, ident):
        assert isinstance(self.player.game.scene, ChoiceScene)
        index = next(index for index, choice in enumerate(self.choice.options) if choice.id == ident)
        self.player.press(str(index + 1))

    def equip(self, ident):
        assert isinstance(self.player.game.scene, ShardScene)
        self.player.press('h')
        assert isinstance(self.player.game.scene, HeroScene)
        if ident is None:
            self.player.press('u')
        else:
            index = self.inventory.index(ident)
            for _ in range(index // 4):
                self.player.press('right')
            self.player.press(str(index % 4 + 1))
        self.player.press('escape')
        assert self.hero.relic == ident

    def resolve_battle(self):
        assert isinstance(self.player.game.scene, ResultScene)
        self.player.press('e')
        return self.log[-1]

    def retreat(self):
        assert isinstance(self.player.game.scene, BattleScene)
        self.player.press('t')
        assert self.battle is None

    def advance(self, destination, *, troop_ids, relic_ids):
        from eador.campaign_scene import CampaignScene
        assert isinstance(self.player.game.scene, CampaignScene) and self.campaign.phase == 'departure'
        stage, before = self.campaign.stage, self.to_json()
        index = next(index for index, offer in enumerate(self.campaign.offers) if offer.id == destination)
        self.player.press(str(index + 1))
        self.player.press('escape')
        assert self.to_json() == before and self.player.game.scene.step == 'offers'
        self.player.press(str(index + 1))
        self.player.choose_retinue(dict(troop_ids=troop_ids, relic_ids=relic_ids))
        self.player.capture(f'stage-{stage}-earned-retinue')
        self.player.press('return')
        assert isinstance(self.player.game.scene, ShardScene) and self.campaign.stage == stage + 1
        assert set(troop_ids) <= {troop.id for troop in self.hero.army}
        assert set(relic_ids) == set(self.inventory)
        self.player.capture(f'stage-{stage + 1}-earned-arrival')
