"""Procedural sound for Tribes.

There are no audio assets.  Every effect and the ambient loop are
synthesised with numpy the first time the game runs and cached as WAV
files next to the save games::

    ~/.tribes/sounds/<name>.wav     one file per SoundBank.play() name
    ~/.tribes/sounds/VERSION        SOUND_VERSION the cached files were made with
    ~/.tribes/music/ambient.wav     the 40 s stereo loop

Bump ``SOUND_VERSION`` after changing a generator; the bank regenerates
when the marker differs or a file is missing.  Everything is in D major
so effects blend with the music.

::

    bank = SoundBank(game)
    bank.play("attack_hit", pitch_variation=0.06)
    bank.start_music()
"""

from __future__ import annotations

import random
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

from saga2d import AssetManager, AudioManager, Game

SOUND_VERSION = "1"
SAMPLE_RATE = 44_100
MUSIC = "ambient"

# -- Synthesis ---------------------------------------------------------------

_NOTE_INDEX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

# Partials as (harmonic multiple, relative amplitude): the timbre of a tone.
SOFT = ((1, 1.0), (2, 0.3), (3, 0.1))                                # flute-like
GLASS = ((1, 1.0), (2, 0.5), (3, 0.28), (4, 0.14), (5, 0.07))        # electric-piano pluck
DARK = ((1, 1.0), (2, 0.15))                                         # muted, almost a sine
BELL = ((1, 1.0), (2, 0.45), (3, 0.25), (4.16, 0.12), (5.43, 0.05))  # a little inharmonic shimmer
PAD = ((1, 1.0), (2, 0.5), (3, 0.33), (4, 0.25))                     # saw-like, filtered by the LFO


def hz(note: str) -> float:
    """``"A4"`` → 440.0; sharps as ``"F#5"``."""
    midi = 12 * (int(note[-1]) + 1) + _NOTE_INDEX[note[:-1]]
    return 440.0 * 2 ** ((midi - 69) / 12)


def _time(seconds: float) -> np.ndarray:
    return np.arange(int(round(seconds * SAMPLE_RATE))) / SAMPLE_RATE


def envelope(seconds: float, attack: float, tau: float) -> np.ndarray:
    """Raised-cosine attack, exponential decay with time constant *tau*,
    and a 5 ms fade at the very end so no clip ends mid-cycle."""
    t = _time(seconds)
    env = np.ones_like(t)
    rising = t < attack
    env[rising] = 0.5 - 0.5 * np.cos(np.pi * t[rising] / attack)
    env[~rising] = np.exp(-(t[~rising] - attack) / tau)
    tail = min(len(t), int(0.005 * SAMPLE_RATE))
    env[-tail:] *= np.linspace(1.0, 0.0, tail)
    return env


def tone(note: str, seconds: float, *, attack: float = 0.005, tau: float = 0.1, partials=SOFT) -> np.ndarray:
    """A decaying note; higher partials die faster, as on a plucked string."""
    freq = hz(note)
    t = _time(seconds)
    out = np.zeros_like(t)
    for k, amp in partials:
        out += amp * envelope(seconds, attack, tau / (1 + 0.6 * (k - 1))) * np.sin(2 * np.pi * freq * k * t)
    return out / sum(amp for _, amp in partials)


def noise(seconds: float, low: float, high: float, *, attack: float = 0.002, tau: float = 0.03, seed: int = 0) -> np.ndarray:
    """Band-limited noise burst between *low* and *high* Hz (soft 8th-order edges)."""
    n = int(round(seconds * SAMPLE_RATE))
    spectrum = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    mask = np.zeros_like(freqs)
    f = freqs[1:]
    mask[1:] = 1 / (1 + (f / high) ** 8) / (1 + (low / f) ** 8)
    burst = np.fft.irfft(spectrum * mask, n)
    return burst / np.max(np.abs(burst)) * envelope(seconds, attack, tau)


def thump(f0: float, f1: float, seconds: float, *, attack: float = 0.002, tau: float = 0.05) -> np.ndarray:
    """A sine gliding exponentially from *f0* to *f1* Hz: drums and impacts."""
    t = _time(seconds)
    freq = f0 * (f1 / f0) ** (t / seconds)
    return np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * envelope(seconds, attack, tau)


