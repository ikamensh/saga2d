"""saga2d.synth: the primitives, the WAV cache and the bank."""

import wave
from pathlib import Path

import numpy as np
import pytest

from saga2d import Game, synth
from saga2d.synth import SAMPLE_RATE, SynthBank, envelope, hz, level, mix, noise, pan, thump, tone, write_wav


def test_notes_and_envelopes() -> None:
    assert hz("A4") == 440.0 and hz("A5") == 880.0 and hz("F#5") == pytest.approx(739.99, abs=0.01)
    env = envelope(0.2, 0.01, 0.05)
    assert env[0] == 0.0 and env.max() == pytest.approx(1.0, abs=0.01) and env[-1] == 0.0
    assert len(env) == int(0.2 * SAMPLE_RATE)


def test_tone_noise_and_thump_are_bounded_and_end_in_silence() -> None:
    for clip in (tone("C5", 0.1), tone(330.0, 0.1, partials=synth.BRASS), noise(0.1, 200, 2000, seed=4), thump(200, 60, 0.1)):
        assert np.abs(clip).max() <= 1.0 and abs(clip[-1]) < 1e-3
    assert noise(0.1, 200, 2000, seed=4).tolist() == noise(0.1, 200, 2000, seed=4).tolist()  # deterministic


def test_mix_places_clips_and_widens_to_stereo_when_needed() -> None:
    a, b = np.ones(100), np.ones(50) * 0.5
    out = mix(a, (100 / SAMPLE_RATE, b))
    assert len(out) == 150 and out[99] == 1.0 and out[100] == 0.5 and out[149] == 0.5
    stereo = mix(a, pan(b, -1.0))
    assert stereo.shape == (100, 2) and stereo[0, 0] == pytest.approx(1.5) and stereo[0, 1] == pytest.approx(1.0)
    assert level(np.array([0.1, -0.5]), 0.8).tolist() == pytest.approx([0.16, -0.8])


def test_write_wav_round_trips_mono_and_stereo(tmp_path: Path) -> None:
    mono = tone("A4", 0.05)
    write_wav(tmp_path / "m.wav", mono)
    write_wav(tmp_path / "s.wav", pan(mono, 0.5))
    with wave.open(str(tmp_path / "m.wav")) as src:
        assert src.getnchannels() == 1 and src.getframerate() == SAMPLE_RATE and src.getsampwidth() == 2
        data = np.frombuffer(src.readframes(src.getnframes()), dtype="<i2") / 32767
    assert np.abs(data - mono).max() < 1e-3
    with wave.open(str(tmp_path / "s.wav")) as src:
        assert src.getnchannels() == 2


def test_bank_generates_once_regenerates_on_a_new_version_and_plays(game: Game, backend, tmp_path: Path) -> None:
    sounds = {"ping": lambda: tone("A5", 0.05), "pong": lambda: tone("E5", 0.05)}
    music = {"loop": lambda: pan(tone("A3", 0.3), 0.0)}
    bank = SynthBank(game, tmp_path, version="1", sounds=sounds, music=music, aliases={"click": "ping"})
    files = synth.sound_files(tmp_path, sounds, music)
    assert all(f.exists() for f in files) and (tmp_path / "sounds" / "VERSION").read_text() == "1"
    stamps = {f: f.stat().st_mtime_ns for f in files}
    SynthBank(game, tmp_path, version="1", sounds=sounds, music=music)
    assert {f: f.stat().st_mtime_ns for f in files} == stamps
    bank.play("click", pitch_variation=0.1)
    assert backend.sounds_played[-1]["handle"] == backend.load_sound(str(tmp_path / "sounds" / "ping.wav"))
    assert 0.9 <= backend.sounds_played[-1]["pitch"] <= 1.1
    with pytest.raises(KeyError, match="Unknown sound"):
        bank.play("bang")
    bank.start_music("loop")
    bank.start_music("loop")
    assert bank.music_playing == "loop" and backend.music_playing is not None
    with pytest.raises(KeyError, match="Unknown track"):
        bank.start_music("nope")
    bank.stop_music()
    assert bank.music_playing is None
    (tmp_path / "sounds" / "ping.wav").write_bytes(b"stale")
    SynthBank(game, tmp_path, version="2", sounds=sounds, music=music)
    assert (tmp_path / "sounds" / "VERSION").read_text() == "2" and (tmp_path / "sounds" / "ping.wav").stat().st_size > 100
