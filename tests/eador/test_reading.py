"""Game-owned complete-entry paging preserves content through measured reflow."""

import pytest


def test_reading_pages_preserve_order_budget_and_anchor():
    """Different measured text sizes keep the same first entry, without missing or duplicating content."""
    from eador.reading import reading_pages

    for heights in ([23, 78, 42, 65, 10], [29, 98, 53, 82, 13]):
        for anchor in range(len(heights)):
            pages, page = reading_pages(heights, 130, anchor=anchor, spacing=8, max_items=3)
            assert pages[page][0] == anchor
            assert [index for group in pages for index in group] == list(range(len(heights)))
            for group in pages:
                assert 1 <= len(group) <= 3
                assert sum(heights[index] for index in group) + 8 * (len(group) - 1) <= 130
    assert reading_pages([], 130) == (((),), 0)
    with pytest.raises(ValueError, match='entry 1'):
        reading_pages([30, 131], 130)
