"""Demo: Using AI-powered visual verification with screenshot tests.

This example demonstrates how to integrate the AI checker with the existing
render_scene() harness to verify visual quality of game scenes.

Run from project root::

    python tests/visual_verify/demo_usage.py

Set ANTHROPIC_API_KEY environment variable to enable actual AI verification.
Without it, the checker will gracefully skip with a warning.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from saga2d import Anchor, Button, Game, Label, Layout, Panel, Scene, Style
from tests.screenshot.harness import render_scene
from tests.visual_verify import check_image


# ---------------------------------------------------------------------------
# Example Scene: Simple Menu
# ---------------------------------------------------------------------------


class SimpleMenuScene(Scene):
    """A minimal menu scene for testing visual verification."""

    background_color = (25, 30, 40, 255)

    def on_enter(self) -> None:
        title = Label(
            "DEMO MENU",
            style=Style(
                font_size=48,
                text_color=(255, 220, 80, 255),
            ),
        )

        play_btn = Button("Play Game")
        settings_btn = Button("Settings")
        quit_btn = Button("Quit")

        panel = Panel(
            anchor=Anchor.CENTER,
            layout=Layout.VERTICAL,
            spacing=12,
            style=Style(
                background_color=(30, 35, 50, 220),
                padding=40,
            ),
            children=[title, play_btn, settings_btn, quit_btn],
        )

        self.ui.add(panel)


# ---------------------------------------------------------------------------
# Demo: Visual verification workflow
# ---------------------------------------------------------------------------


def demo_visual_verification() -> None:
    """Demonstrate the complete visual verification workflow."""

    print("=" * 70)
    print("AI-POWERED VISUAL VERIFICATION DEMO")
    print("=" * 70)
    print()

    # Step 1: Render the scene using the existing harness
    print("Step 1: Rendering scene with render_scene()...")

    def setup(game: Game) -> None:
        game.push(SimpleMenuScene())

    image = render_scene(setup, tick_count=2, resolution=(800, 600))
    print(f"  ✓ Rendered {image.size[0]}x{image.size[1]} image")
    print()

    # Step 2: Define visual assertions
    print("Step 2: Defining visual assertions...")
    assertions = [
        "A menu panel is centered on screen",
        "The title text 'DEMO MENU' is visible at the top of the panel",
        "Three buttons are vertically stacked below the title",
        "The background is dark colored",
    ]

    for i, assertion in enumerate(assertions, 1):
        print(f"  {i}. {assertion}")
    print()

    # Step 3: Verify each assertion
    print("Step 3: Running AI verification...")
    print()

    all_passed = True
    results = []

    for i, assertion in enumerate(assertions, 1):
        print(f"  Checking assertion {i}/{len(assertions)}...")
        print(f'    "{assertion}"')

        result = check_image(image, assertion)
        results.append((assertion, result))

        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"    {status} (confidence: {result.confidence:.2f})")
        print(f"    Reasoning: {result.reasoning}")
        print()

        if not result.passed:
            all_passed = False

    # Step 4: Summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total assertions: {len(assertions)}")
    print(f"Passed: {sum(1 for _, r in results if r.passed)}")
    print(f"Failed: {sum(1 for _, r in results if not r.passed)}")
    print()

    if all_passed:
        print("✓ All visual checks passed!")
    else:
        print("✗ Some visual checks failed")
        print()
        print("Failed assertions:")
        for assertion, result in results:
            if not result.passed:
                print(f"  - {assertion}")
                print(f"    Reason: {result.reasoning}")

    print()

    # Note about anthropic availability
    if any("anthropic" in r.reasoning.lower() for _, r in results):
        print("NOTE: anthropic library not installed or ANTHROPIC_API_KEY not set.")
        print("To enable actual AI verification:")
        print("  1. Install: pip install anthropic")
        print("  2. Set API key: export ANTHROPIC_API_KEY=your_key_here")
        print("  3. Re-run this demo")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_visual_verification()
