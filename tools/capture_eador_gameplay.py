"""Capture a directed manual opening, with native frames and reconstructed audio.

The movie uses fixed 30 Hz simulation frames, not wall-time performance footage.
Audio is reconstructed from pass-through logs of public backend playback calls
using the exact shipping WAVs and gains. It is not a device/loopback recording.
No new rendering or recording interface is added to Saga2D.

    python tools/capture_eador_gameplay.py --output /tmp/shardbound-movie --ffmpeg /path/to/ffmpeg

Capture and encoding run sequentially; temporary raw frames are removed on exit.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game  # noqa: E402
from eador.battle_playback_scene import BattlePlaybackScene  # noqa: E402
from eador.model import State  # noqa: E402
from eador.scene import BattleScene, ChoiceScene, ResultScene, ShardScene, TitleScene  # noqa: E402
from saga2d.testing.cpu_budget import CpuBudget  # noqa: E402
from tools.eador_sources import framework_sources, source_name
from tools.eador_ui import PlayerInput  # noqa: E402
from saga2d.testing.native_frames import tick  # noqa: E402

FPS, WIDTH, HEIGHT, RATE = 30, 1280, 800, 44100


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AudioLog:
    """Observe public backend calls without changing their arguments or results."""

    def __init__(self, backend, frame):
        self.events, self.assets, self.handles = [], {}, {}
        self.frame = frame
        for name in ('load_sound', 'load_music'):
            original = getattr(backend, name)

            def load(path, original=original):
                handle = original(path)
                relative = Path(path).resolve().relative_to(ROOT).as_posix()
                self.handles[id(handle)] = relative
                self.assets[relative] = digest(path)
                return handle

            setattr(backend, name, load)
        sound, music = backend.play_sound, backend.play_music
        volume, stop = backend.set_player_volume, backend.stop_player

        def play_sound(handle, volume=1.0, pitch=1.0):
            player = sound(handle, volume=volume, pitch=pitch)
            self.add('start', player, path=self.handles[id(handle)], volume=volume,
                     pitch=pitch, loop=False, channel='sfx')
            return player

        def play_music(handle, *, loop=True, volume=1.0):
            player = music(handle, loop=loop, volume=volume)
            self.add('start', player, path=self.handles[id(handle)], volume=volume,
                     pitch=1.0, loop=loop, channel='music')
            return player

        def set_volume(player, gain):
            volume(player, gain)
            self.add('volume', player, volume=gain)

        def stop_player(player):
            natural = not backend.is_player_playing(player)
            stop(player)
            self.add('stop', player, natural=natural)

        backend.play_sound, backend.play_music = play_sound, play_music
        backend.set_player_volume, backend.stop_player = set_volume, stop_player

    def add(self, kind, player, **facts):
        self.events.append(dict(frame=self.frame(), kind=kind, player=player, **facts))


def mix_audio(events, assets, frames, output, budget):
    """Mix emitted voices at unity export gain; fail visibly if their sum clips."""
    samples = {}
    for path, expected in assets.items():
        assert digest(ROOT / path) == expected, f'Audio changed: {path}'
        with wave.open(str(ROOT / path), 'rb') as source:
            assert source.getframerate() == RATE and source.getsampwidth() == 2
            channels = source.getnchannels()
            assert channels in (1, 2)
            values = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2')
            values = values.astype(np.float64).reshape(-1, channels) / 32768
            samples[path] = np.repeat(values, 2, axis=1) if channels == 1 else values
        budget.checkpoint()
    voices = {}
    for event in events:
        at, ident = round(event['frame'] * RATE / FPS), event['player']
        if event['kind'] == 'start':
            assert event['pitch'] == 1, 'This bounded exporter supports nominal-pitch shipping cues only'
            voices[ident] = dict(event, start=at, end=round(frames * RATE / FPS),
                                 gains=[(at, event['volume'])])
        elif ident in voices:
            if event['kind'] == 'stop':
                # The native driver reaches EOS on wall time, while this movie
                # advances on simulation frames. Preserve each natural WAV tail.
                if not (event.get('natural', False) and not voices[ident]['loop']):
                    voices[ident]['end'] = min(at, voices[ident]['end'])
            elif event['kind'] == 'volume':
                voices[ident]['gains'].append((at, event['volume']))
    mixed = np.zeros((round(frames * RATE / FPS), 2), dtype=np.float64)
    for voice in voices.values():
        source = samples[voice['path']]
        end = voice['end'] if voice['loop'] else min(voice['end'], voice['start'] + len(source))
        gains = voice['gains'] + [(end, 0)]
        for (start, gain), (stop, _) in zip(gains, gains[1:]):
            stop = min(stop, end)
            if stop > start and gain:
                positions = np.arange(start - voice['start'], stop - voice['start']) % len(source)
                mixed[start:stop] += source[positions] * gain
            budget.checkpoint()
    peak = float(np.abs(mixed).max())
    assert peak <= 1, f'The emitted default-volume mix clips: peak {peak:.4f}; do not normalize it away'
    with wave.open(str(output), 'wb') as destination:
        destination.setnchannels(2)
        destination.setsampwidth(2)
        destination.setframerate(RATE)
        destination.writeframes(np.rint(mixed * 32767).astype('<i2').tobytes())
    budget.checkpoint()
    return dict(sample_rate=RATE, channels=2, peak=peak,
                rms=float(np.sqrt(np.mean(mixed ** 2))), export_gain=1,
                mono_placement='Copied equally to both channels; no spatialization or device latency.')


class MovieInput(PlayerInput):
    """Every actual input and ordinary update shares the movie's frame clock."""

    def __init__(self, game, output, raw, budget, *, native):
        super().__init__(game, native=native, finish_actions=False)
        self.output, self.raw, self.budget = output, raw, budget
        self.frames, self.input_count = 0, 0
        self.inputs, self.orders, self.chapters, self.playback_events = [], [], [], []
        self.audio_log = AudioLog(game.backend, lambda: self.frames)

    def _tick(self):
        assert self.frames < FPS * 90, 'The directed opening exceeded its 90-second capture bound'
        before = self.root.state.to_json() if any(isinstance(s, ShardScene) for s in self.game.scenes) else None
        for event in self.events[self.input_count:]:
            self.inputs.append(dict(frame=self.frames, event=event))
        had_input = self.input_count != len(self.events)
        self.input_count = len(self.events)
        scene = self.game.scene
        if isinstance(scene, BattlePlaybackScene):
            mark = dict(frame=self.frames, kind=scene.playback.event.kind,
                        index=scene.playback.index, applied=scene.playback.applied,
                        text=scene.playback.event.text)
            if not self.playback_events or any(mark[k] != self.playback_events[-1][k]
                                               for k in ('kind', 'index', 'applied', 'text')):
                self.playback_events.append(mark)
        if self.native:
            tick(self.game, 1 / FPS)
            from PIL import Image
            frame = self.game.backend.capture_frame()
            # Video transcoding only: downsample Retina pixels to the logical canvas.
            self.raw.write(frame.resize((WIDTH, HEIGHT), Image.Resampling.BOX).convert('RGB').tobytes())
        else:
            self.game.tick(1 / FPS)
        if before is not None and not had_input:
            assert self.root.state.to_json() == before, 'Presentation frames changed authoritative progress'
        self.frames += 1
        self.budget.checkpoint()

    def hold(self, seconds):
        for _ in range(round(seconds * FPS)):
            self._tick()

    def chapter(self, name):
        self.chapters.append(dict(frame=self.frames, seconds=self.frames / FPS, name=name))
        print(f'{self.frames / FPS:5.1f}s  {name}', flush=True)
        if self.native:
            self.game.backend.capture_frame().save(
                self.output / f'{len(self.chapters):02}-{name.lower().replace(" ", "-")}.png')
            self.budget.checkpoint()

    def do(self, command, *args, hold=1.2, **kwargs):
        assert command != 'battle.auto_turn'
        before = self.root.state.to_json()
        expected = State.from_json(before)
        receiver = expected.battle if command.startswith('battle.') else expected
        getattr(receiver, command.removeprefix('battle.'))(*args, **kwargs)
        start = self.frames
        self.order(command, *args, **kwargs)
        assert self.root.state.to_json() == expected.to_json(), command
        self.orders.append(dict(frame=start, command=command, args=args, kwargs=kwargs,
                                before=before, after=expected.to_json()))
        self.hold(hold)

    def enemy_round(self):
        self.chapter('Enemy turn')
        self.do('battle.end_turn', hold=0)
        self.watch_playback()
        self.hold(1)

    def watch_playback(self):
        while isinstance(self.game.scene, BattlePlaybackScene):
            self._tick()


