"""Shardbound's whole-entry reading policy; layout and controls stay in each screen."""

import math
from collections.abc import Sequence


def reading_pages(heights: Sequence[float], available: float, *, anchor: int = 0,
                  spacing: float = 0, max_items: int | None = None) -> tuple[tuple[tuple[int, ...], ...], int]:
    """Pack complete entries and keep ``anchor`` first on its resulting page.

    Returns immutable index pages and the selected page index. Empty content has
    one empty page. An anchor beyond shortened content selects its last entry.
    Heights come from attached UI measurements; callers own their content budget,
    overflow context and any limit imposed by visible number shortcuts.
    """
    if not math.isfinite(available) or available <= 0 or not math.isfinite(spacing) or spacing < 0:
        raise ValueError('Reading space must be positive and spacing nonnegative, both finite.')
    if type(anchor) is not int or anchor < 0:
        raise ValueError('Reading anchor must be a nonnegative integer.')
    if max_items is not None and (type(max_items) is not int or max_items <= 0):
        raise ValueError('Reading page item limit must be a positive integer.')
    for index, height in enumerate(heights):
        if not math.isfinite(height) or height < 0 or height > available:
            raise ValueError(f'Reading entry {index} has invalid height {height} for available space {available}.')

    def pack(start, stop):
        pages, current, height = [], [], 0
        for index in range(start, stop):
            size = heights[index]
            if current and (height + spacing + size > available or len(current) == max_items):
                pages.append(tuple(current))
                current, height = [], 0
            height += (spacing if current else 0) + size
            current.append(index)
        return pages + ([tuple(current)] if current else [])

    anchor = min(anchor, max(0, len(heights) - 1))
    prefix = pack(0, anchor)
    return tuple(prefix + pack(anchor, len(heights))) or ((),), len(prefix)
