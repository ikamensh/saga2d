"""Generate Ring of Pain's three sound effects procedurally.

Pure stdlib: ``wave`` writes RIFF-WAVE, ``math.sin`` synthesises tones,
``struct`` packs 16-bit samples. No external asset downloads, no
third-party dependencies, no licensing concerns — these sounds are
the repo's own.

Run once from the project root::

    python scripts/generate_sfx.py

Produces ``assets/sounds/hit.wav``, ``coin.wav``, ``heal.wav``. The
three sounds each have a distinct timbre so the player can tell
which event fired without looking at the screen:

* ``hit``  — short descending sweep (600 Hz → 180 Hz), 120 ms,
              suggests impact.
* ``coin`` — two rising chirps (900 Hz then 1400 Hz), 80 ms each,
              bright pickup sound.
* ``heal`` — soft rising arpeggio (440 Hz → 659 Hz → 880 Hz),
              longer 240 ms, gentler envelope.
"""

from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path

SAMPLE_RATE = 22050  # cheap but clear
AMPLITUDE = 0.35     # leave headroom; games mix sounds


def _envelope(t: float, duration: float) -> float:
    """Quick attack, slow decay. 0..1 over the sound's lifetime."""
    attack = 0.005
    if t < attack:
        return t / attack
    release = duration - t
    return min(1.0, release * 6.0)


def _sweep(duration: float, f_start: float, f_end: float) -> list[int]:
    """Generate 16-bit PCM samples for a sine sweep with envelope."""
    samples: list[int] = []
    n = int(duration * SAMPLE_RATE)
    # Phase accumulated so frequency changes don't cause clicks.
    phase = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        # Linear frequency sweep.
        f = f_start + (f_end - f_start) * (i / n)
        phase += 2 * math.pi * f / SAMPLE_RATE
        env = _envelope(t, duration)
        value = AMPLITUDE * env * math.sin(phase)
        samples.append(int(max(-1.0, min(1.0, value)) * 32767))
    return samples


def _concat(segments: list[list[int]], silence_s: float = 0.0) -> list[int]:
    gap = [0] * int(silence_s * SAMPLE_RATE)
    out: list[int] = []
    for i, seg in enumerate(segments):
        out.extend(seg)
        if i != len(segments) - 1:
            out.extend(gap)
    return out


def _write_wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def generate(root: Path) -> None:
    sounds_dir = root / "assets" / "sounds"

    _write_wav(
        sounds_dir / "hit.wav",
        _sweep(duration=0.12, f_start=600, f_end=180),
    )
    _write_wav(
        sounds_dir / "coin.wav",
        _concat(
            [
                _sweep(duration=0.08, f_start=900, f_end=1100),
                _sweep(duration=0.08, f_start=1400, f_end=1600),
            ],
            silence_s=0.02,
        ),
    )
    _write_wav(
        sounds_dir / "heal.wav",
        _concat(
            [
                _sweep(duration=0.08, f_start=440, f_end=440),
                _sweep(duration=0.08, f_start=659, f_end=659),
                _sweep(duration=0.08, f_start=880, f_end=880),
            ],
        ),
    )

    print(f"Wrote 3 WAVs under {sounds_dir}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    generate(root)
