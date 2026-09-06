"""Build Shardbound's original shipping WAVs, provenance and a cue/music sampler.

    uv run python tools/build_eador_audio.py
    uv run python tools/build_eador_audio.py --verify-native

Generation happens before packaging, never on launch. Native verification uses
only the silent driver and runs each music track through a complete loop.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eador.sound import CUES, GENERATOR_VERSION, TRACKS  # noqa: E402
from saga2d.synth import SAMPLE_RATE, mix, write_wav  # noqa: E402
from tools.cpu_budget import CpuBudget  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(path):
    with wave.open(str(path), 'rb') as stream:
        channels, frames = stream.getnchannels(), stream.getnframes()
        pcm = np.frombuffer(stream.readframes(frames), dtype='<i2').reshape(-1, channels) / 32767
    return {'sha256': digest(path), 'bytes': path.stat().st_size, 'frames': frames,
            'channels': channels, 'seconds': round(frames / SAMPLE_RATE, 6),
            'peak': round(float(np.max(np.abs(pcm))), 8),
            'rms': round(float(np.sqrt(np.mean(pcm ** 2))), 8),
            'seam_step': round(float(np.max(np.abs(pcm[0] - pcm[-1]))), 8)}


def build_assets(directory: Path, *, sampler: Path, budget: CpuBudget | None = None) -> dict:
    """Generate deterministic shipping audio and its exact-file manifest."""
    budget = budget or CpuBudget()
    files, placements, order = {}, [], {}
    music_excerpts = {}
    cursor = .25
    for folder, catalogue in (('sounds', CUES), ('music', TRACKS)):
        for name, compose in catalogue.items():
            samples = compose(budget=budget) if folder == 'music' else compose()
            relative = f'{folder}/{name}.wav'
            target = directory / relative
            write_wav(target, samples)
            files[relative] = {**describe(target), 'description': compose.__doc__}
            if folder == 'sounds':
                placements.append((cursor, samples))
                order[name] = round(cursor, 6)
                cursor += len(samples) / SAMPLE_RATE + .35
            else:
                excerpt = samples[:16 * SAMPLE_RATE].copy()
                fade = np.linspace(0, 1, SAMPLE_RATE // 4)[:, None]
                excerpt[:len(fade)] *= fade
                excerpt[-len(fade):] *= fade[::-1]
                placements.append((cursor, excerpt))
                music_excerpts[name] = {'sampler_start': round(cursor, 6),
                                        'source_start': 0, 'seconds': 16}
                cursor += 16.75
            budget.checkpoint()
    write_wav(sampler, mix(*placements, (cursor, np.zeros(round(.25 * SAMPLE_RATE)))))
    manifest = {
        'product': 'Shardbound', 'generator_version': GENERATOR_VERSION,
        'cpu_percent': budget.percent,
        'sample_rate': SAMPLE_RATE, 'encoding': '16-bit PCM WAV',
        'composition': 'Original E-minor shard motif, explicit game-owned voicings and rhythms; deterministic seeded noise.',
        'provenance': 'Generated solely from project source. No recordings, sampled instruments, Eador assets, or externally sourced melodies were used.',
        'license': 'Repository MIT license; see LICENSE.',
        'review_status': 'Technical verification only; listening and artistic approval remain required.',
        'runtime': {'python': '.'.join(map(str, sys.version_info[:3])), 'numpy': np.__version__},
        'source_sha256': {name: digest(ROOT / name) for name in
                          ('eador/sound.py', 'saga2d/synth.py', 'tools/build_eador_audio.py', 'tools/cpu_budget.py')},
        'files': files,
        'sampler': {**describe(sampler), 'order': order, 'music_excerpts': music_excerpts},
    }
    (directory / 'audio-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    budget.checkpoint()
    return manifest


def verify_native(directory: Path, manifest: dict) -> None:
    """Exercise every cue to completion and both native looping streams silently."""
    os.environ['SAGA2D_SILENT'] = '1'
    from saga2d import Game, Scene
    from eador.sound import set_music

    game = Game('Shardbound audio verification', visible=False, resolution=(64, 64), asset_path=directory)
    backend = game.backend
    native_players = []
    catalogue = [('sounds', name) for name in CUES] + [('music', name) for name in TRACKS]

    class Catalogue(Scene):
        def on_enter(self):
            self.index = -1
            self.start_next()

        def start_next(self):
            self.index += 1
            if self.index == len(catalogue):
                game.quit()
                return
            folder, name = catalogue[self.index]
            self.started = time.monotonic()
            self.duration = manifest['files'][f'{folder}/{name}.wav']['seconds']
            game.audio.set_volume('master', .25)
            game.audio.set_volume('sfx', .4)
            game.audio.set_volume('music', .2)
            game.audio.muted = False
            if folder == 'sounds':
                game.audio.play_sound(name, volume=.8)
            else:
                set_music(game, name)
            self.player = list(backend._players.values())[-1]
            native_players.append(self.player)
            gain = .08 if folder == 'sounds' else .05
            assert abs(self.player.volume - gain) < 1e-8
            game.audio.muted = True
            assert self.player.volume == 0
            game.audio.set_volume('master', .5)
            assert self.player.volume == 0
            game.audio.muted = False
            assert abs(self.player.volume - gain * 2) < 1e-8
            print(f'Native silent: {folder}/{name}, {self.duration:.2f}s', flush=True)

        def update(self, dt):
            elapsed = time.monotonic() - self.started
            folder, name = catalogue[self.index]
            if elapsed > self.duration + 3:
                raise TimeoutError(f'Audio did not finish or loop: {name}')
            if elapsed >= self.duration + .15:
                if folder == 'sounds':
                    assert not self.player.playing and self.player.source is None
                    assert not backend._sound_players
                else:
                    assert self.player.playing and self.player.source is not None
                    set_music(game, name)
                    assert self.player is list(backend._players.values())[-1]
                    # Last track deliberately remains active for Game.run teardown.
                    if self.index < len(catalogue) - 1:
                        set_music(game, None)
                        assert not self.player.playing
                self.start_next()

    game.run(Catalogue())
    assert not backend._players and not backend._sound_players
    assert all(not player.playing and player._audio_player is None for player in native_players)
    print('Complete catalogue, loop continuity, live mute/mix and native lifetime checks passed.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'eador' / 'assets')
    parser.add_argument('--sampler', type=Path, default=ROOT / 'docs' / 'evidence' / 'shardbound-cue-sampler.wav')
    parser.add_argument('--verify-native', action='store_true')
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='Cooperative build allowance as a percentage of one core (default: 25; 100 disables pacing)')
    args = parser.parse_args()
    manifest = build_assets(args.out, sampler=args.sampler, budget=CpuBudget(args.cpu_percent))
    print(f'Built {len(manifest["files"])} shipping WAVs in {args.out}; sampler {args.sampler}', flush=True)
    if args.verify_native:
        verify_native(args.out, manifest)


if __name__ == '__main__':
    main()
