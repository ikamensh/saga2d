# AI-Powered Visual Verification

This directory contains tools for AI-driven visual quality assurance of screenshot tests using Claude's vision API.

## Overview

The visual verification system integrates with the existing `render_scene()` harness to provide human-like verification of rendered game scenes. Instead of pixel-perfect golden image comparisons, it uses Claude to verify natural-language assertions about visual appearance.

## Architecture

```
tests/visual_verify/
├── __init__.py           # Public API (check_image, VerificationResult)
├── ai_checker.py         # Core implementation with graceful anthropic fallback
├── test_ai_checker.py    # Unit tests for the verification system
├── demo_usage.py         # Interactive demo showing complete workflow
└── README.md            # This file
```

## Core API

### `check_image(image, assertion, *, model, max_tokens) -> VerificationResult`

Verifies that a PIL Image satisfies a natural-language visual assertion.

**Parameters:**
- `image`: PIL Image object (from `render_scene()` or any source)
- `assertion`: Natural-language statement about what should be visible
- `model`: Claude model to use (default: `claude-3-5-sonnet-20241022`)
- `max_tokens`: Max response tokens (default: 300)

**Returns:**
`VerificationResult` dataclass with:
- `passed: bool` - Whether the assertion was satisfied
- `reasoning: str` - Human-readable explanation
- `confidence: float` - AI confidence score (0.0-1.0)

**Example:**

```python
from tests.screenshot.harness import render_scene
from tests.visual_verify import check_image

def setup(game):
    game.push(MenuScene())

image = render_scene(setup, tick_count=2, resolution=(800, 600))

result = check_image(
    image,
    "A menu panel is centered with three vertically stacked buttons"
)

assert result.passed, f"Visual check failed: {result.reasoning}"
```

## Integration with Existing Tests

### Pattern 1: Supplement Golden Images

Use AI verification **alongside** pixel-perfect tests:

```python
def test_menu_scene():
    # Traditional pixel-perfect check
    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(800, 600))
    assert_screenshot(image, "menu_golden")

    # AI verification for higher-level properties
    result = check_image(image, "Text is readable with good contrast")
    assert result.passed, result.reasoning

    result = check_image(image, "UI elements are properly aligned")
    assert result.passed, result.reasoning
```

### Pattern 2: AI-Only Verification

For tests where pixel-perfect comparison is too brittle:

```python
def test_animated_particle_effect():
    def setup(game):
        scene = BattleScene()
        game.push(scene)
        # Trigger particle effect (non-deterministic timing)
        scene.spawn_hit_particles(400, 300)

    image = render_scene(setup, tick_count=30, resolution=(800, 600))

    # Particles may be at different positions each run
    result = check_image(
        image,
        "Particle effects are visible near the center of the screen"
    )
    assert result.passed, result.reasoning
```

### Pattern 3: Parameterized Multi-Assertion Tests

```python
@pytest.mark.parametrize("assertion", [
    "The title 'DEMO MENU' is clearly visible",
    "Three buttons are vertically aligned",
    "Button text is readable",
    "Panel has rounded corners and a dark background",
])
def test_menu_visual_properties(assertion):
    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=2, resolution=(800, 600))
    result = check_image(image, assertion)

    assert result.passed, f"{assertion}: {result.reasoning}"
    assert result.confidence > 0.7, "AI not confident in result"
```

## Setup

### Without API (Development/CI)

The system works **without** the anthropic library or API key:

```bash
# Tests will auto-pass with warnings
pytest tests/visual_verify/test_ai_checker.py -v
```

This is useful for:
- Development when you don't need AI verification
- CI pipelines where you want to skip optional checks
- Quick iteration on test structure

### With AI Verification (Full QA)

1. **Install anthropic:**
   ```bash
   pip install anthropic
   ```

2. **Set API key:**
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

3. **Run tests:**
   ```bash
   pytest tests/visual_verify/test_ai_checker.py -v
   # Or run the interactive demo:
   python tests/visual_verify/demo_usage.py
   ```

## Graceful Fallback Behavior

When anthropic is not available or API key is missing:

```python
result = check_image(image, "Menu is centered")
# Returns:
VerificationResult(
    passed=True,  # Auto-pass
    reasoning="anthropic library not installed or ANTHROPIC_API_KEY not set. "
              "Skipping AI verification (auto-pass). Install with: pip install anthropic",
    confidence=0.0,
)
```

