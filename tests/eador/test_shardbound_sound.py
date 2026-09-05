"""Original audio compositions through PCM files and the public game audio path."""

from pathlib import Path
import wave

import numpy as np

from saga2d import Game
from saga2d.synth import SAMPLE_RATE, write_wav
from eador.sound import confirm


def read_pcm(path):
    with wave.open(str(path), 'rb') as stream:
        assert stream.getsampwidth() == 2
        assert stream.getframerate() == SAMPLE_RATE
        return np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, stream.getnchannels()) / 32767


def test_composed_confirmation_roundtrips_to_a_playable_effect(tmp_path):
    """An original cue produces finite unclipped PCM accepted by game.audio."""
    samples = confirm()
    path = tmp_path / 'sounds' / 'confirm.wav'
    write_wav(path, samples)
    pcm = read_pcm(path)
    assert .1 < len(pcm) / SAMPLE_RATE < .5
    assert np.max(np.abs(pcm)) < .7
    assert np.max(np.abs(pcm[[0, -1]])) < 1 / 32767
    game = Game('Shardbound audio test', backend='mock', asset_path=tmp_path)
    try:
        game.audio.play_sound('confirm')
        assert game.backend.sounds_played[-1]['handle'] == game.backend.load_sound(str(path))
    finally:
        game._teardown()


def test_catalogue_cues_are_distinct_deterministic_and_have_soft_edges():
    """Every requested event has a real distinct cue with finite headroom and click-free endpoints."""
    from eador.sound import CUES
    assert set(CUES) == {'confirm', 'refuse', 'move', 'attack_hit', 'guard', 'bolt', 'heal',
                         'reward', 'level_up', 'victory', 'defeat', 'end_turn'}
    encoded = []
    for name, compose in CUES.items():
        samples = compose()
        assert np.array_equal(samples, compose()), name
        assert np.isfinite(samples).all(), name
        assert .12 <= len(samples) / SAMPLE_RATE <= 2.5, name
        assert .25 <= np.max(np.abs(samples)) <= .65, name
        assert np.max(np.abs(samples[[0, -1]])) == 0, name
        assert np.max(np.abs(samples[:20])) < .04, name
        assert np.max(np.abs(samples[-20:])) < .04, name
        encoded.append(samples.tobytes())
    assert len(set(encoded)) == len(CUES)


def test_music_loops_have_restraint_stereo_motion_and_continuous_seams():
    """Loop tails wrap naturally: seam steps are small without fading the whole soundtrack to silence."""
    from eador.sound import TRACKS
    for name, seconds in [('campaign', 48), ('battle', 32)]:
        samples = TRACKS[name]()
        assert samples.shape == (seconds * SAMPLE_RATE, 2)
        assert np.isfinite(samples).all()
        assert .015 < np.sqrt(np.mean(samples ** 2)) < .09
        assert np.max(np.abs(samples)) <= .181
        assert not np.array_equal(samples[:, 0], samples[:, 1])
        assert np.max(np.abs(samples[0] - samples[-1])) < .006
        boundary = np.concatenate((samples[-441:], samples[:441]))
        assert np.max(np.abs(np.diff(boundary, axis=0))) < .025
        assert np.sqrt(np.mean(boundary ** 2)) > .002


def test_build_catalogue_decodes_routes_and_regenerates_identically(tmp_path):
    """The shipping build emits deterministic usable files and a review sampler with a manifest."""
    import hashlib
    import json
    from eador.sound import CUES, TRACKS, set_music
    from tools.build_eador_audio import build_assets

    root = tmp_path / 'assets'
    sampler = tmp_path / 'sampler.wav'
    manifest = build_assets(root, sampler=sampler)
    before = {name: (root / name).read_bytes() for name in manifest['files']}
    sampler_before = sampler.read_bytes()
    assert len(manifest['files']) == 14
    for name, details in manifest['files'].items():
        pcm = read_pcm(root / name)
        assert len(pcm) == details['frames']
        assert hashlib.sha256(before[name]).hexdigest() == details['sha256']
        assert np.isfinite(pcm).all() and 0 < np.max(np.abs(pcm)) < .65
    assert list(manifest['sampler']['order']) == list(CUES)
    assert 10 < len(read_pcm(sampler)) / SAMPLE_RATE < 20
    game = Game('Shardbound catalogue', backend='mock', asset_path=root)
    try:
        for cue in CUES:
            game.audio.play_sound(cue)
        assert len(game.backend.sounds_played) == len(CUES)
        for track in TRACKS:
            set_music(game, track)
            assert game.audio.music_name == track
            handle = game.backend.music_playing
            set_music(game, track)
            assert game.backend.music_playing == handle
        set_music(game, None)
        assert game.audio.music_name is None
    finally:
        game._teardown()
    assert build_assets(root, sampler=sampler) == manifest
    assert {name: (root / name).read_bytes() for name in manifest['files']} == before
    assert sampler.read_bytes() == sampler_before
    assert json.loads((root / 'audio-manifest.json').read_text()) == manifest


def test_shipping_files_and_sources_match_the_recorded_manifest():
    """Packaging must not ship missing/stale audio under a current generator label."""
    import hashlib
    import json
    from eador.sound import GENERATOR_VERSION

    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / 'eador' / 'assets' / 'audio-manifest.json').read_text())
    assert manifest['generator_version'] == GENERATOR_VERSION
    for relative, expected in manifest['source_sha256'].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
    for relative, details in manifest['files'].items():
        path = root / 'eador' / 'assets' / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == details['sha256'], relative
        samples = read_pcm(path)
        assert len(samples) == details['frames']
        assert np.max(np.abs(samples)) < .65
    sampler = root / 'docs' / 'evidence' / 'shardbound-cue-sampler.wav'
    assert hashlib.sha256(sampler.read_bytes()).hexdigest() == manifest['sampler']['sha256']
