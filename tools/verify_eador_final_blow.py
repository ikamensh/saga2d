"""Watch one authenticated earned final arrow; never replay its campaign preparation.

Two cases use public input at normal 100% and reduced 125%. Pictures and technical
backend audio events are presentation evidence, not human or device-listening QA.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.app import create_game
from eador.battle_playback_scene import BattlePlaybackScene
from eador.model import State
from eador.persistence import AUTO_SLOTS, CampaignSaves
from eador.preferences import reading_scale, reduced_motion
from eador.scene import ResultScene, SaveScene, ShardScene
from tools.capture_eador_gameplay import AudioLog
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput
from tools.native_frames import tick

SOURCE = ROOT / 'docs/evidence/gameplay-movie/capture.json.gz'
SOURCE_SHA = 'd269952ac585c4df998c5e4b5da121f3f5f89a8c41abad2edebfb76dcdde2c80'


def earned_last_arrow():
    """Return the unchanged orders[13] record from the fixed manual Wizard opening."""
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA, 'Changed earned movie journal'
    order = json.loads(gzip.decompress(data))['orders'][13]
    assert order['command'] == 'battle.attack' and order['args'] == [3, 1003]
    return order


class WatchedInput(PlayerInput):
    def __init__(self, game, budget, *, native):
        super().__init__(game, native=native, finish_actions=False)
        self.budget, self.frames, self.expected = budget, 0, None

    def _tick(self):
        assert self.frames < 600, 'The bounded final-blow case exceeded 20 seconds of frames'
        tick(self.game, 1 / 30) if self.native else self.game.tick(1 / 30)
        self.frames += 1
        if self.expected is not None:
            assert self.state.to_json() == self.expected, 'Presentation changed the resolved state'
        self.budget.checkpoint()


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Choose an empty output directory; earlier captures must remain separate')
    output.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget(25) if budget is None else budget
    started, cpu_started = time.monotonic(), time.process_time()
    paths = {Path(__file__).resolve(), SOURCE, *(ROOT / 'eador').glob('*.py'),
             *(ROOT / 'saga2d').rglob('*.py'), *(ROOT / 'tools' / name for name in
             ('eador_ui.py', 'native_frames.py', 'cpu_budget.py', 'capture_eador_gameplay.py'))}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    order = earned_last_arrow()
    report = dict(source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, backend=backend, cpu_percent_requested=budget.percent, fps=30,
                  origin=dict(file=str(SOURCE.relative_to(ROOT)), sha256=SOURCE_SHA, selector='orders[13]',
                              preparation='Retained agent-directed fresh Wizard/Standard/Frontier7 opening; no autoplay.'),
                  cases=[])
    with TemporaryDirectory(prefix='shardbound-final-blow-') as temporary:
        for still, percent in ((False, 100), (True, 125)):
            name = f'{"reduced" if still else "normal"}-{percent}'
            game = create_game(backend=backend, visible=False, save_dir=Path(temporary) / name / 'saves')
            player = WatchedInput(game, budget, native=backend == 'pyglet')
            audio = AudioLog(game.backend, lambda: player.frames)
            case = dict(name=name, captures=[], before=order['before'], after=order['after'])
            try:
                state = State.from_json(order['before'])
                game.push(ShardScene(state)); player._tick()
                for key in (('f2', 'right', 'up', 'right', 'return') if still else ('f2', 'left', 'return')):
                    player.press(key)
                assert reading_scale(game) == percent and reduced_motion(game) == still
                assert state.to_json() == order['before']
                oracle = State.from_json(order['before'])
                oracle.battle.attack(*order['args'], **order['kwargs'])
                assert oracle.to_json() == order['after']
                audio_start = len(audio.events)
                cues = lambda: [Path(event['path']).stem for event in audio.events[audio_start:]
                                if event['kind'] == 'start' and event['channel'] == 'sfx']
                player.order(order['command'], *order['args'], **order['kwargs'])
                player.expected = order['after']
                assert state.to_json() == player.expected and state.battle.outcome == 'player'
                view = game.scene
                assert isinstance(view, BattlePlaybackScene)
                saves = CampaignSaves(game.save_manager)
                autosaves = {slot: saves.load(slot) for slot in AUTO_SLOTS}
                case['immediate_autosaves'] = [slot for slot, saved in autosaves.items()
                                              if saved is not None and saved.to_json() == player.expected]
                assert case['immediate_autosaves'], 'The terminal state was not autosaved before viewing'
                assert view.battle.unit(1003).hp == 5 and cues() == ['attack_arrow']

                def capture(label):
                    assert player.state.to_json() == player.expected
                    filename = f'{name}-{label}.png'
                    if player.native:
                        game.backend.capture_frame().save(output / filename)
                    case['captures'].append(dict(file=filename if player.native else None, label=label,
                        frame=player.frames, scene=type(game.scene).__name__, window_size=list(game.window_size),
                        reading_scale=reading_scale(game), reduced_motion=reduced_motion(game),
                        target_view_hp=view.battle.unit(1003).hp,
                        event=view.playback.event.kind if game.scene is view else None,
                        fraction=view.playback.fraction if game.scene is view else None,
                        result_overlays=sum(isinstance(s, ResultScene) for s in game.scenes)))

                capture('release')
                while view.playback.fraction < .3:
                    player._tick()
                assert game.scene is view and view.battle.unit(1003).alive and not view.playback.applied
                capture('flight')  # Reduced motion intentionally shows the stationary contact marker.
                player.press('f6')
                assert isinstance(game.scene, SaveScene)
                paused = view.playback.index, view.playback.elapsed
                paused_cues = list(cues())
                for _ in range(15):
                    player._tick()
                assert (view.playback.index, view.playback.elapsed) == paused and cues() == paused_cues
                case['pause_frames'] = 15
                player.press('escape')
                assert game.scene is view
                while view.playback.fraction < .7:
                    player._tick()
                assert game.scene is view and view.playback.event.kind == 'attack'
                assert not view.battle.unit(1003).alive and cues() == ['attack_arrow', 'attack_hit']
                capture('contact')
                if still:
                    player.reload(player.expected)  # Load the resolved save while its terminal trace is still showing.
                else:
                    while game.scene is view:
                        player._tick()
                result_cues = ['attack_arrow', 'attack_hit'] + ([] if still else ['victory'])
                assert type(game.scene) is ResultScene and cues() == result_cues
                assert sum(isinstance(s, ResultScene) for s in game.scenes) == 1
                capture('result')
                if not still:
                    player.reload(player.expected)
                for _ in range(15):
                    player._tick()
                assert type(game.scene) is ResultScene and cues().count('victory') == (0 if still else 1)
                assert cues().count('attack_hit') == 1 and sum(isinstance(s, ResultScene) for s in game.scenes) == 1
                case.update(inputs=player.events, frames=player.frames, exact_save_reloads=player.reloads,
                            loaded_during_playback=still, cues=cues(), audio_events=audio.events,
                            audio_assets=audio.assets, exact_state=True)
                report['cases'].append(case)
            finally:
                game.close()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report.update(source_unchanged=True, wall_seconds=time.monotonic() - started,
                  cpu_seconds=time.process_time() - cpu_started,
                  input_activations=sum(len(case['inputs']) for case in report['cases']))
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Final blow: two cases, eight captures, {report["input_activations"]} inputs ({backend}); {output}')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-final-blow'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
