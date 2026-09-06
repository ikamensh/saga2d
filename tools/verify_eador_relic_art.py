"""Inspect original relic icons and saved reward/equipment pages through public input."""
import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador import art
from eador.app import create_game
from eador.model import State
from eador.scene import ChoiceScene, HeroScene, Screen, ShardScene
from eador.style import GOLD, MUTED, TEAL
from tools.eador_campaign import play_campaign
from tools.eador_ui import PlayerInput


class RelicSheet(Screen):
    kinds = [('wayfarer_boots', 'Wayfarer Boots'), ('oak_standard', 'Oak Standard'),
             ('ember_lens', 'Ember Lens'), ('moonstone', 'Moonstone'),
             ('iron_crown', 'Iron Crown'), ('merchant_seal', 'Merchant Seal'),
             ('watch_bell', 'Watch Bell'), ('storm_quiver', 'Storm Quiver'),
             ('veil_censer', 'Veil Censer'), ('porter_rune', "Porter's Rune"),
             ('mirror_badge', 'Mirror Badge'), ('vanguard_drum', 'Vanguard Drum')]

    def draw(self):
        self.text('SHARDBOUND / RELICS', 46, 26, size=30, serif=True)
        self.text('Original object silhouettes · reward size and equipment size', 46, 76, size=14, color=MUTED)
        for i, (kind, name) in enumerate(self.kinds):
            x, y = 46 + (i % 4) * 306, 128 + (i // 4) * 213
            self.box(x, y, 290, 193)
            self.text(name, x + 145, y + 18, size=17, center=True, color=TEAL)
            art.relic(self, x + 87, y + 99, kind, scale=1.45)
            art.relic(self, x + 217, y + 99, kind, scale=.8)
            self.text('Detail', x + 87, y + 158, size=10, center=True, color=GOLD)
            self.text('Inventory', x + 217, y + 158, size=10, center=True, color=GOLD)


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='relic-art-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)

        def capture_equipment(prefix):
            scene = game.scene
            assert isinstance(scene, HeroScene)
            before, seen = scene.root.state.to_json(), []
            for page in range(scene.pages):
                seen.extend(scene.visible_relics)
                player.capture(f'{prefix}-{page + 1}')
                if page + 1 < scene.pages:
                    player.button('Next')
            assert seen == scene.root.state.inventory
            assert scene.root.state.to_json() == before

        def equipment_key(relic):
            scene = game.scene
            assert isinstance(scene, HeroScene)
            while relic not in scene.visible_relics:
                assert scene.page + 1 < scene.pages, f'No equipment control for {relic!r}'
                player.press('right')
            return str(scene.visible_relics.index(relic) + 1)

        try:
            game.push(RelicSheet())
            player.capture('twelve-relic-sheet')
            # Generated through State.new_campaign(0) + play_campaign's ordinary
            # all-province route at schema11, before any source rewards changed.
            old = Path(__file__).resolve().parents[1] / 'tests/eador/fixtures/v11_relic_collection.json'
            state = State.from_json(old.read_text())
            root = ShardScene(state)
            game.clear_and_push(root)
            game.push(HeroScene(root))
            before = state.to_json()
            capture_equipment('v11-equipment-page')
            assert state.to_json() == before
            selected = state.inventory[-1]
            player.press(equipment_key(selected))
            assert state.hero.relic == selected
            before = state.to_json()
            saved = {path.name: path.read_bytes() for path in (Path(directory) / 'saves').iterdir()}
            player.press(equipment_key(selected))
            assert state.to_json() == before
            assert saved == {path.name: path.read_bytes() for path in (Path(directory) / 'saves').iterdir()}
            while game.scene.page:
                player.button('Previous')
            player.capture('v11-equipment-after-selection')

            # Record actual pending choices along ordinary paid campaigns. These
            # states contain earned loot, not a fabricated inventory for layout.
            choices = {}

            class Rewards:
                def __init__(self, state):
                    self.state = state

                def __getattr__(self, name):
                    return getattr(self.state, name)

                def choose(self, option_id):
                    choice = self.state.choice
                    choices.setdefault((choice.kind, choice.context), self.state.to_json())
                    self.state.choose(option_id)

            for theme in ('frontier', 'elderwild', 'ruins'):
                state = State.new(0, theme=theme)
                route = [state.hero.pos] + [p for p in sorted(state.provinces)
                                           if p not in (state.hero.pos, (2, 0))] + [(2, 0)]
                result = play_campaign(Rewards(state), route)
                root = ShardScene(State.from_json(result.to_json()))
                game.clear_and_push(root)
                game.push(HeroScene(root))
                capture_equipment(f'earned-{theme}-equipment')

            for relic in ('veil_censer', 'porter_rune', 'mirror_badge', 'vanguard_drum'):
                state = State.from_json(choices['relic', relic])
                root = ShardScene(state)
                game.clear_and_push(root)
                assert isinstance(game.scene, ChoiceScene)
                player.capture(f'earned-{relic}-reward')
                player.reload(state.to_json())
                state = player.root.state
                player.press('1')
                assert relic in state.inventory
                player.press('h')
                assert isinstance(game.scene, HeroScene)
                player.press(equipment_key(relic))
                assert state.hero.relic == relic
                player.capture(f'earned-{relic}-equipped')

            skill = next(data for (kind, _), data in choices.items() if kind == 'skill')
            root = ShardScene(State.from_json(skill))
            game.clear_and_push(root)
            assert isinstance(game.scene, ChoiceScene)
            player.capture('earned-skill-choice')
            player.press('1')
            print(f'Relic family, saved paging and four earned/reloaded rewards passed ({backend}): {output}')
        finally:
            game._teardown()
            if backend == 'pyglet':
                game.backend.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-relic-art'))
    verify(parser.parse_args().output)
