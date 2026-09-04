"""SoundBank: generation and caching, WAV validity, playback through the mock backend."""

import shutil
import wave
from pathlib import Path

import numpy as np
import pytest

from saga2d import Game
from tribes import sound
from tribes.sound import SoundBank

EFFECTS = {
    "select", "move", "attack_hit", "attack_blocked", "unit_death", "capture", "level_up", "research",
    "train", "harvest", "end_turn", "turn_start", "error", "victory", "defeat", "ui_click", "ui_hover",
}


@pytest.fixture(scope="session")
def generated(tmp_path_factory) -> Path:
    """One generated bank shared by the tests that only play from it."""
    root = tmp_path_factory.mktemp("tribes")
    sound.generate(root)
    return root


@pytest.fixture
def bank(game: Game, generated: Path) -> SoundBank:
    return SoundBank(game, data_dir=generated)


def read_wav(path: Path) -> tuple[np.ndarray, int, int]:
    """``(samples in [-1, 1] shaped (frames, channels), sample width, rate)``."""
    with wave.open(str(path), "rb") as src:
        channels, width, rate, frames = src.getparams()[:4]
        data = np.frombuffer(src.readframes(frames), dtype="<i2").astype(float) / 32768
    return data.reshape(-1, channels), width, rate


def test_bank_generates_every_effect_and_the_music_loop(bank: SoundBank, generated: Path) -> None:
    assert set(bank.names) == EFFECTS
    assert (generated / "sounds" / "VERSION").read_text() == sound.SOUND_VERSION
    for name in EFFECTS:
        data, width, rate = read_wav(generated / "sounds" / f"{name}.wav")
        assert (data.shape[1], width, rate) == (1, 2, sound.SAMPLE_RATE), name
        assert 0.05 <= len(data) / rate <= 0.6, name
    data, width, rate = read_wav(generated / "music" / "ambient.wav")
    assert (data.shape[1], width, rate) == (2, 2, sound.SAMPLE_RATE)
    assert 30 <= len(data) / rate <= 45


def test_effects_are_normalised_and_click_free(generated: Path) -> None:
    for name in EFFECTS:
        data, _, _ = read_wav(generated / "sounds" / f"{name}.wav")
        mono = data[:, 0]
        assert 0.15 <= np.abs(mono).max() <= 0.95, name
        assert abs(mono[0]) < 0.01 and abs(mono[-1]) < 0.01, name  # starts and ends in silence
        assert np.abs(np.diff(mono)).max() < 0.5, name  # no sample-to-sample jump that would click


def test_music_is_quiet_and_loops_seamlessly(generated: Path) -> None:
    data, _, _ = read_wav(generated / "music" / "ambient.wav")
    assert 0.3 <= np.abs(data).max() <= 0.6
    seam = np.abs(data[-1] - data[0]).max()
    inside = np.abs(np.diff(data, axis=0)).max()
    assert seam <= inside, "the loop seam jumps more than any step inside the track"


def test_play_reaches_the_backend_with_the_cached_file(bank: SoundBank, backend, generated: Path) -> None:
    bank.play("attack_hit")
    played = backend.sounds_played[-1]
    assert played["handle"] == backend.load_sound(str(generated / "sounds" / "attack_hit.wav"))
    assert played["pitch"] == 1.0 and played["volume"] == 1.0


def test_pitch_variation_spreads_pitches_around_nominal(bank: SoundBank, backend) -> None:
    for _ in range(20):
        bank.play("move", pitch_variation=0.08)
    pitches = [played["pitch"] for played in backend.sounds_played]
    assert all(0.92 <= pitch <= 1.08 for pitch in pitches)
    assert len(set(pitches)) > 1


def test_unknown_sound_raises_key_error(bank: SoundBank, backend) -> None:
    with pytest.raises(KeyError, match="Unknown sound 'boom'"):
        bank.play("boom")
    assert backend.sounds_played == []


def test_music_volume_and_mute(bank: SoundBank, backend) -> None:
    bank.set_volume("music", 0.4)
    bank.start_music()
    bank.start_music()
    assert bank.music_playing and backend.music_playing is not None
    assert backend.music_volume == pytest.approx(0.4)
    bank.muted = True
    bank.play("select")
    assert backend.music_volume == 0.0 and backend.sounds_played == []
    bank.muted = False
    assert backend.music_volume == pytest.approx(0.4)
    bank.stop_music()
    assert not bank.music_playing and backend.music_playing is None


def test_bad_channel_is_rejected(bank: SoundBank) -> None:
    with pytest.raises(KeyError):
        bank.set_volume("voice", 0.5)


def test_cache_is_reused_when_complete(game: Game, generated: Path) -> None:
    before = {path: path.stat().st_mtime_ns for path in sound.sound_files(generated)}
    SoundBank(game, data_dir=generated)
    assert {path: path.stat().st_mtime_ns for path in sound.sound_files(generated)} == before


def test_missing_file_triggers_regeneration(game: Game, generated: Path, tmp_path: Path) -> None:
    copy = tmp_path / "tribes"
    shutil.copytree(generated, copy)
    (copy / "sounds" / "move.wav").unlink()
    SoundBank(game, data_dir=copy)
    assert (copy / "sounds" / "move.wav").read_bytes() == (generated / "sounds" / "move.wav").read_bytes()


def test_stale_version_marker_regenerates_identical_files(game: Game, generated: Path, tmp_path: Path) -> None:
    """Deterministic synthesis: a regenerated bank is byte-identical to the shared one."""
    for path in sound.sound_files(tmp_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"stale")
    (tmp_path / "sounds" / "VERSION").write_text("0")
    SoundBank(game, data_dir=tmp_path)
    assert (tmp_path / "sounds" / "VERSION").read_text() == sound.SOUND_VERSION
    for fresh, shared in zip(sound.sound_files(tmp_path), sound.sound_files(generated)):
        assert fresh.read_bytes() == shared.read_bytes(), fresh.name