This allows tests to:
- ✅ Run successfully in any environment
- ✅ Pass CI without API keys
- ✅ Provide clear guidance when AI verification is skipped
- ✅ Be gradually adopted without breaking existing workflows

## Writing Effective Assertions

### ✅ Good Assertions

Clear, specific, verifiable:

```python
"The text 'Game Over' is displayed in large red font"
"Three blue buttons are horizontally aligned at the bottom"
"A health bar is visible above each unit sprite"
"The background is dark with a green tint"
"Text is readable with good contrast against the background"
```

### ❌ Poor Assertions

Vague, subjective, or unverifiable:

```python
"The UI looks good"  # Too vague
"Colors are beautiful"  # Subjective
"Performance is smooth"  # Not visual
"The code is well-structured"  # Not about the image
```

### Tips

1. **Be specific**: "Three buttons" not "several buttons"
2. **Describe position**: "centered", "top-left", "below the title"
3. **Mention colors**: "red text", "dark blue background"
4. **State expectations**: "visible", "readable", "aligned"
5. **Focus on visuals**: What a human QA tester would check

## Use Cases

### When to Use AI Verification

1. **Layout and alignment** - "Elements are properly centered"
2. **Readability** - "Text is large enough and has good contrast"
3. **Color and styling** - "The health bar is green when full"
4. **Presence checks** - "A particle effect is visible at impact point"
5. **Non-deterministic content** - Animations, particles, random layouts

### When to Use Golden Images

1. **Pixel-perfect rendering** - Exact sprite positioning
2. **Regression detection** - Catch unintended visual changes
3. **Deterministic scenes** - Static UI, fixed layouts
4. **Performance** - No API calls, instant comparison

### Best Practice: Use Both

```python
def test_battle_scene_comprehensive():
    # Setup
    image = render_scene(...)

    # Pixel-perfect regression test
    assert_screenshot(image, "battle_golden")

    # High-level quality checks
    ai_checks = [
        "All unit sprites are visible on the grid",
        "Health bars are positioned above each unit",
        "The UI text is readable",
        "Grid cells are clearly defined",
    ]

    for check in ai_checks:
        result = check_image(image, check)
        assert result.passed, f"{check}: {result.reasoning}"
```

## Cost and Performance

### API Usage

- **Model**: Claude 3.5 Sonnet (vision-capable)
- **Cost per image**: ~$0.003-0.005 (varies by image size)
- **Latency**: 1-3 seconds per verification

### Optimization Tips

1. **Batch assertions**: Test multiple properties in one call when possible
2. **Skip in CI**: Set `ANTHROPIC_API_KEY` only for full QA runs
3. **Use golden images for regression**: Reserve AI for quality checks
4. **Adjust max_tokens**: Lower to 100-150 for simple yes/no checks

## Running the Demo

```bash
# Without API key (shows fallback behavior)
python tests/visual_verify/demo_usage.py

# With API key (actual AI verification)
export ANTHROPIC_API_KEY=your_key_here
python tests/visual_verify/demo_usage.py
```

The demo:
1. Renders a simple menu scene
2. Defines 4 visual assertions
3. Verifies each with Claude's vision API
4. Shows detailed results and summary

## Testing the Implementation

```bash
# Run unit tests
pytest tests/visual_verify/test_ai_checker.py -v

# Run with API tests (requires key)
pytest tests/visual_verify/test_ai_checker.py -v --no-skip

# Run all visual_verify tests
pytest tests/visual_verify/ -v
```

## Future Enhancements

Potential improvements:

1. **Batch verification** - Multiple assertions in one API call
2. **Caching** - Cache results for identical image+assertion pairs
3. **Confidence thresholds** - Configurable minimum confidence scores
4. **Multiple models** - Support other vision models (GPT-4V, Gemini)
5. **Visual diff highlighting** - Generate annotated failure images
6. **Assertion templates** - Pre-built assertions for common checks

## See Also

- `tests/screenshot/harness.py` - Screenshot capture infrastructure
- `CLAUDE.md` - Project-wide visual verification guidelines
- `tests/screenshot/` - Existing golden image tests
