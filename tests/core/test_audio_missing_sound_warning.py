"""iter-35: AudioManager warns when an optional sound is missing.

Parallels iter-30's AssetManager font-registration warning. Silent
fallback on ``play_sound(name, optional=True)`` was the iter-1..34
default and made "why is there no sound" genuinely hard to diagnose.
A ``RuntimeWarning`` keeps the fallback contract (returns None rather
than raising) while letting the developer notice.
"""

from __future__ import annotations

import warnings

import pytest

from saga2d import Game


def _game() -> Game:
    return Game(
        "audio-warn-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )


def test_missing_optional_sound_emits_runtime_warning() -> None:
    game = _game()
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            game.audio.play_sound("does_not_exist", optional=True)
        assert len(captured) == 1
        assert issubclass(captured[0].category, RuntimeWarning)
        msg = str(captured[0].message)
        assert "does_not_exist" in msg
        assert "optional" in msg.lower() or "no-op" in msg.lower()
    finally:
        game._teardown()


def test_missing_nonoptional_sound_still_raises() -> None:
    """``optional=False`` (the default) keeps the original
    AssetNotFoundError contract — iter-35 only softens the
    optional path."""
    from saga2d import AssetNotFoundError

    game = _game()
    try:
        with pytest.raises(AssetNotFoundError):
            game.audio.play_sound("does_not_exist", optional=False)
    finally:
        game._teardown()


def test_present_optional_sound_emits_no_warning() -> None:
    """If the sound exists, ``optional=True`` plays it normally with
    no warning."""
    game = _game()
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            # 'hit' exists — bundled procedurally in iter-32.
            game.audio.play_sound("hit", optional=True)
        runtime_warnings = [
            w for w in captured if issubclass(w.category, RuntimeWarning)
        ]
        assert runtime_warnings == []
    finally:
        game._teardown()


def test_mock_backend_records_nothing_on_missing_optional() -> None:
    """Fallback contract unchanged — no backend play_sound call when
    the asset is missing and optional=True."""
    game = _game()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            game.audio.play_sound("does_not_exist", optional=True)
        assert game.backend.sounds_played == []
    finally:
        game._teardown()
