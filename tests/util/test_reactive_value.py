"""Properties of :class:`saga2d.util.reactive.ReactiveValue`.

This helper is the foundation for reactive widget bindings (Label text,
ProgressBar value). Tests verify binding semantics in isolation — so
refactoring widgets on top doesn't regress behaviour.
"""

from __future__ import annotations

from saga2d.util.reactive import ReactiveValue


def test_static_value_returns_unchanged() -> None:
    rv: ReactiveValue[int] = ReactiveValue(42, default=0)
    assert rv.value == 42
    assert rv.refresh() is False
    assert rv.value == 42


def test_callable_refreshes() -> None:
    state = {"n": 0}
    rv: ReactiveValue[int] = ReactiveValue(lambda: state["n"], default=0)
    assert rv.value == 0  # pre-refresh, default
    rv.refresh()
    assert rv.value == 0
    state["n"] = 7
    assert rv.refresh() is True
    assert rv.value == 7


def test_refresh_returns_true_only_on_change() -> None:
    state = {"n": 1}
    rv: ReactiveValue[int] = ReactiveValue(lambda: state["n"], default=0)
    rv.refresh()
    assert rv.refresh() is False  # same value
    state["n"] = 2
    assert rv.refresh() is True
    assert rv.refresh() is False  # value stable at 2


def test_explicit_set_unbinds_callable() -> None:
    calls = {"n": 0}

    def read() -> str:
        calls["n"] += 1
        return "live"

    rv = ReactiveValue(read, default="")
    rv.refresh()
    assert rv.value == "live"
    assert rv.is_reactive

    rv.set("frozen")
    assert not rv.is_reactive
    before = calls["n"]
    rv.refresh()  # no callable to fire
    rv.refresh()
    assert calls["n"] == before
    assert rv.value == "frozen"


def test_on_change_callback_fires_on_refresh() -> None:
    history: list[tuple[int, int]] = []
    state = {"n": 10}
    rv = ReactiveValue(
        lambda: state["n"],
        default=0,
        on_change=lambda old, new: history.append((old, new)),
    )
    rv.refresh()  # 0 -> 10
    state["n"] = 10  # unchanged
    rv.refresh()
    state["n"] = 11
    rv.refresh()  # 10 -> 11
    assert history == [(0, 10), (10, 11)]


def test_on_change_fires_on_explicit_set() -> None:
    history: list[tuple[str, str]] = []
    rv = ReactiveValue("a", default="", on_change=lambda o, n: history.append((o, n)))
    rv.set("b")
    rv.set("b")  # same value, no fire
    rv.set("c")
    assert history == [("a", "b"), ("b", "c")]
