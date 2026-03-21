"""AI-powered visual verification for Battle Vignette example.

This test verifies the visual quality of the battle vignette demo using
AI-driven semantic checks. It ensures the game looks presentable and polished.

Run from project root::

    # Without AI (fallback mode, auto-pass)
    pytest tests/visual_verify/test_battle_vignette_ai.py -v

    # With AI verification (requires ANTHROPIC_API_KEY)
    export ANTHROPIC_API_KEY=your_key_here
    pytest tests/visual_verify/test_battle_vignette_ai.py -v

Key visual checks based on goal.md:
- Characters are readable
- Background isn't blank
- Selection ring is visible
- Attack animations feel impactful
- UI panels have visual depth
- Health bars are readable
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.screenshot.harness import render_scene
from tests.visual_verify import check_image

# Import BattleScene from the example
_DEMO_DIR = Path(__file__).resolve().parents[2] / "examples" / "battle_vignette"


def _load_battle_scene():
    """Import BattleScene from battle_demo.py."""
    if "battle_demo" in sys.modules:
        del sys.modules["battle_demo"]

    added = False
    if str(_DEMO_DIR) not in sys.path:
        sys.path.insert(0, str(_DEMO_DIR))
        added = True
    try:
        from battle_demo import BattleScene  # type: ignore[import-not-found]

        return BattleScene
    finally:
        if added and str(_DEMO_DIR) in sys.path:
            sys.path.remove(str(_DEMO_DIR))
        if "battle_demo" in sys.modules:
            del sys.modules["battle_demo"]


# Output directory for manual inspection
_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _setup_battle_assets(game):
    """Set up asset manager for battle vignette."""
    from saga2d import AssetManager

    asset_path = _DEMO_DIR / "assets"
    game.assets = AssetManager(game.backend, base_path=asset_path)


# ---------------------------------------------------------------------------
# Test: Battle Scene Initial Formation
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_battle_initial_formation_visual_quality() -> None:
    """Verify the battle scene's initial visual quality.

    This test checks the critical visual elements that make the battle
    vignette look like a presentable game demo:
    - Unit sprites are visible and distinct
    - Background has appropriate terrain (not blank)
    - Grid is clearly defined
    - UI panels are readable
    - Visual hierarchy is clear
    """
    BattleScene = _load_battle_scene()

    def setup(game):
        # Set up asset path for battle vignette
        from saga2d import AssetManager

        asset_path = _DEMO_DIR / "assets"
        game.assets = AssetManager(game.backend, base_path=asset_path)

        scene = BattleScene()
        game.push(scene)

    # Render at demo's native resolution
    image = render_scene(setup, tick_count=5, resolution=(1920, 1080))

    # Save for manual inspection
    image.save(_OUTPUT_DIR / "battle_initial_formation.png")

    # AI visual quality checks
    checks = [
        # Core requirement: sprites are visible
        "Unit sprites (warriors and skeletons) are clearly visible on the battlefield",
        # Background quality
        "The grid background has terrain tiles and is not blank white",
        # Grid visibility
        "A grid is visible with clearly defined cells",
        # UI readability
        "Side panels showing team information are visible on the left and right edges",
        # Text readability
        "The turn indicator text at the top is readable",
        # Visual polish
        "Unit sprites are visually distinct from the background",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Battle Scene with Selected Unit
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_battle_unit_selection_visual() -> None:
    """Verify that unit selection is visually clear and polished.

    Key checks:
    - Selection ring is visible
    - Selected unit info bar is readable
    - Visual feedback for selection is clear
    """
    BattleScene = _load_battle_scene()

    def setup(game):
        _setup_battle_assets(game)
        scene = BattleScene()
        game.push(scene)
        # Advance a few ticks to ensure scene is fully initialized
        game.tick(dt=1.0 / 60.0)

        # Select the first warrior unit
        if scene.warriors:
            warrior = scene.warriors[0]
            scene._select(warrior)

    image = render_scene(setup, tick_count=10, resolution=(1920, 1080))
    image.save(_OUTPUT_DIR / "battle_unit_selection.png")

    checks = [
        "A selection indicator (ring or highlight) is visible around one of the units",
        "The selected unit stands out visually from unselected units",
        "A unit information panel or bar is visible showing the selected unit's details",
        "The selected unit's stats or information is readable",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Battle Scene Health Bars
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_battle_health_bars_visual() -> None:
    """Verify that health bars are visible and readable.

    Health bars are critical UI feedback for tactical combat.
    They must be clearly visible and positioned correctly.
    """
    BattleScene = _load_battle_scene()

    def setup(game):
        _setup_battle_assets(game)
        scene = BattleScene()
        game.push(scene)

    image = render_scene(setup, tick_count=10, resolution=(1920, 1080))
    image.save(_OUTPUT_DIR / "battle_health_bars.png")

    checks = [
        "Health bars are visible above or near the unit sprites",
        "Health bar colors provide clear visual feedback (green for healthy, red for damaged)",
        "The health bars are appropriately sized and positioned",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Battle Scene UI Panels
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_battle_ui_panels_visual() -> None:
    """Verify that UI panels have visual depth and are readable.

    Goal.md requirement: "UI panels have visual depth"
    Checks for:
    - Panel backgrounds provide contrast
    - Text within panels is readable
    - Panels are visually distinct from game area
    """
    BattleScene = _load_battle_scene()

    def setup(game):
        _setup_battle_assets(game)
        scene = BattleScene()
        game.push(scene)

    image = render_scene(setup, tick_count=5, resolution=(1920, 1080))
    image.save(_OUTPUT_DIR / "battle_ui_panels.png")

    checks = [
        "Side panels on the left and right are visually distinct from the game grid",
        "Panel backgrounds provide contrast with the content they contain",
        "Text within the panels (team info, stats) is readable with good contrast",
        "The turn indicator panel at the top is clearly visible",
        "UI elements have visual hierarchy (important elements stand out)",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Battle Scene Overall Polish
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_battle_overall_visual_polish() -> None:
    """High-level check: Does the battle vignette look like a presentable demo?

    This is the ultimate test from goal.md: "battle vignette example looks
    like a real game". It checks subjective visual quality that would make
    a user think "this looks polished for a 2D framework."
    """
    BattleScene = _load_battle_scene()

    def setup(game):
        _setup_battle_assets(game)
        scene = BattleScene()
        game.push(scene)

    image = render_scene(setup, tick_count=10, resolution=(1920, 1080))
    image.save(_OUTPUT_DIR / "battle_overall_polish.png")

    checks = [
        "The game has a cohesive visual style and color palette",
        "UI elements are well-organized and not cluttered",
        "The grid and units have good visual separation from the UI",
        "Text throughout the scene is readable and properly sized",
        "The scene looks polished enough to showcase in a framework demo",
        "Visual elements have appropriate spacing and are not overlapping",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        # For polish checks, we're more lenient - just warn if confidence is low
        if not result.passed:
            print(f"WARNING: Polish check may need attention: {assertion}")
            print(f"  Reasoning: {result.reasoning}")
            # Don't fail the test for subjective polish checks in fallback mode
            if result.confidence > 0.0:
                assert result.passed, (
                    f"Visual polish check failed: {assertion}\n  Reasoning: {result.reasoning}"
                )
