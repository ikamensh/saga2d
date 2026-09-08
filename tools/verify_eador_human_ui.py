"""Bounded native tactical adapter check, using fresh armies and real paid preparation.

This verifies a defender's BattleScene contract, not room networking or a played campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.app import create_game
from eador.battle import Battle
from eador.battle_playback_scene import BattlePlaybackScene
from eador.model import State
from eador.scene import ShardScene
from saga2d import Button, Label
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput


class PacedInput(PlayerInput):
    def __init__(self, game, budget, **options):
        super().__init__(game, finish_actions=False, **options)
        self.budget = budget

    def _tick(self):
        super()._tick()  # Existing native cap: 30 FPS.
        self.budget.checkpoint()


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Choose an empty directory to preserve earlier evidence.')
    output.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget(25) if budget is None else budget
    started, cpu_started = time.monotonic(), time.process_time()
    paths = sorted((ROOT / 'eador').glob('*.py')) + sorted((ROOT / 'saga2d').rglob('*.py'))
    paths += [Path(__file__).resolve(), ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    attacker, defender = State.new(7, 'Wizard'), State.new(12, 'Wizard')
    for action, args in [('end_turn', ()), ('build', ('temple',)), ('recruit', ('healer',))]:
        getattr(defender, action)(*args)
        budget.checkpoint()
    battle = Battle.create_duel(attacker.hero, defender.hero, 'plains', attacker.spells, defender.spells)
    initial = battle.to_dict()
    defender.battle, defender.battle_province, defender.battle_kind = battle, defender.hero.pos, 'army'
    root = ShardScene(defender)
    root.battle_team, root.live_match = 'enemy', True
    report = dict(backend=backend, cpu_percent_requested=budget.percent, native_fps=30,
                  scope='Tactical adapter with paid model preparation; no online room or campaign journey.',
                  preparation=['Fresh Wizard realms: seeds 7 and 12.',
                               'Defender: End turn, buy Temple, recruit Acolyte, then create_duel.'],
                  defender_gold=defender.gold, source_sha256=hashes, orders=[], captures=[])

    def unit(team, source):
        return next(actor for actor in battle.units if actor.team == team and actor.source_id == source)

    with TemporaryDirectory(prefix='shardbound-human-ui-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PacedInput(game, budget, native=backend == 'pyglet', output=output)

        def capture(name, phase):
            scene = game.scene
            button = scene.ui.find(lambda item: isinstance(item, Button) and item.text == phase)
            assert button is not None and button.enabled == (phase == 'End phase')
            pool = scene.ui.find(lambda item: item.tooltip ==
                                f'Mana: {battle.enemy_magic.mana}. Shared pool for the hero and allied spellcasters.')
            assert pool is not None
            assert any(item.text == str(battle.enemy_magic.mana) for item in pool.walk() if isinstance(item, Label))
            before = battle.to_dict()
            player.capture(name, settle=False)
            assert battle.to_dict() == before
            report['captures'].append(dict(name=name, local_mana=battle.enemy_magic.mana,
                                           opposing_mana=battle.mana, phase=phase))

        def order(action, *args, peer=False, **kwargs):
            expected = Battle.from_dict(battle.to_dict())
            getattr(expected, action)(*args, **kwargs)
            if peer:
                trace = battle.trace(lambda: getattr(battle, action)(*args, **kwargs))
                game.scene.begin_playback(trace)
                while isinstance(game.scene, BattlePlaybackScene):
                    player._tick()
            else:
                player.order('battle.' + action, *args, **kwargs)
            assert battle.to_dict() == expected.to_dict()
            report['orders'].append(dict(action=action, args=args, kwargs=kwargs,
                                         actor='model peer' if peer else 'native input' if player.native else 'mock input',
                                         after_sha256=hashlib.sha256(json.dumps(battle.to_dict(), sort_keys=True).encode()).hexdigest()))

        try:
            game.set_window_size((1280, 720))
            game.push(root)
            player._tick()
            for key in ('f2', 'right', 'return'):
                player.press(key)
            capture('defender-waiting-125', 'Waiting for opponent')
            before = battle.to_dict()
            for key in ('e', 'a', 'g', '1', '2', 't'):
                player.press(key)
                assert battle.to_dict() == before
            order('move', unit('player', 1).id, (-1, 0), peer=True)
            order('move', unit('player', 0).id, (-1, -1), peer=True)
            order('cast', 'bolt', unit('enemy', 0).id, peer=True)
            order('end_turn', peer=True)
            capture('defender-phase-125', 'End phase')
            healer = next(actor for actor in battle.units if actor.team == 'enemy' and actor.can_heal)
            order('cast', 'heal', unit('enemy', 0).id, caster_id=healer.id)
            order('move', unit('enemy', 1).id, (1, 0))
            order('move', unit('enemy', 0).id, (1, 1))
            order('cast', 'bolt', unit('player', 0).id, caster_id=unit('enemy', 0).id)
            capture('defender-spent-mana-125', 'End phase')
            order('end_turn')
            while isinstance(game.scene, BattlePlaybackScene):
                player._tick()
            capture('defender-returned-waiting-125', 'Waiting for opponent')
        finally:
            game.close()
        assert not game.scenes
        if player.native:
            assert game.backend.window is None
        else:
            assert not game.backend.is_running
        report['input_activations'] = len(player.events)
    assert hashes == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report.update(source_unchanged=True, game_closed=True, wall_seconds=time.monotonic() - started,
                  cpu_seconds=time.process_time() - cpu_started)
    for name, data in [('initial-battle', initial), ('final-battle', battle.to_dict()), ('verification', report)]:
        (output / f'{name}.json').write_text(json.dumps(data, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    print(json.dumps(verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent)), indent=2))
