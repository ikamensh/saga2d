"""Compose original audio as NumPy samples and write ordinary WAV assets.

Pure synthesis helpers shared by Tribes, Warband and Shardbound. Sound names,
compositions, cache/build policy and playback belong to callers. See
``tools/demo_synth.py`` for a composition playable through ``game.audio``.
"""

from __future__ import annotations

from pathlib import Path
import wave

import numpy as np

SAMPLE_RATE = 44_100

_NOTE_INDEX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

# Partials as (harmonic multiple, relative amplitude): the timbre of a tone.
SOFT = ((1, 1.0), (2, 0.3), (3, 0.1))                                # flute-like
GLASS = ((1, 1.0), (2, 0.5), (3, 0.28), (4, 0.14), (5, 0.07))        # electric-piano pluck
DARK = ((1, 1.0), (2, 0.15))                                         # muted, almost a sine
BELL = ((1, 1.0), (2, 0.45), (3, 0.25), (4.16, 0.12), (5.43, 0.05))  # a little inharmonic shimmer
PAD = ((1, 1.0), (2, 0.5), (3, 0.33), (4, 0.25))                     # saw-like
BRASS = ((1, 1.0), (2, 0.7), (3, 0.55), (4, 0.4), (5, 0.3), (6, 0.2))  # bright, for horns


def hz(note: str) -> float:
    """``"A4"`` → 440.0; sharps as ``"F#5"``."""
    midi = 12 * (int(note[-1]) + 1) + _NOTE_INDEX[note[:-1]]
    return 440.0 * 2 ** ((midi - 69) / 12)


def seconds(count: float) -> np.ndarray:
    """Sample times for *count* seconds."""
    return np.arange(int(round(count * SAMPLE_RATE))) / SAMPLE_RATE


def envelope(length: float, attack: float, tau: float) -> np.ndarray:
    """Raised-cosine attack, exponential decay with time constant *tau*,
    and a 5 ms fade at the very end so no clip ends mid-cycle."""
    t = seconds(length)
    env = np.ones_like(t)
    rising = t < attack
    env[rising] = 0.5 - 0.5 * np.cos(np.pi * t[rising] / attack)
    env[~rising] = np.exp(-(t[~rising] - attack) / tau)
    tail = min(len(t), int(0.005 * SAMPLE_RATE))
    env[-tail:] *= np.linspace(1.0, 0.0, tail)
    return env


def tone(note: str | float, length: float, *, attack: float = 0.005, tau: float = 0.1, partials=SOFT) -> np.ndarray:
    """A decaying note (a name or a frequency); higher partials die faster, as on a plucked string."""
    freq = hz(note) if isinstance(note, str) else float(note)
    t = seconds(length)
    out = np.zeros_like(t)
    for k, amp in partials:
        out += amp * envelope(length, attack, tau / (1 + 0.6 * (k - 1))) * np.sin(2 * np.pi * freq * k * t)
    return out / sum(amp for _, amp in partials)


def noise(length: float, low: float, high: float, *, attack: float = 0.002, tau: float = 0.03, seed: int = 0) -> np.ndarray:
    """Band-limited noise burst between *low* and *high* Hz (soft 8th-order edges)."""
    n = int(round(length * SAMPLE_RATE))
    spectrum = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    mask = np.zeros_like(freqs)
    f = freqs[1:]
    mask[1:] = 1 / (1 + (f / high) ** 8) / (1 + (low / f) ** 8)
    burst = np.fft.irfft(spectrum * mask, n)
    return level(burst, 1) * envelope(length, attack, tau)


def thump(f0: float, f1: float, length: float, *, attack: float = 0.002, tau: float = 0.05) -> np.ndarray:
    """A sine gliding exponentially from *f0* to *f1* Hz: drums and impacts."""
    t = seconds(length)
    freq = f0 * (f1 / f0) ** (t / length)
    return np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * envelope(length, attack, tau)


def mix(*layers: np.ndarray | tuple[float, np.ndarray]) -> np.ndarray:
    """Sum clips (mono or stereo alike); a ``(start_seconds, clip)`` pair places the clip later."""
    placed = [(0.0, layer) if isinstance(layer, np.ndarray) else layer for layer in layers]
    starts = [int(round(start * SAMPLE_RATE)) for start, _ in placed]
    stereo = any(clip.ndim == 2 for _, clip in placed)
    length = max(start + len(clip) for start, (_, clip) in zip(starts, placed))
    out = np.zeros((length, 2) if stereo else length)
    for start, (_, clip) in zip(starts, placed):
        if stereo and clip.ndim == 1:
            clip = np.stack([clip, clip], axis=1)
        out[start:start + len(clip)] += clip
    return out


def level(clip: np.ndarray, peak: float) -> np.ndarray:
    """Scale so the loudest sample is *peak*, rejecting silence or nonfinite data."""
    if not np.isfinite(peak) or not 0 <= peak <= 1:
        raise ValueError("Peak must be finite and between 0 and 1")
    magnitude = np.max(np.abs(clip))
    if not np.isfinite(magnitude) or magnitude == 0:
        raise ValueError("Cannot normalize a silent or nonfinite clip")
    return clip * (peak / magnitude)


def pan(clip: np.ndarray, position: float) -> np.ndarray:
    """Mono → stereo with equal-power panning; *position* −1 (left) … 1 (right)."""
    angle = (position + 1) * np.pi / 4
    return np.stack([clip * np.cos(angle), clip * np.sin(angle)], axis=1)


def write_wav(path: Path, samples: np.ndarray) -> None:
    """Write nonempty mono/stereo 16-bit PCM; invalid samples leave an existing file intact.

    Samples must be finite and in [-1, 1], shaped ``(n,)``, ``(n, 1)`` or
    ``(n, 2)``. Use ``level`` before writing if a mix exceeds that range.
    """
    if samples.ndim not in (1, 2) or not samples.size or (samples.ndim == 2 and samples.shape[1] not in (1, 2)):
        raise ValueError("WAV samples must be a nonempty mono or stereo clip")
    if not np.all(np.isfinite(samples)) or np.max(np.abs(samples)) > 1:
        raise ValueError("WAV samples must be finite and between -1 and 1")
    pcm = np.round(samples * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm.tobytes())
