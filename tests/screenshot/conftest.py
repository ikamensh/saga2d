"""Screenshot test configuration — skip if pyglet unavailable, register marker."""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Skip the entire directory when pyglet is not importable (headless CI, etc.)
# ---------------------------------------------------------------------------
try:
    import pyglet  # noqa: F401
except ImportError:
    pytest.skip(
        "pyglet not available — skipping screenshot tests",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# Skip when no display is available (e.g. IndexError from
# CocoaDisplay.get_default_screen() in headless environments)
# ---------------------------------------------------------------------------
def _display_available() -> bool:
    """Return True if pyglet can get a display/screen."""
    try:
        display = pyglet.display.get_display()
        display.get_default_screen()
        return True
    except IndexError:
        return False


# ---------------------------------------------------------------------------
# Register the "screenshot" marker so users can do: pytest -m screenshot
# ---------------------------------------------------------------------------
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "screenshot: visual regression test (requires pyglet + GPU context)",
    )


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list) -> None:
    """Skip all screenshot tests when no display is available."""
    if not _display_available():
        skip = pytest.mark.skip(reason="No display available for screenshot tests")
        for item in items:
            item.add_marker(skip)


# ---------------------------------------------------------------------------
# Ensure the output directory exists (for diff / failure images)
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


@pytest.fixture(autouse=True, scope="session")
def _ensure_output_dir() -> None:
    """Create tests/screenshot/output/ if it doesn't already exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
