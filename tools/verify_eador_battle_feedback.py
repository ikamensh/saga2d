"""Watch an earned enemy chain through real input, with exact resolved saves per frame."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.app import create_game
from eador.battle_playback_scene import BattlePlaybackScene
from eador.model import State
from eador.scene import BattleScene, ResultScene, TitleScene
from tools.eador_relief_campaign import prepare_relief, relief_forward_opening, relief_passive_route
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders


def watch(player, report, *, output, overlays=False):
    game = player.game
    assert isinstance(game.scene, BattlePlaybackScene)
    scene = game.scene
    resolved = player.state.to_json()
    if overlays:
        player.press('f2')
        clock = scene.playback.elapsed
        game.tick(2)
        assert scene.playback.elapsed == clock
        player.capture('settings-pauses-playback', settle=False)
        player.press('escape'); player.press('l')
        clock = scene.playback.elapsed
        game.tick(2)
        assert scene.playback.elapsed == clock
        player.capture('complete-authoritative-history', settle=False)
        player.press('escape')
    frames, seen = [], set()
    for tick in range(490):
        assert player.state.to_json() == resolved
        if game.scene is not scene:
            break
        playback = scene.playback
        event = playback.event
        stamp = (playback.index, playback.applied)
        if stamp not in seen:
            seen.add(stamp)
            report.append(dict(tick=tick, event=event.kind, index=playback.index,
                               applied=playback.applied, text=event.text,
                               actor=event.actor_id, target=event.target_id))
        if player.native and tick % 3 == 0:
            name = f'frame-{tick:03}.png'
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            game.backend.capture_frame().save(path)
            frames.append(dict(tick=tick, seconds=round(tick / 60, 3), file=name))
        game.tick(1 / 60)
    else:
        raise AssertionError('Playback exceeded its eight-second bound.')
    assert type(game.scene) in (BattleScene, ResultScene)
    assert player.state.to_json() == resolved
    if frames:
        (output / 'timing.json').write_text(json.dumps(frames, indent=2) + '\n')
    player.reload(resolved)
    return frames


class WatchedOrders(ControlOrders):
    """Resolve only through E, then observe natural ticks rather than skipping or reloading early."""
    def do(self, command, *args, **kwargs):
        if command != 'end_turn':
            return super().do(command, *args, **kwargs)
        expected = State.from_json(self.state.to_json())
        expected.battle.end_turn()
        self.player.press('e')
        assert self.state.to_json() == expected.to_json()
        self.orders.append((command, args, kwargs))
        watch(self.player, self.player.observed, output=self.player.output / f'phase-{len(self.orders)}',
              overlays=not self.player.observed)


def verify(output, *, backend='pyglet', scenario='rally', still=False, scale=100):
    output.mkdir(parents=True, exist_ok=True)
    paths = sorted([*ROOT.glob('eador/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/eador_*.py'),
                    ROOT / 'tools/verify_eador_battle_feedback.py', ROOT / 'tools/verify_eador_control.py',
                    ROOT / 'tools/verify_eador_extraction.py'])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    with TemporaryDirectory(prefix='shardbound-feedback-') as temporary:
        game = create_game(backend=backend, visible=False, save_dir=Path(temporary) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        player.observed = []
        try:
            game.push(TitleScene(7)); player.press('return')
            prepare_relief(state=player.state)
            player.press('f2')
            if scale == 125:
                player.press('right')
            if still:
                player.press('up'); player.press('right')
            player.press('return')
            if scenario == 'hold':
                player.finish_actions = False
                route = relief_passive_route(player.state, orders_type=WatchedOrders)
                assert player.state.battle.outcome_reason == 'hold'
                orders = route.orders
            else:
                player.state.explore(approach='forward')
                play = WatchedOrders(player.state)
                player.finish_actions = False
                relief_forward_opening(play, finish_support=False)
                order = [item['event'] for item in player.observed if not item['applied']]
                assert order.index('rally') < order.index('move') < order.index('brace') < order.index('attack')
                assert player.state.battle.outcome is None
                orders = play.orders
            report = dict(scenario=scenario, backend=backend, reduced_motion=still, reading_scale=scale,
                          observed=player.observed, inputs=player.events, input_activations=len(player.events),
                          exact_save_reloads=player.reloads, orders=orders, source_revision=revision,
                          dirty_at_start=dirty, source_sha256=hashes)
            player.capture('resolved-battle', settle=False)
            (output / 'resolved-state.json').write_text(player.state.to_json())
        finally:
            game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha for p, sha in hashes.items())
    (output / 'journey.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Feedback {scenario}/{scale}/still={still}: {len(player.events)} inputs, {player.reloads} exact reloads ({backend})')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-battle-feedback'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--scenario', choices=('rally', 'hold'), default='rally')
    parser.add_argument('--still', action='store_true')
    parser.add_argument('--scale', type=int, choices=(100, 125), default=100)
    args = parser.parse_args()
    verify(args.output, backend=args.backend, scenario=args.scenario, still=args.still, scale=args.scale)
