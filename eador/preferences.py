"""Shardbound's presentation preferences, independent of campaign state and saves."""

from collections.abc import Mapping
from typing import Any

from saga2d import Game, Settings


WINDOW_SIZES = ((960, 600), (1280, 720), (1280, 800), (1600, 900), (1920, 1080))
DEFAULTS = {"master": .8, "music": .5, "sfx": .8, "muted": False,
            "window_size": [1280, 800], "fullscreen": False, "reduced_motion": False}


def validate_preferences(values: Mapping[str, Any]) -> None:
    for channel in ("master", "music", "sfx"):
        value = values[channel]
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError(f"{channel.title()} volume must be a finite number between 0 and 1")
    for key in ("muted", "fullscreen", "reduced_motion"):
        if type(values[key]) is not bool:
            raise ValueError(f"{key.replace('_', ' ').title()} must be true or false")
    size = values["window_size"]
    if (type(size) is not list or len(size) != 2
            or any(type(value) is not int or not 1 <= value <= 16384 for value in size)):
        raise ValueError("Window size must contain two integer dimensions between 1 and 16384")


def apply_preferences(game: Game, values: Mapping[str, Any]) -> None:
    """Apply live audio/motion values; display changes are explicit and separate."""
    validate_preferences(values)
    for channel in ("master", "music", "sfx"):
        game.audio.set_volume(channel, values[channel])
    game.audio.muted = values["muted"]
    game._shardbound_reduced_motion = values["reduced_motion"]


def reduced_motion(game: Game) -> bool:
    """Whether game-owned action feedback should stay still, including live previews."""
    return getattr(game, "_shardbound_reduced_motion", DEFAULTS["reduced_motion"])


def apply_display_preferences(game: Game, values: Mapping[str, Any]) -> None:
    """Apply one explicit display request, preserving the fixed logical canvas."""
    validate_preferences(values)
    size = tuple(values["window_size"])
    if game.windowed_size != size:
        game.set_window_size(size)
    game.set_fullscreen(values["fullscreen"])


def load_preferences(game: Game) -> Settings:
    """Apply sound/motion only; check the returned ``error`` to offer recovery.

    ``create_game`` applies saved display once. Scene entries may call this helper
    without undoing a player's later native window resize or fullscreen change.

    Invalid files stay intact. Their explicit error accompanies usable defaults
    in memory, so the title can present Settings without starting unsafe audio.
    """
    preferences = game.settings(DEFAULTS, validator=validate_preferences)
    apply_preferences(game, preferences)
    return preferences
