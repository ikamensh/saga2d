"""Capture a short, paced attack-motion preview from real public inputs.

Commander preparation uses public model commands and automatic battles; the
shown attacks are manual inputs, with exact immediate outcomes and UI reloads.
The movie is fixed-30-Hz presentation, with reconstructed shipping audio rather
than device recording. It is not independent playtesting or battery evidence.
"""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale, reduced_motion
from eador.scene import BattleScene, ResultScene, ShardScene
from tools.capture_eador_gameplay import FPS, HEIGHT, WIDTH, MovieInput, digest, encode, mix_audio
from tools.cpu_budget import CpuBudget
from tools.eador_observatory_campaign import prepare_observatory
from tools.verify_eador_final_blow import SOURCE, SOURCE_SHA, earned_last_arrow


def capture(output, *, backend='pyglet', ffmpeg=None, cpu_percent=25):
    output = Path(output).resolve()
    if backend == 'pyglet':
        if ffmpeg is None:
            raise ValueError('Native capture requires an explicit --ffmpeg executable')
        ffmpeg = Path(ffmpeg).resolve(strict=True)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError('Choose an empty directory; retain earlier previews separately')
    budget = CpuBudget(cpu_percent)
    paths = {Path(__file__).resolve(), SOURCE, *(ROOT / 'eador').glob('*.py'),
             *(ROOT / 'saga2d').rglob('*.py'), *(ROOT / 'tools').glob('eador_*.py'),
             *(ROOT / 'tools' / name for name in ('cpu_budget.py', 'native_frames.py',
               'capture_eador_gameplay.py', 'verify_eador_final_blow.py'))}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    sources = {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)}
    started, cpu_started = time.monotonic(), time.process_time()
    prepared = prepare_observatory(budget=budget).to_json()
    final_order = earned_last_arrow()
    budget.checkpoint()
    report = dict(scope=__doc__, backend=backend, fps=FPS, resolution=[WIDTH, HEIGHT],
                  cpu_percent_requested=budget.percent, source_sha256=sources,
                  source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  dirty_at_start=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
                  preparation=dict(commander=prepared, method='prepare_observatory: public model commands, automatic preparation battles; reused for the two presentation modes.'),
                  earned_origin=dict(file=str(SOURCE.relative_to(ROOT)), sha256=SOURCE_SHA, selector='orders[13]'),
                  cases=[])
    with TemporaryDirectory(prefix='shardbound-attack-motion-') as temporary:
        raw_path = Path(temporary) / 'frames.rgb'
        with raw_path.open('wb') as raw:
            game = create_game(backend=backend, visible=False, save_dir=Path(temporary) / 'saves')
            try:
                player = MovieInput(game, output, raw, budget, native=backend == 'pyglet')
                for name in ('Melee and retaliation', 'Wizard arrow', 'Earned final arrow', 'Reduced motion melee'):
                    still, lethal = name == 'Reduced motion melee', name == 'Earned final arrow'
                    melee = name in ('Melee and retaliation', 'Reduced motion melee')
                    if melee:
                        state = State.from_json(prepared)
                    elif lethal:
                        state = State.from_json(final_order['before'])
                    else:
                        state = State.new(hero_class='Wizard')
                    start, first_order, first_input = player.frames, len(player.orders), len(player.inputs)
                    origin = state.to_json()
                    game.clear_and_push(ShardScene(state))
                    player._tick()
                    if still:
                        # F2 focuses reading size; Up selects Reduced motion.
                        for key in ('f2', 'up', 'right', 'return'):
                            player.press(key)
                    assert reduced_motion(game) == still and reading_scale(game) == 100
                    assert state.to_json() == origin
                    if not lethal:
                        player.do('explore', approach='clear' if melee else None, hold=0)
                        if melee:
                            for ident, pos in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
                                player.do('battle.move', ident, pos, hold=0)
                            actor = 0
                            target = next(u.id for u in state.battle.units if u.team == 'enemy' and u.kind == 'guard')
                        else:
                            actor = next(u.id for u in state.battle.units if u.team == 'player' and u.can_pin)
                            player.do('battle.move', actor, (-1, 0), hold=0)
                            target = state.battle.targets(actor)[0].id
                    else:
                        actor, target = final_order['args']
                    assert type(game.scene) is BattleScene
                    player.chapter(name)
                    player.hold(.8)
                    before = state.to_json()
                    actor_hp, target_hp = state.battle.unit(actor).hp, state.battle.unit(target).hp
                    player.do('battle.attack', actor, target, hold=0)
                    resolved = state.to_json()
                    assert state.battle.unit(target).hp < target_hp
                    if melee:
                        assert state.battle.unit(actor).hp < actor_hp, 'The Guard must actually retaliate'
                    if lethal:
                        assert resolved == final_order['after'] and state.battle.outcome == 'player'
                    player.hold(.24)
                    player.chapter(name + ' Lunge')
                    player.hold(.24)
                    player.chapter(name + ' Recoil')
                    player.hold(1.5)
                    player.watch_playback()  # Natural completion; no Space skip.
                    assert type(game.scene) is (ResultScene if lethal else BattleScene)
                    assert state.to_json() == resolved
                    player.chapter(name + ' Settled')
                    player.reload(resolved)
                    player.hold(1)
                    assert player.root.state.to_json() == resolved
                    report['cases'].append(dict(name=name, initial_state=origin, before_attack=before,
                        after_attack=resolved, actor=actor, target=target, reduced_motion=still,
                        start_frame=start, end_frame=player.frames, orders=player.orders[first_order:],
                        inputs=player.inputs[first_input:], exact_save_reload=True))
                assert 15 <= player.frames / FPS <= 25, 'Keep this preview between 15 and 25 simulation seconds'
            finally:
                game.close()
            assert game.backend.window is None if backend == 'pyglet' else not game.backend.is_running
            report.update(frames=player.frames, duration=player.frames / FPS, inputs=player.inputs,
                          orders=player.orders, chapters=player.chapters, exact_save_reloads=player.reloads,
                          playback_events=player.playback_events, audio_events=player.audio_log.events,
                          audio_assets=player.audio_log.assets, game_closed=True)
        report['audio_mix'] = mix_audio(player.audio_log.events, player.audio_log.assets,
                                        player.frames, output / 'gameplay-mix.wav', budget)
        report.update(capture_wall_seconds=time.monotonic() - started,
                      capture_cpu_seconds=time.process_time() - cpu_started,
                      timing_scope='After imports/source hashing; includes model preparation, capture, game cleanup and audio mix. Excludes the separately paced encoder.')
        if backend == 'pyglet':
            report['encoder'] = encode(ffmpeg, raw_path, output / 'gameplay-mix.wav', output / 'gameplay.mp4', budget.percent)
    assert all(digest(ROOT / path) == expected for path, expected in sources.items()), 'Preview sources changed'
    report['source_unchanged'] = True
    report['artifacts'] = {path.name: digest(path) for path in output.iterdir()
                           if path.suffix in ('.png', '.mp4', '.wav')}
    (output / 'capture.json.gz').write_bytes(gzip.compress(json.dumps(report, indent=2).encode(), mtime=0))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--ffmpeg', type=Path)
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    result = capture(args.output, backend=args.backend, ffmpeg=args.ffmpeg, cpu_percent=args.cpu_percent)
    print(f'{result["duration"]:.2f}s; four cases; {result["exact_save_reloads"]} exact UI reloads: {args.output}')