def mix(*layers: np.ndarray | tuple[float, np.ndarray]) -> np.ndarray:
    """Sum mono clips; a ``(start_seconds, clip)`` pair places the clip later."""
    placed = [(0.0, layer) if isinstance(layer, np.ndarray) else layer for layer in layers]
    starts = [int(round(start * SAMPLE_RATE)) for start, _ in placed]
    out = np.zeros(max(start + len(clip) for start, (_, clip) in zip(starts, placed)))
    for start, (_, clip) in zip(starts, placed):
        out[start:start + len(clip)] += clip
    return out


def level(clip: np.ndarray, peak: float) -> np.ndarray:
    return clip * (peak / np.max(np.abs(clip)))


# -- Effects (mono, 50–600 ms, D major) --------------------------------------


def select() -> np.ndarray:
    """Two quick soft blips, a fourth apart."""
    return level(mix(tone("A5", 0.10, tau=0.05), (0.055, tone("D6", 0.16, tau=0.08))), 0.55)


def ui_click() -> np.ndarray:
    return level(mix(noise(0.035, 1800, 7000, tau=0.010, seed=1) * 0.5, tone("D6", 0.06, attack=0.002, tau=0.018)), 0.45)


def ui_hover() -> np.ndarray:
    return level(tone("F#6", 0.05, attack=0.01, tau=0.025, partials=DARK), 0.22)


def move() -> np.ndarray:
    """Three soft footsteps: low noise with a little weight underneath."""
    steps = []
    for i, (start, weight) in enumerate(((0.0, 1.0), (0.13, 0.75), (0.26, 0.9))):
        steps.append((start, noise(0.08, 120, 900, attack=0.004, tau=0.022, seed=10 + i) * weight))
        steps.append((start, thump(140, 70, 0.06, tau=0.02) * 0.5 * weight))
    return level(mix(*steps), 0.5)


def attack_hit() -> np.ndarray:
    return level(mix(
        thump(200, 50, 0.20, tau=0.07),
        noise(0.10, 600, 5000, tau=0.028, seed=20) * 0.8,
        (0.005, tone("D3", 0.18, tau=0.06, partials=DARK) * 0.4),
    ), 0.9)


def attack_blocked() -> np.ndarray:
    """Duller and shorter than a hit: the blow landed on a shield."""
    return level(mix(thump(130, 65, 0.15, tau=0.05) * 0.8, noise(0.07, 250, 1500, tau=0.02, seed=21) * 0.6), 0.6)


def unit_death() -> np.ndarray:
    """A falling A–F#–D over a low swell."""
    return level(mix(
        tone("A4", 0.30, attack=0.01, tau=0.14),
        (0.14, tone("F#4", 0.30, attack=0.01, tau=0.14)),
        (0.28, tone("D4", 0.32, attack=0.01, tau=0.16, partials=DARK)),
        noise(0.5, 90, 500, attack=0.12, tau=0.14, seed=30) * 0.35,
    ), 0.65)


def capture() -> np.ndarray:
    """Short fanfare: rising D-major arpeggio into a chord with a sparkle."""
    layers = [(start, tone(note, 0.20, tau=0.09, partials=GLASS)) for note, start in (("D5", 0.0), ("F#5", 0.08), ("A5", 0.16), ("D6", 0.24))]
    layers += [(0.32, tone(note, 0.28, attack=0.01, tau=0.16, partials=GLASS) * 0.7) for note in ("D5", "A5", "F#6")]
    layers.append((0.32, noise(0.08, 4000, 9000, tau=0.03, seed=40) * 0.15))
    return level(mix(*layers), 0.8)


def level_up() -> np.ndarray:
    """A quick pentatonic run up with a shimmer on top."""
    layers = [(i * 0.055, tone(note, 0.16, tau=0.07, partials=GLASS)) for i, note in enumerate(("D5", "E5", "F#5", "A5", "B5", "D6"))]
    layers.append((0.33, tone("F#6", 0.24, attack=0.01, tau=0.13) * 0.6))
    layers.append((0.33, tone("A6", 0.22, attack=0.01, tau=0.11) * 0.35))
    return level(mix(*layers), 0.7)


