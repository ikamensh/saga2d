"""Public synthesis helpers compose real WAV assets accepted by the audio API."""

import wave

import numpy as np
import pytest

from saga2d import Game
from saga2d.synth import SAMPLE_RATE, level, mix, noise, pan, thump, tone, write_wav


def test_composed_stereo_asset_roundtrips_pcm_and_plays(tmp_path):
    """A layered mono/stereo composition keeps timing, panning and signal through file playback."""
    clip = level(mix(pan(tone("D4", .2), -.5),
                     (.1, pan(noise(.15, 300, 4000, seed=19), .5)),
                     thump(180, 60, .12)), .7)
    path = tmp_path / "sounds" / "impact.wav"
    write_wav(path, clip)
    with wave.open(str(path), "rb") as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (2, 2, SAMPLE_RATE)
        restored = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").reshape(-1, 2) / 32767
    assert restored.shape == (round(.25 * SAMPLE_RATE), 2)
    assert np.max(np.abs(restored - clip)) <= 1 / 32767
    assert np.max(np.abs(restored)) <= .7001
    assert np.max(np.abs(restored[-1])) == 0
    game = Game("Composed audio", backend="mock", asset_path=tmp_path)
    try:
        game.audio.play_sound("impact")
        assert game.backend.sounds_played[-1]["handle"] == game.backend.load_sound(str(path))
    finally:
        game._teardown()


def test_silent_normalization_refuses_nan_audio():
    """Normalizing silence has no defined gain and must fail instead of manufacturing NaNs."""
    with pytest.raises(ValueError, match="silent"):
        level(np.zeros(128), .6)


def test_noise_too_short_for_a_signal_refuses_nan_audio():
    """A one-sample filtered burst has no non-DC signal and cannot be normalized."""
    with pytest.raises(ValueError, match="silent"):
        noise(1 / SAMPLE_RATE, 300, 4000)


@pytest.mark.parametrize("samples", [np.array([np.nan, 0.]), np.array([0., np.inf]),
                                     np.zeros((5, 3)), np.array([0., 1.2]), np.array([])])
def test_invalid_asset_is_rejected_before_replacing_file(tmp_path, samples):
    """Bad samples must not silently clip, change channel shape or destroy a valid prior asset."""
    path = tmp_path / "cue.wav"
    write_wav(path, tone("C4", .1))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        write_wav(path, samples)
    assert path.read_bytes() == before