def opening(player):
    """A small directed manual battle, never the game's auto-play command."""
    game = player.game
    game.push(TitleScene(7, hero_class='Wizard'))
    player.hold(2)
    player.chapter('Choose your hero')
    player.press('return')
    player.hold(3)
    player.chapter('A new realm')
    player.do('explore', hold=2)
    assert type(game.scene) is BattleScene
    player.chapter('Manual tactics')
    archer = next(u for u in player.state.battle.units if u.team == 'player' and u.can_pin)
    archer_start = archer.pos
    player.do('battle.move', archer.id, (-1, 0))
    target = player.state.battle.targets(archer.id)[0]
    player.do('battle.attack', archer.id, target.id, hold=1.5)
    player.do('battle.move', 0, archer_start)
    target = max(player.state.battle.spell_targets('bolt'), key=lambda u: u.hp)
    player.do('battle.cast', 'bolt', target.id, hold=1.5)
    for militia in [u for u in player.state.battle.units if u.team == 'player' and u.kind == 'militia']:
        player.do('battle.guard', militia.id, hold=.8)
    player.enemy_round()
    # Complete the actual opening, choosing visible targets and legal reachable
    # positions. This is a directed capture policy, not independent player evidence.
    for _ in range(4):
        if player.state.battle.outcome:
            break
        heal_targets = player.state.battle.spell_targets('heal')
        if heal_targets:
            player.do('battle.cast', 'heal', min(heal_targets, key=lambda u: u.hp / u.max_hp).id, hold=1.5)
        for ident in [u.id for u in player.state.battle.units if u.team == 'player' and u.alive]:
            battle = player.state.battle
            if battle.outcome:
                break
            actor = battle.unit(ident)
            if actor.acted:
                continue
            targets = battle.targets(ident)
            if not targets and battle.reachable(ident):
                enemies = [u for u in battle.units if u.team == 'enemy' and u.alive]
                destination = min(battle.reachable(ident),
                                  key=lambda pos: (min(battle.grid.distance(pos, foe.pos) for foe in enemies), pos))
                player.do('battle.move', ident, destination, hold=.6)
                targets = player.state.battle.targets(ident)
            if targets:
                player.do('battle.attack', ident, min(targets, key=lambda u: u.hp).id, hold=1.3)
            else:
                player.do('battle.guard', ident, hold=.5)
        if not player.state.battle.outcome:
            player.enemy_round()
    assert player.state.battle.outcome == 'player', 'The directed opening did not reach victory'
    player.watch_playback()
    assert isinstance(game.scene, ResultScene)
    player.chapter('Victory')
    player.hold(3)
    player.do('resolve_battle', hold=2)
    while isinstance(game.scene, ChoiceScene):
        player.chapter('An earned reward')
        player.hold(3)
        player.do('choose', player.state.choice.options[0].id, hold=2)
    assert type(game.scene) is ShardScene
    player.chapter('Back to the realm')
    player.hold(3)


