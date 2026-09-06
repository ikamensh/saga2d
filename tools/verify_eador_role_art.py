"""Render role silhouettes and browse current/legacy Codex pages with native input."""
import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador import art
from eador.codex import CodexScene
from eador.model import State
from eador.scene import Screen, ShardScene
from eador.style import GOLD, MUTED, TEAL
from tools.eador_roles_campaign import prepare_support_watch
from tools.eador_ui import PlayerInput


class TroopSheet(Screen):
    kinds = [('archer', 'Archer'), ('ranger', 'Ranger'), ('swordsman', 'Swordsman'),
             ('warden', 'Warden'), ('Wizard', 'Wizard'), ('healer', 'Acolyte')]

    def draw(self):
        self.text('SHARDBOUND / TROOP SILHOUETTES', 50, 35, size=28, serif=True)
        self.text('Original vector pieces · same rendering at battle and retinue scales', 50, 79, size=14, color=MUTED)
        for i, (kind, label) in enumerate(self.kinds):
            x = 155 + 192 * i
            self.text(label, x, 125, size=19, center=True, color=TEAL)
            art.piece(self, x, 272, kind, 'player', scale=1.8)
            art.piece(self, x, 410, kind, 'player', scale=1)
            art.piece(self, x, 510, kind, 'player', scale=.61)
            art.piece(self, x, 607, kind, 'enemy', scale=1)
            art.piece(self, x, 708, kind, 'player', scale=.61, selected=True, spent=True)
        for y, label in [(329, 'Battle size'), (448, 'Retinue size'), (544, 'Enemy'), (650, 'Selected / spent')]:
            self.text(label, 32, y, size=10, color=GOLD)
            self.rule(150, y + 8, 1060)


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='role-art-') as directory:
        game = create_game(visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=True, output=output)
        try:
            game.push(TroopSheet())
            player.capture('troop-sheet')
            state = prepare_support_watch()
            root = ShardScene(state)
            game.clear_and_push(root)
            player.capture('paid-watch-board')
            before = state.to_json()
            game.push(CodexScene(root))
            game.tick(1 / 60)
            player.button('Abilities')
            player.button('Next')
            assert game.scene.category == 1 and game.scene.page == 1
            player.capture('current-role-abilities')
            player.button('Troops')
            player.button('Next')
            player.capture('current-acolyte-troop')
            player.button('Next')
            player.capture('warden-troop')
            player.button('Next')
            player.capture('ranger-troop')
            player.press('escape')
            assert state.to_json() == before
            fixture = Path(__file__).resolve().parents[1] / 'tests/eador/fixtures/v8_acolyte_battle.json'
            old = State.from_json(fixture.read_text())
            root = ShardScene(old)
            game.clear_and_push(root)
            before = old.to_json()
            game.push(CodexScene(root))
            player.press('right')
            player.capture('v8-acolyte-troop')
            player.press('2')
            player.press('right')
            assert game.scene.category == 1 and game.scene.page == 1
            player.capture('v8-role-abilities')
            player.press('escape')
            assert old.to_json() == before
            assert not list((Path(directory) / 'saves').glob('*'))
            print(f'Role sheet, paid Watch and current/legacy Codex native journeys passed: {output}')
        finally:
            game._teardown()
            game.backend.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-role-art'))
    verify(parser.parse_args().output)
