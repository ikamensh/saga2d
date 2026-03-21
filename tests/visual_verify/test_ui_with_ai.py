"""Example: Integrating AI verification with existing UI screenshot tests.

This test demonstrates how to combine traditional golden-image screenshot tests
with AI-powered visual verification for comprehensive quality assurance.

Run from project root::

    # Without AI (fallback mode, auto-pass)
    pytest tests/visual_verify/test_ui_with_ai.py -v

    # With AI verification (requires ANTHROPIC_API_KEY)
    export ANTHROPIC_API_KEY=your_key_here
    pytest tests/visual_verify/test_ui_with_ai.py -v

Based on tests/screenshot/test_ui_screenshots.py but enhanced with AI checks.
"""

from __future__ import annotations

import pytest

from saga2d import Anchor, Button, Label, Layout, Panel, Scene, Style
from tests.screenshot.harness import assert_screenshot, render_scene
from tests.visual_verify import check_image

_RESOLUTION = (480, 360)


# ---------------------------------------------------------------------------
# Test: Main Menu with AI verification
# ---------------------------------------------------------------------------


@pytest.mark.screenshot
def test_ui_main_menu_with_ai() -> None:
    """Main menu with both golden-image and AI verification.

    This test demonstrates the recommended pattern:
    1. Traditional pixel-perfect golden image check (regression detection)
    2. AI-powered quality checks (layout, readability, styling)

    The AI checks verify properties that golden images can't validate:
    - Are elements properly centered?
    - Is text readable with good contrast?
    - Are buttons appropriately sized and spaced?
    """

    class MenuScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Main Menu", style=Style(font_size=28)))
            panel.add(Button("New Game"))
            panel.add(Button("Load Game"))
            panel.add(Button("Quit"))
            self.ui.add(panel)

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # Step 1: Pixel-perfect regression test (use unique name to avoid conflicts)
    assert_screenshot(image, "ai_ui_main_menu")

    # Step 2: AI-powered quality checks
    ai_checks = [
        "A panel is centered on the screen",
        "The text 'Main Menu' is visible at the top",
        "Three buttons are vertically stacked below the title",
        "The button text is clearly readable",
        "UI elements have consistent spacing",
    ]

    for assertion in ai_checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"AI check failed: {assertion}\n  Reason: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Button Layout with AI verification
# ---------------------------------------------------------------------------


@pytest.mark.screenshot
def test_ui_horizontal_buttons_with_ai() -> None:
    """Horizontal button bar with AI verification of alignment and spacing."""

    class HBarScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.BOTTOM,
                layout=Layout.HORIZONTAL,
                spacing=12,
                margin=10,
            )
            panel.add(Button("Attack"))
            panel.add(Button("Defend"))
            panel.add(Button("Magic"))
            self.ui.add(panel)

    def setup(game):
        game.push(HBarScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # Golden image check (use unique name to avoid conflicts)
    assert_screenshot(image, "ai_ui_horizontal_buttons")

    # AI quality checks
    result = check_image(
        image, "Three buttons are horizontally aligned at the bottom of the screen"
    )
    assert result.passed, result.reasoning

    result = check_image(image, "Buttons have equal spacing between them")
    assert result.passed, result.reasoning

    result = check_image(
        image, "Button text ('Attack', 'Defend', 'Magic') is clearly visible"
    )
    assert result.passed, result.reasoning


# ---------------------------------------------------------------------------
# Test: Color and Styling with AI verification
# ---------------------------------------------------------------------------


@pytest.mark.screenshot
def test_ui_styled_label_with_ai() -> None:
    """Verify that custom styling is correctly applied and visually effective."""

    class LabelScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(
                Label(
                    "GAME OVER",
                    anchor=Anchor.CENTER,
                    style=Style(
                        font_size=40,
                        text_color=(255, 60, 60, 255),
                    ),
                )
            )

    def setup(game):
        game.push(LabelScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # Golden image check (use unique name to avoid conflicts)
    assert_screenshot(image, "ai_ui_styled_label")

    # AI quality checks focus on visual effectiveness
    result = check_image(image, "The text 'GAME OVER' is displayed in large, red font")
    assert result.passed, result.reasoning

    result = check_image(image, "The text is centered on the screen")
    assert result.passed, result.reasoning

    result = check_image(image, "The text is clearly readable with good contrast")
    assert result.passed, result.reasoning


# ---------------------------------------------------------------------------
# Test: AI-only verification for non-deterministic content
# ---------------------------------------------------------------------------


@pytest.mark.screenshot
def test_dynamic_content_ai_only() -> None:
    """Example where AI verification is used WITHOUT golden images.

    This pattern is useful for:
    - Randomly generated content
    - Animated elements (particles, effects)
    - Time-dependent visuals
    - Content that varies by run but should meet quality standards
    """

    class DynamicScene(Scene):
        background_color = (20, 25, 30, 255)

        def on_enter(self) -> None:
            # Simulate dynamic content that varies each run
            import random

            colors = [
                (255, 100, 100, 255),  # Red
                (100, 255, 100, 255),  # Green
                (100, 100, 255, 255),  # Blue
            ]
            color = random.choice(colors)

            self.ui.add(
                Label(
                    "DYNAMIC CONTENT",
                    anchor=Anchor.CENTER,
                    style=Style(
                        font_size=32,
                        text_color=color,
                    ),
                )
            )

    def setup(game):
        game.push(DynamicScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # NO golden image check — content varies each run

    # AI checks verify quality regardless of which color was chosen
    result = check_image(
        image, "Text reading 'DYNAMIC CONTENT' is visible and centered"
    )
    assert result.passed, result.reasoning

    result = check_image(
        image, "The text is displayed in a bright color with good visibility"
    )
    assert result.passed, result.reasoning

    result = check_image(
        image, "The background is dark, providing good contrast with the text"
    )
    assert result.passed, result.reasoning


# ---------------------------------------------------------------------------
# Test: Confidence threshold
# ---------------------------------------------------------------------------


@pytest.mark.screenshot
def test_ui_with_confidence_threshold() -> None:
    """Verify that AI is confident in its assessments.

    This pattern ensures the AI isn't just guessing — useful for
    critical visual checks where false positives would be problematic.
    """

    class MenuScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Settings", style=Style(font_size=28)))
            panel.add(Button("Volume"))
            panel.add(Button("Graphics"))
            self.ui.add(panel)

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # AI check with confidence requirement
    result = check_image(image, "The title 'Settings' is clearly visible")

    assert result.passed, f"Check failed: {result.reasoning}"

    # Require high confidence (skip if anthropic not available)
    if result.confidence > 0.0:  # 0.0 indicates fallback mode
        assert result.confidence >= 0.7, (
            f"AI confidence too low: {result.confidence:.2f} < 0.70"
        )
