"""Procedural sound: a few synthesis primitives and a bank that caches the
results as WAV files and plays them through :class:`~saga2d.audio.AudioManager`.

A game describes each effect as a function returning samples in ``[-1, 1]``
(mono ``(n,)`` or stereo ``(n, 2)`` at :data:`SAMPLE_RATE`), built from
:func:`tone`, :func:`noise`, :func:`thump`, :func:`mix` and :func:`level`::

    def hit() -> np.ndarray:
        return level(mix(thump(200, 50, 0.2), noise(0.1, 600, 5000, seed=1) * 0.8), 0.9)

    bank = SynthBank(game, "~/.mygame", version="1", sounds={"hit": hit}, music={"theme": theme})
    bank.play("hit", pitch_variation=0.06)
    bank.start_music("theme")

The WAVs are written under ``<data_dir>/sounds`` and ``<data_dir>/music``
on first use, with a ``VERSION`` marker written last so an interrupted
run regenerates; bump the version after changing a generator.
"""

from __future__ import annotations

import random
import wave
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from saga2d.assets import AssetManager
from saga2d.audio import AudioManager

if TYPE_CHECKING:
    from saga2d.game import Game

SAMPLE_RATE = 44_100
Generator = Callable[[], np.ndarray]

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
    return burst / np.max(np.abs(burst)) * envelope(length, attack, tau)


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
    """Scale so the loudest sample is *peak*."""
    return clip * (peak / np.max(np.abs(clip)))


def pan(clip: np.ndarray, position: float) -> np.ndarray:
    """Mono → stereo with equal-power panning; *position* −1 (left) … 1 (right)."""
    angle = (position + 1) * np.pi / 4
    return np.stack([clip * np.cos(angle), clip * np.sin(angle)], axis=1)


def write_wav(path: Path, samples: np.ndarray) -> None:
    """16-bit PCM at SAMPLE_RATE; *samples* in [-1, 1], shape ``(n,)`` or ``(n, channels)``."""
    pcm = np.clip(np.round(samples * 32767), -32768, 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm.tobytes())


# -- Cache -------------------------------------------------------------------


def sound_files(data_dir: Path, sounds: Mapping[str, Generator], music: Mapping[str, Generator]) -> list[Path]:
    """Every WAV a bank with these generators expects under *data_dir*."""
    return [data_dir / "sounds" / f"{name}.wav" for name in sounds] + [data_dir / "music" / f"{name}.wav" for name in music]


def is_generated(data_dir: Path, version: str, sounds: Mapping[str, Generator], music: Mapping[str, Generator]) -> bool:
    marker = data_dir / "sounds" / "VERSION"
    return marker.exists() and marker.read_text() == version and all(path.exists() for path in sound_files(data_dir, sounds, music))


def generate(data_dir: Path, version: str, sounds: Mapping[str, Generator], music: Mapping[str, Generator]) -> None:
    """Synthesise every effect and track into *data_dir*, overwriting; the
    VERSION marker is written last so an interrupted run regenerates."""
    for name, make in sounds.items():
        write_wav(data_dir / "sounds" / f"{name}.wav", make())
    for name, make in music.items():
        write_wav(data_dir / "music" / f"{name}.wav", make())
    (data_dir / "sounds" / "VERSION").write_text(version)


# -- Bank --------------------------------------------------------------------


class SynthBank:
    """A game's sounds, generated on first use and played through its own :class:`AudioManager`.

    Parameters:
        game:     The game whose backend plays the audio.
        data_dir: Where the WAVs are cached (``~/.<game>`` is the usual place).
        version:  Bump after changing a generator; a different marker regenerates everything.
        sounds:   Effect name → generator.
        music:    Track name → generator (loops; stereo welcome).
        aliases:  Extra event names mapped onto effects.
    """

    def __init__(
        self, game: Game, data_dir: Path | str, *, version: str, sounds: Mapping[str, Generator],
        music: Mapping[str, Generator] | None = None, aliases: Mapping[str, str] | None = None,
    ) -> None:
        self.data_dir = Path(data_dir).expanduser()
        self.version = version
        self.sounds = dict(sounds)
        self.music = dict(music or {})
        self.aliases = dict(aliases or {})
        if not is_generated(self.data_dir, version, self.sounds, self.music):
            generate(self.data_dir, version, self.sounds, self.music)
        self._audio = AudioManager(game.backend, AssetManager(game.backend, base_path=self.data_dir))
        self._rng = random.Random(0)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.sounds)

    def play(self, name: str, *, pitch_variation: float = 0.0, volume: float = 1.0) -> None:
        """Play effect *name*.  *pitch_variation* 0.05 shifts the pitch by up
        to ±5 % so a repeated effect does not sound stamped out."""
        name = self.aliases.get(name, name)
        if name not in self.sounds:
            raise KeyError(f"Unknown sound {name!r}. Sounds: {', '.join(self.sounds)}")
        pitch = 1.0 + self._rng.uniform(-pitch_variation, pitch_variation) if pitch_variation else 1.0
        self._audio.play_sound(name, pitch=pitch, volume=volume)

    def start_music(self, name: str) -> None:
        """Start a track looping; a no-op while that track is already playing."""
        if name not in self.music:
            raise KeyError(f"Unknown track {name!r}. Tracks: {', '.join(self.music)}")
        if self._audio.music_name != name:
            self._audio.play_music(name, loop=True)

    def stop_music(self) -> None:
        self._audio.stop_music()

    @property
    def music_playing(self) -> str | None:
        return self._audio.music_name

    def set_volume(self, channel: str, level: float) -> None:
        """*channel* is ``"master"``, ``"music"`` or ``"sfx"``; *level* 0–1."""
        self._audio.set_volume(channel, level)

    def get_volume(self, channel: str) -> float:
        return self._audio.get_volume(channel)

    @property
    def muted(self) -> bool:
        return self._audio.muted

    @muted.setter
    def muted(self, value: bool) -> None:
        self._audio.muted = value
