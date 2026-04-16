"""Properties of :class:`saga2d.Selector` — choose-one-of-N helper."""

from __future__ import annotations

import pytest

from saga2d import Selector


def test_initial_state() -> None:
    s = Selector(["a", "b", "c"])
    assert s.index == 0
    assert s.value == "a"
    assert len(s) == 3


def test_initial_index_param() -> None:
    s = Selector(["a", "b", "c"], initial=2)
    assert s.index == 2
    assert s.value == "c"


def test_initial_index_wraps_modulo() -> None:
    """``initial`` larger than the list length wraps around."""
    s = Selector(["a", "b", "c"], initial=5)
    assert s.index == 5 % 3


def test_next_wraps_at_end() -> None:
    s = Selector(["a", "b", "c"])
    assert s.next() == "b"
    assert s.next() == "c"
    assert s.next() == "a"  # wrapped
    assert s.index == 0


def test_prev_wraps_at_start() -> None:
    s = Selector(["a", "b", "c"])
    assert s.prev() == "c"  # wrapped
    assert s.index == 2


def test_set_index_direct_jump() -> None:
    s = Selector(["a", "b", "c", "d"])
    assert s.set_index(2) == "c"
    assert s.set_index(-1) == "d"  # -1 % 4 == 3


def test_options_is_immutable_view() -> None:
    """``.options`` returns a tuple — mutating it must not affect
    the selector's internal state."""
    s = Selector(["a", "b", "c"])
    view = s.options
    assert view == ("a", "b", "c")
    # Can't mutate a tuple; just make sure subsequent selector ops
    # still see the original list.
    s.next()
    assert s.options == ("a", "b", "c")


def test_replace_keeps_index_when_possible() -> None:
    s = Selector(["a", "b", "c"], initial=1)
    s.replace(["x", "y", "z", "w"])
    assert s.index == 1  # still in range
    assert s.value == "y"


def test_replace_clamps_index_when_shrunk() -> None:
    s = Selector(["a", "b", "c", "d"], initial=3)
    s.replace(["x", "y"])
    assert s.index == 1  # clamped from 3 to max valid (len 2 → 1)


def test_replace_reset_mode() -> None:
    s = Selector(["a", "b"], initial=1)
    s.replace(["x", "y", "z"], keep_index=False)
    assert s.index == 0


def test_empty_selector_raises_on_value_and_nav() -> None:
    s: Selector[str] = Selector([])
    assert len(s) == 0
    assert not s
    with pytest.raises(IndexError):
        _ = s.value
    with pytest.raises(IndexError):
        s.next()
    with pytest.raises(IndexError):
        s.prev()


def test_empty_replace_leaves_selector_unusable() -> None:
    s = Selector(["a", "b"])
    s.replace([])
    assert len(s) == 0
    assert not s
    with pytest.raises(IndexError):
        _ = s.value
