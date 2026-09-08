"""Directed native campaign PvP input with a real socket peer and a 25% CPU allowance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import MatchClient, MatchHost
from eador.app import create_game
from eador.concurrent_campaign import ConcurrentCampaign
from eador.concurrent_scene import ConcurrentShardScene
from eador.scene import BattleScene
from tools.cpu_budget import CpuBudget
from tools.verify_eador_shard_look import PacedInput


def verify(output, *, backend='pyglet', seat=0):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    budget = CpuBudget(25)
    started, cpu = time.monotonic(), time.process_time()
    match = ConcurrentCampaign.new(7, heroes=('Warrior', 'Warrior'))
    commands = []

    def apply(player, command):
        match.apply(player, command)
        commands.append({'seat': player, 'command': command, 'checkpoint': match.checkpoint()})

    host = MatchHost('shardbound-pvp-v1', apply, match.snapshot, address=('127.0.0.1', 0), token='native-check')
    client = MatchClient('shardbound-pvp-v1', host.address, token=host.token)
    sessions = host, client
    game = create_game('Shardbound campaign PvP verification', backend=backend, visible=False,
                       save_dir=output / 'saves')
    player = PacedInput(game, budget, native=backend == 'pyglet', output=output)
    captures = []

    def settle(until):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            host.poll()
            client.poll()
            player._tick()
            assert not client.error, client.error
            if until() and all(session.state == match.snapshot(index) for index, session in enumerate(sessions)):
                return
            time.sleep(.005)
        raise AssertionError('Native campaign views did not converge.')

    def peer_order(action, *args):
        peer = sessions[1 - seat]
        previous = peer.state['realm']['revision']
        peer.submit({'day': peer.state['day'], 'realm_revision': previous,
                     'action': action, 'args': list(args), 'kwargs': {}})
        settle(lambda: peer.state['realm']['revision'] > previous)

    def capture(name):
        player.capture(name, settle=False)
        captures.append(name)

    try:
        settle(lambda: client.ready)
        root = ConcurrentShardScene(sessions[seat])
        game.push(root)
        player._tick()
        capture('01-map')
        title = max(root.state.provinces.values(), key=lambda province: len(province.name))
        player.pointer(*root.grid.center(title.pos))
        player.click(*root.grid.center(title.pos))
        assert root.selected == title.pos
        capture('02-hover-selection')
        player.press('f1')
        help_screen = game.scene
        before = match.snapshot(seat)['realm']
        peer_order('build', 'barracks')
        assert game.scene is help_screen and match.snapshot(seat)['realm'] == before
        capture('03-help-during-peer-purchase')
        player.press('escape')
        player.press('b')
        player.press('1')
        settle(lambda: bool(root.state.buildings))
        capture('04-purchase')
        player.press('escape')
        player.press('home')
        player.press('x')
        settle(lambda: type(game.scene) is BattleScene)
        tactical = game.scene
        peer_order('explore')
        assert game.scene is tactical
        capture('05-concurrent-pve')
        before = match.checkpoint()
        enemy = next(unit for unit in root.state.battle.units if unit.team == 'enemy')
        player.click(*tactical.grid.center(enemy.pos))
        assert game.scene is tactical and tactical.message and match.checkpoint() == before
        capture('05b-invalid-order-refusal')
        player.press('f6')
        assert game.scene.title == 'Live room'
        capture('05c-live-room-persistence')
        player.press('escape')
        player.press('g')
        settle(lambda: root.state.battle.unit(0).stance == 'guard')
        player.finish_playback()
        player.press('f1')
        help_screen = game.scene
        battle = root.state.battle.to_dict()
        peer_order('battle.guard', 0)
        assert game.scene is help_screen and root.state.battle.to_dict() == battle
        capture('06-battle-help-during-peer-order')
        player.press('escape')
        player.press('t')
        settle(lambda: game.scene is root and root.state.battle is None)
        assert match.realms[1 - seat].battle is not None
        capture('07-own-retreat-peer-still-fighting')
        player.press('e')
        settle(lambda: root.state.ready)
        assert root.state.day == 1
        capture('08-ready-waits-for-battle')
        peer_order('retreat')
        peer_order('ready')
        settle(lambda: root.state.day == 2)
        capture('09-shared-new-day')
        player.press('f2')
        player.press('right')
        player.press('return')
        capture('10-map-large-text')
        player.press('h')
        capture('11-hero-large-text')
        player.press('escape')
        files = ('eador/art.py', 'eador/concurrent_scene.py', 'eador/concurrent_view.py', 'eador/concurrent_campaign.py',
                 'eador/scene.py', 'eador/model.py', 'eador/entities.py', 'eador/battle_playback_scene.py',
                 'tools/verify_eador_concurrent_ui.py')
        receipt = {'backend': backend, 'seat': seat, 'inputs': player.events, 'commands': commands,
                   'captures': captures, 'final_checkpoint': match.checkpoint(),
                   'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
                   'directed_verification_not_independent_human_play': True}
    finally:
        game.close()
        client.close()
        host.close()
    receipt.update(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu,
                   closed=True, cpu_allowance_percent=25, native_fps_cap=30)
    (output / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('seat', 'captures', 'wall_seconds', 'cpu_seconds', 'closed')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--seat', type=int, choices=(0, 1), default=0)
    args = parser.parse_args()
    verify(args.output, backend=args.backend, seat=args.seat)
