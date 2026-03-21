#!/bin/bash
# Update screenshot golden images after UI improvements
#
# This script deletes the golden images that are affected by the UI improvements
# and then runs the tests to regenerate them.
#
# Requirements:
# - Must be run on a machine with a display (not headless/SSH)
# - Pyglet must be working with OpenGL support
#
# Usage:
#   ./scripts/update_screenshot_goldens.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GOLDEN_DIR="$PROJECT_ROOT/tests/screenshot/golden"

echo "=========================================="
echo "Screenshot Golden Image Update"
echo "=========================================="
echo ""

# Check if we have a display
if ! python3 -c "import pyglet; d = pyglet.display.get_display(); d.get_default_screen()" 2>/dev/null; then
    echo "ERROR: No display available!"
    echo ""
    echo "This script requires a display to run pyglet screenshot tests."
    echo "Please run this on a local machine with a display, not via SSH."
    echo ""
    exit 1
fi

echo "✓ Display detected"
echo ""

# List of golden images to update
GOLDEN_IMAGES=(
    "widget_progress_bar.png"
    "widget_tabgroup.png"
    "widget_datatable.png"
    "widget_tooltip_visible.png"
)

echo "The following golden images will be updated:"
for img in "${GOLDEN_IMAGES[@]}"; do
    echo "  - $img"
done
echo ""

# Ask for confirmation
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Deleting old golden images..."
for img in "${GOLDEN_IMAGES[@]}"; do
    if [ -f "$GOLDEN_DIR/$img" ]; then
        echo "  Deleting $img"
        rm "$GOLDEN_DIR/$img"
    else
        echo "  Skipping $img (not found)"
    fi
done

echo ""
echo "Step 2: Running tests to regenerate goldens..."
echo ""

cd "$PROJECT_ROOT"

# Run tests for each affected widget
pytest tests/screenshot/test_widget_screenshots.py::test_progress_bar -v
pytest tests/screenshot/test_widget_screenshots.py::test_tabgroup -v
pytest tests/screenshot/test_widget_screenshots.py::test_datatable -v
pytest tests/screenshot/test_widget_screenshots.py::test_tooltip_visible -v

echo ""
echo "Step 3: Verifying new golden images..."
MISSING=0
for img in "${GOLDEN_IMAGES[@]}"; do
    if [ -f "$GOLDEN_DIR/$img" ]; then
        echo "  ✓ $img created"
    else
        echo "  ✗ $img MISSING!"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "ERROR: Some golden images were not created!"
    echo "Check the test output above for errors."
    exit 1
fi

echo ""
echo "Step 4: Running all widget screenshot tests..."
pytest tests/screenshot/test_widget_screenshots.py -v

echo ""
echo "=========================================="
echo "✓ Golden images updated successfully!"
echo "=========================================="
echo ""
echo "The following images were updated:"
for img in "${GOLDEN_IMAGES[@]}"; do
    echo "  - tests/screenshot/golden/$img"
done
echo ""
echo "Review the new golden images to ensure they look correct:"
for img in "${GOLDEN_IMAGES[@]}"; do
    echo "  open tests/screenshot/golden/$img"
done
echo ""
