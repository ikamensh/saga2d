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


def test_long_prose_pages_preserve_every_character_and_fit_actual_scene_measurement():
    """Explicit newlines, spaces and overlong path tokens survive measured 100/125 reflow exactly."""
    from saga2d import Game, Label, Scene
    from eador.reading import reading_text_pages
    game = Game('Reading prose', backend='mock')
    try:
        scene = Scene(); game.push(scene)
        text = 'Cannot read file\n\n' + '/ordinary-directory' * 60 + '.json: Is a directory.\nTry another slot.  '
        for font_size in (16, 20):
            def measure(text):
                return scene.measure(Label(text, width=240, wrap=True, font_size=font_size))[1]
            pages = reading_text_pages(text, 120, measure=measure)
            assert len(pages) > 2 and ''.join(pages) == text
            assert pages[0].startswith('Cannot read file\n\n/ordinary-directory')
            assert all(page and measure(page) <= 120 for page in pages)
        assert reading_text_pages('', 120, measure=measure) == ('',)
        with pytest.raises(ValueError, match='character'):
            reading_text_pages('Cannot fit', 1, measure=measure)
    finally:
        game._teardown()