def encode(ffmpeg, raw, audio, output, percent):
    """Run one single-thread encoder after capture, yielding its own process budget."""
    command = [str(ffmpeg), '-y', '-loglevel', 'warning', '-filter_threads', '1',
               '-filter_complex_threads', '1', '-threads', '1', '-f', 'rawvideo',
               '-pixel_format', 'rgb24', '-video_size', f'{WIDTH}x{HEIGHT}', '-framerate', str(FPS),
               '-i', str(raw), '-i', str(audio), '-c:v', 'libx264', '-threads', '1',
               '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
               '-b:a', '192k', '-movflags', '+faststart', str(output)]
    with (output.parent / 'encoder.log').open('w') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 300
        try:
            while child.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('The single-thread movie encoder exceeded five minutes')
                time.sleep(.05)
                if child.poll() is None and percent < 100:
                    child.send_signal(signal.SIGSTOP)
                    time.sleep(.05 * (100 / percent - 1))
                    child.send_signal(signal.SIGCONT)
            if child.returncode:
                raise subprocess.CalledProcessError(child.returncode, command)
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGCONT)
                child.terminate()
                child.wait(timeout=10)
    return dict(command=command, executable_sha256=digest(ffmpeg), cpu_percent_requested=percent)


def capture(output, *, backend='pyglet', ffmpeg=None, cpu_percent=25):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError('Choose an empty capture directory so older media cannot enter this receipt')
    if backend == 'pyglet' and ffmpeg is None:
        raise ValueError('Native capture requires an explicit ffmpeg executable')
    files = [Path(__file__), ROOT / 'tools/eador_ui.py', *(ROOT / 'eador').glob('*.py'),
             *framework_sources(),
             *(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())]
    sources = {source_name(path): digest(path) for path in files}
    budget = CpuBudget(cpu_percent)
    started, cpu_started = time.monotonic(), time.process_time()
    report = dict(scope=__doc__, source_revision=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), source_sha256=sources,
        dirty_at_start=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
        backend=backend, fps=FPS, resolution=[WIDTH, HEIGHT], cpu_percent_requested=cpu_percent)
    with TemporaryDirectory(prefix='shardbound-movie-') as temporary:
        raw_path = Path(temporary) / 'frames.rgb'
        with raw_path.open('wb') as raw:
            game = create_game(backend=backend, visible=False, save_dir=Path(temporary) / 'saves')
            player = MovieInput(game, output, raw, budget, native=backend == 'pyglet')
            try:
                opening(player)
                report['final_state'] = player.root.state.to_json()
            finally:
                game.close()
            report.update(frames=player.frames, duration=player.frames / FPS, inputs=player.inputs,
                          orders=player.orders, chapters=player.chapters,
                          playback_events=player.playback_events, audio_events=player.audio_log.events,
                          audio_assets=player.audio_log.assets)
        report['audio_mix'] = mix_audio(player.audio_log.events, player.audio_log.assets,
                                        player.frames, output / 'gameplay-mix.wav', budget)
        report['capture_wall_seconds'] = time.monotonic() - started
        report['capture_cpu_seconds'] = time.process_time() - cpu_started
        if backend == 'pyglet':
            print('Encoding after capture; one encoder thread with paced CPU allowance.', flush=True)
            report['encoder'] = encode(ffmpeg, raw_path, output / 'gameplay-mix.wav', output / 'gameplay.mp4', cpu_percent)
    assert all(digest(ROOT / path) == expected for path, expected in sources.items()), 'Capture sources changed'
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
    print(f'{result["duration"]:.2f}s; {len(result["orders"])} public commands; '
          f'{len(result["audio_events"])} emitted audio events: {args.output}', flush=True)