def research() -> np.ndarray:
    """Three bell tones opening up: D, A, B."""
    return level(mix(
        tone("D5", 0.32, attack=0.008, tau=0.18, partials=BELL),
        (0.10, tone("A5", 0.30, attack=0.008, tau=0.16, partials=BELL) * 0.8),
        (0.20, tone("B5", 0.34, attack=0.008, tau=0.20, partials=BELL) * 0.7),
    ), 0.65)


def train() -> np.ndarray:
    """Two soft hammer taps, A then D."""
    return level(mix(
        noise(0.05, 1200, 6000, tau=0.014, seed=50) * 0.6,
        tone("A4", 0.24, attack=0.003, tau=0.12, partials=GLASS),
        (0.12, tone("D5", 0.24, attack=0.003, tau=0.12, partials=GLASS) * 0.9),
        (0.12, noise(0.04, 1200, 6000, tau=0.012, seed=51) * 0.4),
    ), 0.7)


def harvest() -> np.ndarray:
    """A pluck and a pop with a little rustle."""
    return level(mix(
        noise(0.04, 300, 2500, tau=0.012, seed=60) * 0.6,
        tone("F#5", 0.14, attack=0.002, tau=0.05, partials=GLASS),
        (0.09, tone("A5", 0.16, attack=0.002, tau=0.06, partials=GLASS) * 0.8),
        (0.02, noise(0.18, 2500, 7000, attack=0.02, tau=0.05, seed=61) * 0.12),
    ), 0.6)


def end_turn() -> np.ndarray:
    """Settling: D down to A, doubled an octave below."""
    return level(mix(
        tone("D5", 0.26, attack=0.02, tau=0.13),
        tone("D4", 0.26, attack=0.02, tau=0.13, partials=DARK) * 0.5,
        (0.17, tone("A4", 0.30, attack=0.02, tau=0.16)),
        (0.17, tone("A3", 0.30, attack=0.02, tau=0.16, partials=DARK) * 0.5),
    ), 0.6)


def turn_start() -> np.ndarray:
    """The mirror of end_turn: A up to D, then a brighter F#."""
    return level(mix(
        tone("A4", 0.26, attack=0.015, tau=0.13),
        (0.15, tone("D5", 0.30, attack=0.015, tau=0.16)),
        (0.30, tone("F#5", 0.26, attack=0.015, tau=0.14, partials=GLASS) * 0.6),
    ), 0.6)


def error() -> np.ndarray:
    """A gentle "nope": E down to D, muted."""
    return level(mix(
        tone("E4", 0.13, attack=0.012, tau=0.07, partials=DARK),
        (0.12, tone("D4", 0.18, attack=0.012, tau=0.09, partials=DARK)),
    ), 0.45)


def victory() -> np.ndarray:
    """D–A–D leap into a full D-major chord."""
    layers = [(start, tone(note, 0.22, tau=0.10, partials=GLASS)) for note, start in (("D5", 0.0), ("A5", 0.09), ("D6", 0.18))]
    layers += [(0.28, tone(note, 0.32, attack=0.01, tau=0.20, partials=GLASS) * gain)
               for note, gain in (("D5", 0.8), ("F#5", 0.7), ("A5", 0.7), ("D6", 0.6), ("F#6", 0.4))]
    layers.append((0.28, noise(0.12, 4000, 10000, attack=0.005, tau=0.04, seed=70) * 0.15))
    return level(mix(*layers), 0.85)


def defeat() -> np.ndarray:
    """D, B♭, G: the major key turning minor, over a low swell."""
    return level(mix(
        tone("D5", 0.30, attack=0.02, tau=0.15),
        (0.16, tone("A#4", 0.30, attack=0.02, tau=0.15)),
        (0.32, tone("G4", 0.28, attack=0.02, tau=0.14, partials=DARK)),
        (0.32, tone("G3", 0.28, attack=0.02, tau=0.14, partials=DARK) * 0.5),
        noise(0.55, 80, 400, attack=0.15, tau=0.18, seed=80) * 0.3,
    ), 0.65)


