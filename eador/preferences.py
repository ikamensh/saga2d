"""Shardbound's audio preferences, independent of campaign state and saves."""

from collections.abc import Mapping
from typing import Any

from saga2d import Game, Settings


DEFAULTS = {"master": .8, "music": .5, "sfx": .8, "muted": False}


def validate_preferences(values: Mapping[str, Any]) -> None:
    for channel in ("master", "music", "sfx"):
        value = values[channel]
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError(f"{channel.title()} volume must be a finite number between 0 and 1")
    if type(values["muted"]) is not bool:
        raise ValueError("Mute must be true or false")


def apply_preferences(game: Game, values: Mapping[str, Any]) -> None:
    """Apply validated preferences to the game's one audio manager."""
    validate_preferences(values)
    for channel in ("master", "music", "sfx"):
        game.audio.set_volume(channel, values[channel])
    game.audio.muted = values["muted"]


def load_preferences(game: Game) -> Settings:
    """Call before first playback; check the returned ``error`` to offer recovery.

    Invalid files stay intact. Their explicit error accompanies usable defaults
    in memory, so the title can present Settings without starting unsafe audio.
    """
    preferences = game.settings(DEFAULTS, validator=validate_preferences)
    apply_preferences(game, preferences)
    return preferences
