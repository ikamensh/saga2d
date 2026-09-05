"""Where Tribes' sound events go.

The scenes call :func:`play_sound` with an event name; ``__main__`` points
:data:`sound_hook` at the :class:`~tribes.sound.SoundBank` so it is heard,
while tests leave it ``None``.  The visual effects themselves live in
:mod:`saga2d.effects`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

#: ``play_sound(name)`` forwards here when set; ``None`` is silent.
sound_hook: Callable[[str], None] | None = None
volume_hook: Callable[[str, float], None] | None = None


def apply_volumes(settings: Mapping[str, Any]) -> None:
    """Push the ``music``/``sfx`` levels from a settings dict to the sound bank."""
    if volume_hook is not None:
        volume_hook("music", float(settings["music"]))
        volume_hook("sfx", float(settings["sfx"]))


def play_sound(name: str) -> None:
    """Sound event names used by the game: ``select move attack_hit attack_blocked
    attack_kill capture harvest level_up research train end_turn turn_start error
    victory defeat button``."""
    if sound_hook is not None:
        sound_hook(name)
