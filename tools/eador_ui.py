"""Drive the shipped controls with a public-command policy; never mutate its model.

The same driver works against mock input and native pyglet event dispatch. Reads
come from the current saved game; every changing command goes through its UI.
"""
from eador.model import BUILDINGS, RECRUITABLE
from eador.scene import BattleScene, CatalogScene, ChoiceScene, HeroScene, ResultScene, ShardScene
from eador.encounter_scene import EncounterScene


class PlayerInput:
    def __init__(self, game, *, native=False, output=None):
        self.game, self.native, self.output = game, native, output
        self.events = []
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

    def capture(self, name):
        for _ in range(110 if isinstance(self.game.scene, BattleScene) else 1):
            self.game.tick(1 / 60)
        if self.native and self.output is not None:
            self.output.mkdir(parents=True, exist_ok=True)
            self.game.backend.capture_frame().save(self.output / f'{name}.png')

    def reload(self, expected):
        self.press('f5')
        self.press('f9')
        assert self.root.state.to_json() == expected, 'UI quicksave/load changed the campaign'
        self.reloads += 1
        return self.state


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

    def explore(self):
        assert isinstance(self.player.game.scene, ShardScene)
        self.player.press('x')
        self.enter_briefing('x')

    def enter_briefing(self, shortcut):
        if isinstance(self.player.game.scene, EncounterScene):
            before = self.to_json()
            self.player.capture('briefing-' + self.player.game.scene.definition.name.lower().replace(' ', '-'))
            self.player.press('escape')
            assert self.to_json() == before, 'Canceling a briefing spent campaign resources'
            # Repeat the visible action that opened it, before accepting.
            self.player.press(shortcut)
            assert isinstance(self.player.game.scene, EncounterScene)
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
        self.player.press(str(index + 1))
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