SOUNDS: dict[str, Callable[[], np.ndarray]] = {
    "select": select, "move": move, "attack_hit": attack_hit, "attack_blocked": attack_blocked,
    "unit_death": unit_death, "capture": capture, "level_up": level_up, "research": research,
    "train": train, "harvest": harvest, "end_turn": end_turn, "turn_start": turn_start,
    "error": error, "victory": victory, "defeat": defeat, "ui_click": ui_click, "ui_hover": ui_hover,
}

# -- Music -------------------------------------------------------------------

BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
PROGRESSION: tuple[tuple[int, tuple[str, ...]], ...] = (  # (bars, chord low→high); 12 bars = 40 s
    (2, ("D3", "A3", "D4", "F#4", "A4", "C#5")),    # Dmaj7
    (2, ("B2", "F#3", "B3", "D4", "F#4", "A4")),    # Bm7
    (2, ("G2", "D3", "G3", "B3", "D4", "F#4")),     # Gmaj7
    (2, ("A2", "E3", "A3", "C#4", "E4", "B4")),     # Aadd9
    (1, ("F#2", "C#3", "F#3", "A3", "C#4", "E4")),  # F#m7
    (1, ("G2", "D3", "G3", "B3", "D4", "F#4")),     # Gmaj7
    (1, ("E3", "B3", "E4", "G4", "B4", "D5")),      # Em7
    (1, ("A2", "E3", "A3", "D4", "G4", "B4")),      # A7sus4 → back to D
)
LOOP_SECONDS = sum(bars for bars, _ in PROGRESSION) * BAR
_CROSSFADE = 1.6
_ARPEGGIO = (0, 2, 1, 3, 2, 1, 0, 2)  # eighth-note pattern over the chord's top four notes


def _add_wrapped(out: np.ndarray, clip: np.ndarray, start_seconds: float) -> None:
    """Add a stereo clip into the loop buffer at *start_seconds*, wrapping past the end."""
    n = len(out)
    start = int(round(start_seconds * SAMPLE_RATE)) % n
    first = min(len(clip), n - start)
    out[start:start + first] += clip[:first]
    out[:len(clip) - first] += clip[first:]


def _pad(chord: tuple[str, ...], seconds: float, t0: float) -> np.ndarray:
    """Detuned stereo pad with an equal-power crossfade at both ends and a
    brightness LFO (two cycles per loop) that opens and closes the harmonics."""
    t = _time(seconds)
    fade_in = np.sin(np.minimum(1.0, t / _CROSSFADE) * np.pi / 2)
    fade_out = np.sin(np.minimum(1.0, (seconds - t) / _CROSSFADE) * np.pi / 2)
    env = fade_in * fade_out
    bright = 0.5 + 0.5 * np.sin(2 * np.pi * (t0 + t) / (LOOP_SECONDS / 2))
    gains = [amp * k ** -(1.3 * (1 - bright)) for k, amp in PAD]
    out = np.zeros((len(t), 2))
    for note in chord:
        freq = hz(note)
        for (k, _), gain in zip(PAD, gains):
            for channel, detune in ((0, 1.0015), (1, 0.9985)):
                out[:, channel] += gain * np.sin(2 * np.pi * freq * k * detune * t)
    root = hz(chord[0]) / 2
    out += 0.35 * np.sin(2 * np.pi * root * t)[:, None]
    return out * (env / len(chord))[:, None]


def _pluck(note: str, pan: float, velocity: float) -> np.ndarray:
    clip = tone(note, 0.9, attack=0.003, tau=0.35, partials=GLASS) * velocity
    angle = (pan + 1) * np.pi / 4
    return np.stack([clip * np.cos(angle), clip * np.sin(angle)], axis=1)


