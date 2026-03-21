# AI Visual Verification - Quick Start

## 5-Minute Setup

### 1. Basic Usage (No Setup Required)

```python
from tests.screenshot.harness import render_scene
from tests.visual_verify import check_image

# Render a scene
def setup(game):
    game.push(MenuScene())

image = render_scene(setup, tick_count=2, resolution=(800, 600))

# Verify visual properties
result = check_image(image, "The menu title is centered and readable")
assert result.passed, result.reasoning
```

**No installation needed!** Works immediately with graceful fallback.

### 2. Enable AI (Optional)

```bash
# Install anthropic
pip install anthropic

# Set API key
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Run your tests - AI is now active!
pytest tests/visual_verify/test_ui_with_ai.py -v
```

## Common Patterns

### Pattern: Supplement Golden Images

```python
def test_menu():
    image = render_scene(setup, resolution=(800, 600))

    # Pixel-perfect regression test
    assert_screenshot(image, "menu_golden")

    # AI quality checks
    result = check_image(image, "Text has good contrast")
    assert result.passed
```

### Pattern: AI-Only (Dynamic Content)

```python
def test_particles():
    # Particles appear at different positions each run
    image = render_scene(setup_with_particles, tick_count=30)

    result = check_image(image, "Particle effects are visible")
    assert result.passed
```

### Pattern: Multiple Checks

```python
checks = [
    "Title is visible and centered",
    "Buttons are vertically aligned",
    "Text is readable with good contrast"
]

for check in checks:
    result = check_image(image, check)
    assert result.passed, f"{check}: {result.reasoning}"
```

## Quick Reference

### API

```python
result = check_image(
    image,                            # PIL Image
    assertion,                        # str: what to verify
    model="claude-3-5-sonnet-...",   # optional
    max_tokens=300,                   # optional
)

# result.passed: bool
# result.reasoning: str
# result.confidence: float (0.0-1.0)
```

### Good Assertions

✅ "The text 'Game Over' is displayed in large red font"
✅ "Three blue buttons are horizontally aligned"
✅ "Health bars are visible above each unit"
✅ "The background is dark with good contrast"

❌ "The UI looks good" (too vague)
❌ "Colors are beautiful" (subjective)

### Running Tests

```bash
# All tests (fallback mode, no API)
pytest tests/visual_verify/ -v

# With AI enabled
export ANTHROPIC_API_KEY=your_key
pytest tests/visual_verify/ -v

# Run the demo
python tests/visual_verify/demo_usage.py
```

## Files

```
tests/visual_verify/
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── IMPLEMENTATION.md      # Technical details
├── demo_usage.py          # Interactive demo
├── ai_checker.py          # Core implementation
├── test_ai_checker.py     # Unit tests
└── test_ui_with_ai.py     # Integration examples
```

## Troubleshooting

**Q: Tests pass but always show "confidence: 0.00"**
A: anthropic library not installed or ANTHROPIC_API_KEY not set. This is expected fallback behavior.

**Q: Want to disable fallback auto-pass?**
A: Check `result.confidence > 0.0` to detect fallback mode and skip the test.

**Q: How much does it cost?**
A: ~$0.003-0.005 per image verification. Skip in CI to minimize costs.

**Q: Tests are slow with API enabled**
A: Each API call takes 1-3 seconds. Use sparingly or disable in CI.

## Next Steps

1. Read `README.md` for comprehensive documentation
2. Run `python tests/visual_verify/demo_usage.py` to see it in action
3. Study `test_ui_with_ai.py` for integration patterns
4. Add AI checks to your own screenshot tests!

## Support

- **Full docs**: `tests/visual_verify/README.md`
- **Implementation details**: `tests/visual_verify/IMPLEMENTATION.md`
- **Claude docs**: https://docs.anthropic.com/claude/docs/vision
