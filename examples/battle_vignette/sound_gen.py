"""Generate procedural sound effects for the tactical battle demo.

Run from project root::

    python examples/battle_vignette/sound_gen.py

Generates .wav files in examples/battle_vignette/assets/sounds/.
Uses numpy for waveform synthesis — no external audio files needed.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 22050
OUTPUT_DIR = Path(__file__).resolve().parent / "assets" / "sounds"


def _write_wav(filepath: Path, samples: np.ndarray) -> None:
    """Write a mono 16-bit WAV file."""
    # Normalize to [-1, 1] then scale to int16
    peak = np.max(np.abs(samples))
    if peak > 0:
        samples = samples / peak
    int_samples = (samples * 32767 * 0.8).astype(np.int16)

    with wave.open(str(filepath), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int_samples.tobytes())


def _envelope(length: int, attack: float = 0.01, decay: float = 0.1) -> np.ndarray:
    """Simple attack-decay envelope."""
    t = np.linspace(0, 1, length)
    env = np.ones(length)
    # Attack ramp
    attack_samples = max(1, int(attack * length))
    env[:attack_samples] = np.linspace(0, 1, attack_samples)
    # Decay ramp
    decay_samples = max(1, int(decay * length))
    env[-decay_samples:] = np.linspace(1, 0, decay_samples)
    return env


def make_sword_hit() -> np.ndarray:
    """Metallic clang — short burst of harmonics with noise."""
    duration = 0.2
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Mix of metallic frequencies
    signal = (
        0.5 * np.sin(2 * np.pi * 800 * t)
        + 0.3 * np.sin(2 * np.pi * 1200 * t)
        + 0.2 * np.sin(2 * np.pi * 2400 * t)
        + 0.15 * np.sin(2 * np.pi * 3600 * t)
    )

    # Add noise burst at start
    noise = np.random.RandomState(42).uniform(-0.3, 0.3, n)
    noise_env = np.exp(-t * 30)
    signal += noise * noise_env

    # Sharp attack, quick decay
    env = np.exp(-t * 15) * _envelope(n, attack=0.005, decay=0.05)
    return signal * env


def make_death() -> np.ndarray:
    """Low descending tone with noise — unit death."""
    duration = 0.5
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Descending frequency sweep
    freq = np.linspace(300, 80, n)
    phase = np.cumsum(freq / SAMPLE_RATE) * 2 * np.pi
    signal = 0.7 * np.sin(phase)

    # Add rumble
    signal += 0.3 * np.sin(2 * np.pi * 60 * t)

    # Add crumbling noise
    rng = np.random.RandomState(99)
    noise = rng.uniform(-0.2, 0.2, n)
    noise_env = np.linspace(0.3, 1.0, n)
    signal += noise * noise_env

    env = _envelope(n, attack=0.01, decay=0.3)
    return signal * env


def make_select() -> np.ndarray:
    """Bright click — unit selection."""
    duration = 0.1
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # High-pitched blip
    signal = 0.6 * np.sin(2 * np.pi * 1000 * t) + 0.4 * np.sin(2 * np.pi * 1500 * t)

    env = np.exp(-t * 40) * _envelope(n, attack=0.002, decay=0.02)
    return signal * env


def make_turn_change() -> np.ndarray:
    """Two-tone chime — turn transition."""
    duration = 0.4
    n = int(SAMPLE_RATE * duration)
    half = n // 2

    # First tone (lower)
    t1 = np.linspace(0, duration / 2, half)
    tone1 = np.sin(2 * np.pi * 523 * t1)  # C5
    env1 = np.exp(-t1 * 8)

    # Second tone (higher)
    t2 = np.linspace(0, duration / 2, n - half)
    tone2 = np.sin(2 * np.pi * 659 * t2)  # E5
    env2 = np.exp(-t2 * 6)

    signal = np.concatenate([tone1 * env1, tone2 * env2])
    return signal * _envelope(n, attack=0.005, decay=0.15)


def make_move() -> np.ndarray:
    """Soft footstep — unit movement."""
    duration = 0.08
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Low thud
    signal = 0.5 * np.sin(2 * np.pi * 150 * t)

    # Noise burst
    rng = np.random.RandomState(77)
    noise = rng.uniform(-0.5, 0.5, n)
    signal += noise * np.exp(-t * 60)

    env = np.exp(-t * 30) * _envelope(n, attack=0.002, decay=0.01)
    return signal * env


def generate() -> list[Path]:
    """Generate all sound effects and return list of file paths."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sounds = {
        "sword_hit.wav": make_sword_hit(),
        "death.wav": make_death(),
        "select.wav": make_select(),
        "turn_change.wav": make_turn_change(),
        "move.wav": make_move(),
    }

    paths = []
    for name, samples in sounds.items():
        filepath = OUTPUT_DIR / name
        _write_wav(filepath, samples)
        print(f"Created {filepath}")
        paths.append(filepath)

    return paths


if __name__ == "__main__":
    generate()
