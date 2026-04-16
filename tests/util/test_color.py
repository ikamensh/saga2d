"""Properties of the shared colour utility helpers."""

from __future__ import annotations

from saga2d.util.color import lighten


def test_lighten_with_factor_one_is_identity() -> None:
    c = (100, 120, 140, 200)
    assert lighten(c, 1.0) == c


def test_lighten_alpha_is_preserved() -> None:
    assert lighten((50, 50, 50, 42), 2.0)[3] == 42


def test_lighten_clamps_to_255() -> None:
    r, g, b, _ = lighten((200, 200, 200, 255), 2.0)
    assert (r, g, b) == (255, 255, 255)


def test_darken_by_half() -> None:
    r, g, b, a = lighten((100, 120, 140, 200), 0.5)
    assert (r, g, b, a) == (50, 60, 70, 200)


def test_negative_channels_never_produced() -> None:
    # Defensive: a wild factor of 0 should still produce a valid colour.
    assert lighten((10, 20, 30, 255), 0) == (0, 0, 0, 255)
