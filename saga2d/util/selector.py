"""Choose-one-of-N state helper.

Two saga2d example games (Ring of Pain, dial menu) each reinvent the
same pattern: a list of options and a current index that advances
with wraparound. :class:`Selector` wraps it::

    self.selector = Selector(["New Game", "Settings", "Quit"])
    self.selector.next()            # advance, wraps at end
    self.selector.prev()            # step back, wraps at start
    current = self.selector.value   # selected option
    index = self.selector.index     # 0-based index

Game code can bind a reactive :class:`~saga2d.Label` straight to
``selector.value`` — the same declarative-HUD pattern the rest of
saga2d uses::

    self.ui.add(Label(lambda: self.selector.value, text_style="heading"))
"""

from __future__ import annotations

from typing import Generic, Iterable, TypeVar

T = TypeVar("T")


class Selector(Generic[T]):
    """Stateful choose-one-of-N wrapper.

    Holds a list of options and a current index. Supports wraparound
    navigation (``next`` / ``prev``), direct index setting, and
    dynamic option list replacement (``replace``) that preserves a
    sensible index if possible.
    """

    __slots__ = ("_options", "_index")

    def __init__(
        self,
        options: Iterable[T],
        *,
        initial: int = 0,
    ) -> None:
        self._options: list[T] = list(options)
        if not self._options:
            self._index = 0
            return
        self._index = initial % len(self._options)

    # -- Properties --------------------------------------------------------

    @property
    def options(self) -> tuple[T, ...]:
        """Read-only view of the current option list."""
        return tuple(self._options)

    @property
    def index(self) -> int:
        """Current selection index (0-based). ``0`` when empty."""
        return self._index

    @property
    def value(self) -> T:
        """Currently selected option.

        Raises :class:`IndexError` when the selector is empty.
        """
        if not self._options:
            raise IndexError("Selector has no options")
        return self._options[self._index]

    def __len__(self) -> int:
        return len(self._options)

    def __bool__(self) -> bool:
        return bool(self._options)

    # -- Navigation --------------------------------------------------------

    def next(self) -> T:
        """Advance by one with wraparound. Returns the new value."""
        if not self._options:
            raise IndexError("Selector has no options")
        self._index = (self._index + 1) % len(self._options)
        return self._options[self._index]

    def prev(self) -> T:
        """Step back by one with wraparound. Returns the new value."""
        if not self._options:
            raise IndexError("Selector has no options")
        self._index = (self._index - 1) % len(self._options)
        return self._options[self._index]

    def set_index(self, i: int) -> T:
        """Jump to index *i* (modulo length). Returns the new value."""
        if not self._options:
            raise IndexError("Selector has no options")
        self._index = i % len(self._options)
        return self._options[self._index]

    # -- Mutation ----------------------------------------------------------

    def replace(
        self,
        options: Iterable[T],
        *,
        keep_index: bool = True,
    ) -> None:
        """Swap the option list.

        *keep_index* (default ``True``) preserves the current index
        clamped to the new list's length. Pass ``False`` to reset to
        zero — useful when the new list is semantically unrelated
        (e.g. descending to the next floor in a roguelike).
        """
        self._options = list(options)
        if not self._options:
            self._index = 0
            return
        if keep_index:
            self._index = min(self._index, len(self._options) - 1)
        else:
            self._index = 0
