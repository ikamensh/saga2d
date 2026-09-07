"""Recorded pictures and reconstructed audio share one bounded game timeline."""
import wave

import numpy as np
import pytest

from eador.model import State
from tools.capture_eador_gameplay import FPS, RATE, capture, digest, mix_audio
from tools.cpu_budget import CpuBudget


def test_directed_movie_reaches_an_earned_reward_without_skipping_enemy_playback(tmp_path):
    """The same recording journey executes UI orders, observes motion and emits actual game cues."""
    report = capture(tmp_path, backend='mock')
    state = State.from_json(report['final_state'])
    assert state.battle is None and state.choice is None and state.inventory
    assert state.provinces[state.hero.pos].explored
    assert not any(order['command'] == 'battle.auto_turn' for order in report['orders'])
    assert not any(tuple(item['event'][1:]) == ('key', 'space') for item in report['inputs'])
    assert {'move', 'attack', 'retaliation'} <= {event['kind'] for event in report['playback_events']}
    cues = {event['path'].split('/')[-1] for event in report['audio_events'] if event['kind'] == 'start'}
    assert {'campaign.wav', 'battle.wav', 'attack_arrow.wav', 'bolt.wav', 'heal.wav', 'victory.wav'} <= cues
    with wave.open(str(tmp_path / 'gameplay-mix.wav')) as audio:
        assert audio.getnframes() == round(report['frames'] * RATE / FPS)
        assert audio.getnchannels() == 2
    assert 0 < report['audio_mix']['peak'] <= 1 and report['audio_mix']['export_gain'] == 1


def test_audio_gain_changes_preserve_loop_phase_and_stop_the_voice(tmp_path, monkeypatch):
    """Silence changes the active voice's gain; unmute resumes its timeline instead of restarting."""
    import tools.capture_eador_gameplay as movie

    monkeypatch.setattr(movie, 'ROOT', tmp_path)
    # Two frame-long halves make loop position audible and exactly inspectable.
    step = RATE // FPS
    values = np.array([1000] * step + [2000] * step, dtype='<i2')
    with wave.open(str(tmp_path / 'loop.wav'), 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes(values.tobytes())
    events = [dict(frame=0, kind='start', player=1, path='loop.wav', volume=1, pitch=1, loop=True),
              dict(frame=1, kind='volume', player=1, volume=0),
              dict(frame=3, kind='volume', player=1, volume=.5),
              dict(frame=4, kind='stop', player=1)]
    destination = tmp_path / 'mix.wav'
    mix_audio(events, {'loop.wav': digest(tmp_path / 'loop.wav')}, 5, destination, CpuBudget())
    with wave.open(str(destination), 'rb') as wav:
        actual = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').reshape(-1, 2)
    expected = np.array([1000] * step + [0] * (2 * step) + [1000] * step + [0] * step)
    assert np.array_equal(actual[:, 0], expected) and np.array_equal(actual[:, 1], expected)


@pytest.mark.parametrize('natural', [True, False])
def test_natural_driver_cleanup_preserves_the_fixed_timeline_tail(tmp_path, monkeypatch, natural):
    """A slower capture must not shorten a WAV when the native driver finishes first."""
    import tools.capture_eador_gameplay as movie

    monkeypatch.setattr(movie, 'ROOT', tmp_path)
    step = RATE // FPS
    with wave.open(str(tmp_path / 'cue.wav'), 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes(np.full(2 * step, 1000, dtype='<i2').tobytes())
    events = [dict(frame=0, kind='start', player=1, path='cue.wav', volume=1, pitch=1, loop=False),
              dict(frame=1, kind='stop', player=1, natural=natural)]
    destination = tmp_path / 'mix.wav'
    mix_audio(events, {'cue.wav': digest(tmp_path / 'cue.wav')}, 3, destination, CpuBudget())
    with wave.open(str(destination), 'rb') as wav:
        actual = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').reshape(-1, 2)
    length = (2 if natural else 1) * step
    assert np.all(actual[:length] == 1000) and np.all(actual[length:] == 0)
