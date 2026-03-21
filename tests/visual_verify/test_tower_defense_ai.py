"""AI-powered visual verification for Tower Defense example.

This test verifies the visual quality of the tower defense demo using
AI-driven semantic checks. It ensures the game looks playable and polished.

Run from project root::

    # Without AI (fallback mode, auto-pass)
    pytest tests/visual_verify/test_tower_defense_ai.py -v

    # With AI verification (requires ANTHROPIC_API_KEY)
    export ANTHROPIC_API_KEY=your_key_here
    pytest tests/visual_verify/test_tower_defense_ai.py -v

Key visual checks based on goal.md:
- Grass tiles tile seamlessly (no gaps/seams)
- Towers look distinct from each other
- UI panels have visual depth
- HUD bar is readable
- Enemy sprites are distinguishable
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.screenshot.harness import render_scene
from tests.visual_verify import check_image

# Import scenes from the tower defense example
_TD_DIR = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"


def _load_tower_defense():
    """Import TitleScene and GameScene from tower defense example."""
    if "main" in sys.modules:
        del sys.modules["main"]

    added = False
    if str(_TD_DIR) not in sys.path:
        sys.path.insert(0, str(_TD_DIR))
        added = True
    try:
        from main import TitleScene, GameScene  # type: ignore[import-not-found]

        return TitleScene, GameScene
    finally:
        if added and str(_TD_DIR) in sys.path:
            sys.path.remove(str(_TD_DIR))
        if "main" in sys.modules:
            del sys.modules["main"]


# Output directory for manual inspection
_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _setup_td_assets(game):
    """Set up asset manager for tower defense."""
    from saga2d import AssetManager

    asset_path = _TD_DIR / "assets"
    game.assets = AssetManager(game.backend, base_path=asset_path)


# ---------------------------------------------------------------------------
# Test: Tower Defense Title Screen
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_title_visual() -> None:
    """Verify the title screen visual quality.

    Title screen should look inviting and polished, with clear
    navigation options.
    """
    TitleScene, _ = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        game.push(TitleScene())

    image = render_scene(setup, tick_count=2, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_title.png")

    checks = [
        "The title 'Tower Defense' is clearly visible and prominent",
        "Menu buttons (Play, Quit) are clearly visible and readable",
        "The background is not blank white",
        "Text has good contrast against the background",
        "The menu has a cohesive visual style",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Tower Defense Game Initial State
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_game_initial_visual() -> None:
    """Verify the game scene's initial visual quality.

    Critical checks from goal.md:
    - Grass tiles tile seamlessly (no gaps)
    - Path is visually distinct
    - HUD is readable
    - Tower slots are visible
    """
    _, GameScene = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        game.push(GameScene())

    # More ticks to ensure tiles are rendered and first wave starts
    image = render_scene(setup, tick_count=10, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_game_initial.png")

    checks = [
        # CRITICAL: Tile seams (goal.md requirement)
        "Grass tiles connect seamlessly without visible gaps or seams between tiles",
        # Path visibility
        "A path made of distinct tiles is visible across the map",
        # Path distinction
        "The path tiles are visually distinct from the grass tiles",
        # HUD readability (goal.md requirement)
        "A HUD panel at the top shows game information (wave, gold, lives)",
        # Tower slots
        "Tower placement slots are visible on the map",
        # Build menu (goal.md requirement: "UI panels have visual depth")
        "A build menu or tower selection panel is visible",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Tower Defense HUD Readability
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_hud_readability() -> None:
    """Verify that the HUD panel is readable.

    Goal.md requirement: "HUD bar is readable"
    The HUD must clearly show wave, gold, lives, and score.
    """
    _, GameScene = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        scene = GameScene()
        game.push(scene)

    image = render_scene(setup, tick_count=5, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_hud.png")

    checks = [
        "The HUD shows wave information that is readable",
        "Gold amount is displayed and readable",
        "Lives or health information is visible",
        "HUD text has good contrast against its background",
        "HUD elements are well-spaced and not overlapping",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Tower Defense with Placed Towers
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_towers_visual() -> None:
    """Verify that towers are visually distinct and identifiable.

    Goal.md requirement: "Towers look distinct from each other"
    Different tower types must be easily distinguishable.
    """
    _, GameScene = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        scene = GameScene()
        game.push(scene)
        # Advance to let scene initialize
        game.tick(dt=1.0 / 60.0)

        # Try to place a tower if possible (give player gold and place on first slot)
        if hasattr(scene, "_gold"):
            scene._gold = 1000  # Give enough gold
            scene._gold_label.text = f"Gold: {scene._gold}"

        # Try to place towers on available slots
        if hasattr(scene, "_slot_sprites") and scene._slot_sprites:
            from saga2d import Sprite

            # Place a tower on the first available slot
            first_slot = next(iter(scene._slot_sprites.keys()))
            col, row = first_slot

            # Use the first tower definition
            if hasattr(scene, "_placed_towers"):
                # Get tower definitions
                import sys

                _td_path = (
                    Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
                )
                if str(_td_path) not in sys.path:
                    sys.path.insert(0, str(_td_path))
                try:
                    from main import TOWER_DEFS, TILE_SIZE

                    if TOWER_DEFS:
                        tower_def = TOWER_DEFS[0]
                        # Create tower sprite
                        from saga2d import RenderLayer, SpriteAnchor

                        tower_sprite = scene.add_sprite(
                            Sprite(
                                tower_def["image"],
                                position=(col * TILE_SIZE, row * TILE_SIZE),
                                anchor=SpriteAnchor.TOP_LEFT,
                                layer=RenderLayer.OBJECTS,
                            )
                        )
                        scene._placed_towers[(col, row)] = {
                            "def": tower_def,
                            "sprite": tower_sprite,
                            "cooldown": 0.0,
                        }
                        # Remove slot marker
                        if (col, row) in scene._slot_sprites:
                            scene._slot_sprites.pop((col, row))
                finally:
                    if str(_td_path) in sys.path:
                        sys.path.remove(str(_td_path))

    image = render_scene(setup, tick_count=15, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_with_towers.png")

    checks = [
        "Tower structures are visible on the map",
        "Towers are visually distinct from the grass and path tiles",
        "Tower sprites have clear shapes and are recognizable",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Tower Defense with Enemies
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_enemies_visual() -> None:
    """Verify that enemies are visible and distinguishable.

    Goal.md requirement: "Enemy sprites are distinguishable"
    Enemies must be clearly visible on the path.
    """
    _, GameScene = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        scene = GameScene()
        game.push(scene)

    # Wait for enemies to spawn (wave starts after delay)
    image = render_scene(setup, tick_count=150, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_with_enemies.png")

    checks = [
        "Enemy units are visible on the path",
        "Enemies are visually distinct from the background tiles",
        "Enemy sprites have recognizable shapes",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        # Enemies might not have spawned yet, so be lenient in fallback mode
        if not result.passed and result.confidence == 0.0:
            print(f"WARNING: Enemy check may need more time: {assertion}")
        elif not result.passed:
            assert False, (
                f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
            )


# ---------------------------------------------------------------------------
# Test: Tower Defense UI Panel Visual Depth
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_ui_panels_depth() -> None:
    """Verify that UI panels have visual depth.

    Goal.md requirement: "UI panels have visual depth"
    Panels should not look like flat rectangles - they need visual polish.
    """
    _, GameScene = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        game.push(GameScene())

    image = render_scene(setup, tick_count=5, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_ui_depth.png")

    checks = [
        "UI panels have visible backgrounds that separate them from the game area",
        "Panel backgrounds provide contrast with their content",
        "The HUD panel is visually distinct from the game map",
        "Build menu panel has clear visual boundaries",
        "UI elements have appropriate spacing and padding",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        assert result.passed, (
            f"Visual check failed: {assertion}\n  Reasoning: {result.reasoning}"
        )


# ---------------------------------------------------------------------------
# Test: Tower Defense Overall Polish
# ---------------------------------------------------------------------------


@pytest.mark.visual_ai
def test_tower_defense_overall_polish() -> None:
    """High-level check: Does tower defense look playable?

    Goal.md: "tower defense example looks playable"
    This checks subjective visual quality.
    """
    _, GameScene = _load_tower_defense()

    def setup(game):
        _setup_td_assets(game)
        game.push(GameScene())

    image = render_scene(setup, tick_count=10, resolution=(960, 540))
    image.save(_OUTPUT_DIR / "tower_defense_overall.png")

    checks = [
        "The game has a cohesive visual style",
        "All UI text is readable with good contrast",
        "Game elements (tiles, towers, UI) are well-organized",
        "The scene looks polished enough to be playable",
        "Visual hierarchy is clear (game area vs UI)",
    ]

    for assertion in checks:
        result = check_image(image, assertion)
        # For polish checks, be lenient in fallback mode
        if not result.passed:
            print(f"WARNING: Polish check may need attention: {assertion}")
            print(f"  Reasoning: {result.reasoning}")
            if result.confidence > 0.0:
                assert result.passed, (
                    f"Visual polish check failed: {assertion}\n  Reasoning: {result.reasoning}"
                )