def ambient() -> np.ndarray:
    """The seamless 40 s loop: pads over a I–vi–IV–V progression, a sub
    root, a sparse pluck arpeggio, and a slow swell — stereo, quiet."""
    n = int(round(LOOP_SECONDS * SAMPLE_RATE))
    out = np.zeros((n, 2))
    rng = random.Random(7)
    start = 0.0
    for bars, chord in PROGRESSION:
        length = bars * BAR
        _add_wrapped(out, _pad(chord, length + _CROSSFADE, start - _CROSSFADE / 2), start - _CROSSFADE / 2)
        top = [note[:-1] + str(int(note[-1]) + 1) for note in chord[2:]]
        for eighth in range(bars * 8):
            if rng.random() < 0.3:
                continue
            velocity = (1.0 if eighth % 4 == 0 else 0.7) * rng.uniform(0.75, 1.0)
            _add_wrapped(out, 0.28 * _pluck(top[_ARPEGGIO[eighth % 8]], 0.6 * np.sin(eighth * 1.3), velocity), start + eighth * BEAT / 2)
        start += length
    swell = 0.85 + 0.15 * np.sin(2 * np.pi * _time(LOOP_SECONDS) / (LOOP_SECONDS / 4))
    return level(out * swell[:, None], 0.45)


# -- Cache -------------------------------------------------------------------


def sound_files(data_dir: Path) -> list[Path]:
    """Every WAV the bank expects under *data_dir*."""
    return [data_dir / "sounds" / f"{name}.wav" for name in SOUNDS] + [data_dir / "music" / f"{MUSIC}.wav"]


def is_generated(data_dir: Path) -> bool:
    marker = data_dir / "sounds" / "VERSION"
    return marker.exists() and marker.read_text() == SOUND_VERSION and all(path.exists() for path in sound_files(data_dir))


def generate(data_dir: Path) -> None:
    """Synthesise every effect and the loop into *data_dir*, overwriting.
    The VERSION marker is written last so an interrupted run regenerates."""
    for name, make in SOUNDS.items():
        write_wav(data_dir / "sounds" / f"{name}.wav", make())
    write_wav(data_dir / "music" / f"{MUSIC}.wav", ambient())
    (data_dir / "sounds" / "VERSION").write_text(SOUND_VERSION)


def write_wav(path: Path, samples: np.ndarray) -> None:
    """16-bit PCM at SAMPLE_RATE; *samples* in [-1, 1], shape ``(n,)`` or ``(n, channels)``."""
    pcm = np.clip(np.round(samples * 32767), -32768, 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm.tobytes())


# -- Bank --------------------------------------------------------------------


#: Scene event names that map onto a differently named effect.
ALIASES = {"attack_kill": "unit_death", "button": "ui_click"}


class SoundBank:
    """The game's sounds, played through its own :class:`AudioManager`.

    *data_dir* defaults to ``~/.tribes``; the WAVs are generated there on
    first use (see the module docstring for the layout).
    """

    def __init__(self, game: Game, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else Path.home() / ".tribes"
        if not is_generated(self.data_dir):
            generate(self.data_dir)
        self._audio = AudioManager(game.backend, AssetManager(game.backend, base_path=self.data_dir))
        self._rng = random.Random(0)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(SOUNDS)

    def play(self, name: str, *, pitch_variation: float = 0.0) -> None:
        """Play effect *name*.  *pitch_variation* 0.05 shifts the pitch by up
        to ±5 % so a repeated effect does not sound stamped out."""
        name = ALIASES.get(name, name)
        if name not in SOUNDS:
            raise KeyError(f"Unknown sound {name!r}. Sounds: {', '.join(SOUNDS)}")
        pitch = 1.0 + self._rng.uniform(-pitch_variation, pitch_variation) if pitch_variation else 1.0
        self._audio.play_sound(name, pitch=pitch)

    def start_music(self) -> None:
        """Start the ambient loop; a no-op while it is already playing."""
        if self._audio.music_name != MUSIC:
            self._audio.play_music(MUSIC, loop=True)

    def stop_music(self) -> None:
        self._audio.stop_music()

    @property
    def music_playing(self) -> bool:
        return self._audio.music_name == MUSIC

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
