"""AI-powered visual verification for Menu Tutorial example.

This test verifies the visual quality of the menugame example using
AI-driven semantic checks. It addresses the specific issues mentioned
in goal.md about the main menu.

Run from project root::

    # Without AI (fallback mode, auto-pass)
    pytest tests/visual_verify/test_menu_tutorial_ai.py -v

    # With AI verification (requires ANTHROPIC_API_KEY)
    export ANTHROPIC_API_KEY=your_key_here
    pytest tests/visual_verify/test_menu_tutorial_ai.py -v

Key visual issues from goal.md to verify:
- Title "Main Menu" is NOT clipped by panel boundaries
- NOT "gray on gray on gray" - needs visual hierarchy
- NOT flat rectangles - needs visual depth
- NOT white background outside panel
- Buttons are NOT oversized relative to their text
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.screenshot.harness import render_scene
from tests.visual_verify import check_image

# Import MenuScene from the example
_MENU_DIR = Path(__file__).resolve().parents[2] / "examples" / "menugame"


def _load_menu_scene():
    """Import MenuScene from menugame example."""
    # Clear sys.modules to avoid conflicts with other main.py files
    if "main" in sys.modules:
        del sys.modules["main"]

    added = False
    if str(_MENU_DIR) not in sys.path:
        sys.path.insert(0, str(_MENU_DIR))
        added = True
    try:
        from main import MenuScene  # type: ignore[import-not-found]

        return MenuScene
    finally:
        if added and str(_MENU_DIR) in sys.path:
            sys.path.remove(str(_MENU_DIR))
        # Clean up module
        if "main" in sys.modules:
            del sys.modules["main"]


# Output directory for manual inspection
_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Test: Menu Title Not Clipped
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_title_not_clipped() -> None:
    """Verify that the menu title is not clipped by panel boundaries.

    Goal.md issue: "Title 'Main Menu' is CLIPPED — the top of the text is
    cut off by the panel boundary."

    This is a critical usability issue that must be fixed.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_title_clipping.png")

    checks = [
        "The title text at the top of the menu is fully visible without being cut off",
        "No text is clipped or truncated by panel boundaries",
        "The title has adequate spacing from the panel edge",
        "All letters in the title are completely visible",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, f"CRITICAL: {assertion}\n  Reasoning: {result.reasoning}"


# ---------------------------------------------------------------------------
# Test: Visual Hierarchy (Not Gray on Gray)
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_visual_hierarchy() -> None:
    """Verify that the menu has clear visual hierarchy, not "gray on gray on gray".

    Goal.md issue: "Gray on gray on gray — panel is medium gray, buttons are
    slightly darker gray, text is light gray/white. Zero visual hierarchy."

    The menu should have distinct visual levels.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_visual_hierarchy.png")

    checks = [
        "The menu has clear visual hierarchy with the title standing out from buttons",
        "Panel, buttons, and text have distinct colors that create visual separation",
        "The color palette is not monotonous gray tones",
        "Interactive elements (buttons) are visually distinct from static elements (labels)",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual hierarchy check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Visual Depth (Not Flat Rectangles)
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_visual_depth() -> None:
    """Verify that the menu has visual depth, not just flat rectangles.

    Goal.md issue: "No visual depth — everything is flat rectangles. No borders,
    no shadows, no rounded corners."

    The menu should have some visual polish beyond flat shapes.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_visual_depth.png")

    checks = [
        "UI elements have visual depth or dimensionality (not completely flat)",
        "Panel and buttons have visual separation from the background",
        "The menu has some visual polish beyond basic rectangles",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        # Visual depth is a polish concern - be lenient in fallback
        if not result.passed:
            print(f"WARNING: Depth check: {assertion}")
            print(f"  Reasoning: {result.reasoning}")
            if result.confidence > 0.0:
                assert result.passed, (
                    f"Visual depth check failed: {assertion}\n  Reasoning: {result.reasoning}"
                )


# ---------------------------------------------------------------------------
# Test: Background Not Plain White
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_background_not_white() -> None:
    """Verify that the background is not plain white.

    Goal.md issue: "White background outside the panel — a real game would
    never have a plain white bg behind its menu."

    The scene background should be appropriate for a game menu.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_background.png")

    checks = [
        "The background behind the menu panel is not plain white",
        "The scene has an appropriate background color or pattern for a game menu",
        "The background provides good contrast with the menu panel",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Background check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Button Sizing
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_button_sizing() -> None:
    """Verify that buttons are not oversized relative to their text.

    Goal.md issue: "Buttons are oversized relative to their text — they
    stretch to fill the panel width with enormous padding."

    Buttons should be appropriately sized.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_button_sizing.png")

    checks = [
        "Buttons are appropriately sized relative to their text content",
        "Button padding is reasonable and not excessive",
        "Buttons do not appear stretched or oversized",
        "The button-to-text ratio looks balanced",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Button sizing check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Text Readability
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_text_readability() -> None:
    """Verify that all text is readable with good contrast.

    Basic requirement: text must be legible.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_text_readability.png")

    checks = [
        "All menu text is clearly readable",
        "Text has good contrast against its background",
        "Font size is appropriate for the menu elements",
        "No text is overlapping or obscured",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Text readability check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Overall Menu Polish
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_overall_polish() -> None:
    """High-level check: Does the menu look polished?

    Goal.md: User should think "this looks polished for a 2D framework"
    when they see the menu.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_overall_polish.png")

    checks = [
        "The menu has a cohesive, polished appearance",
        "UI elements are well-organized and properly spaced",
        "The menu looks like something from a finished game, not a prototype",
        "The color scheme is visually appealing",
        "The menu layout is clean and professional",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        # Polish is subjective - be lenient in fallback
        if not result.passed:
            print(f"WARNING: Polish check: {assertion}")
            print(f"  Reasoning: {result.reasoning}")
            if result.confidence > 0.0:
                assert result.passed, (
                    f"Menu polish check failed: {assertion}\n  Reasoning: {result.reasoning}"
                )


# ---------------------------------------------------------------------------
# Test: Comparison with Goal.md Issues
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_menu_addresses_goal_issues() -> None:
    """Comprehensive check that all goal.md issues are addressed.

    This test explicitly checks each issue mentioned in goal.md
    to ensure they have been fixed.
    """
    MenuScene = _load_menu_scene()

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(480, 360))
    image.save(_OUTPUT_DIR / "menu_goal_issues.png")

    # Each check directly maps to a goal.md issue
    critical_checks = {
        "Title NOT clipped": "The title text is fully visible and not cut off at the top",
        "Visual hierarchy EXISTS": "Different UI elements have distinct visual treatments",
        "NOT all gray": "The color palette uses more than just shades of gray",
        "Background NOT white": "The scene background is not plain white",
        "Buttons properly sized": "Buttons are appropriately sized, not stretched",
    }

    for issue_name, assertion in critical_checks.items():
        result = check_image(image, assertion)
        assert result.passed, (
            f"Goal.md issue '{issue_name}' not fixed: {assertion}\n  Reasoning: {result.reasoning}"
        )
