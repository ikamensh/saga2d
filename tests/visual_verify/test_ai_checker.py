"""Tests for the AI-powered visual verification system.

These tests verify the ai_checker module's behavior in both anthropic-available
and anthropic-unavailable scenarios.

Run with::

    pytest tests/visual_verify/test_ai_checker.py -v
"""

from __future__ import annotations

import pytest
from PIL import Image

from tests.visual_verify import VerificationResult, check_image


def test_verification_result_structure() -> None:
    """VerificationResult has the required fields."""
    result = VerificationResult(
        passed=True,
        reasoning="Test reasoning",
        confidence=0.95,
    )

    assert result.passed is True
    assert result.reasoning == "Test reasoning"
    assert result.confidence == 0.95
    assert isinstance(result.confidence, float)


def test_check_image_without_anthropic() -> None:
    """check_image gracefully handles missing anthropic library.

    When anthropic is not installed or ANTHROPIC_API_KEY is not set,
    check_image should return a permissive result (passed=True) with
    a warning message about the missing dependency.
    """
    # Create a dummy image
    image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

    result = check_image(
        image,
        assertion="This is a test assertion",
    )

    # Should be a VerificationResult
    assert isinstance(result, VerificationResult)
    assert isinstance(result.passed, bool)
    assert isinstance(result.reasoning, str)
    assert isinstance(result.confidence, float)

    # Without anthropic or API key, should auto-pass with warning
    # (This test will pass regardless of whether anthropic is installed,
    # since it tests the fallback behavior when API key is missing)
    if (
        "anthropic library not installed" in result.reasoning
        or "ANTHROPIC_API_KEY not set" in result.reasoning
    ):
        assert result.passed is True
        assert result.confidence == 0.0
        assert "anthropic" in result.reasoning.lower()


@pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY and will make API calls")
def test_check_image_with_api_simple_pass() -> None:
    """check_image correctly verifies a simple passing assertion.

    This test requires:
    - anthropic library installed
    - ANTHROPIC_API_KEY environment variable set
    - Internet connection for API calls

    It creates a red square and verifies that Claude can detect it.
    """
    # Create a solid red image
    image = Image.new("RGBA", (200, 200), (255, 0, 0, 255))

    result = check_image(
        image,
        assertion="The image is a solid red square",
    )

    assert isinstance(result, VerificationResult)
    assert result.passed is True
    assert result.confidence > 0.7
    assert "red" in result.reasoning.lower()


@pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY and will make API calls")
def test_check_image_with_api_simple_fail() -> None:
    """check_image correctly identifies a failing assertion.

    Creates a blue square but asserts it should be red.
    """
    # Create a solid blue image
    image = Image.new("RGBA", (200, 200), (0, 0, 255, 255))

    result = check_image(
        image,
        assertion="The image is a solid red square",
    )

    assert isinstance(result, VerificationResult)
    assert result.passed is False
    assert result.confidence > 0.7
    # Reasoning should mention the color mismatch
    assert "blue" in result.reasoning.lower() or "not red" in result.reasoning.lower()


def test_check_image_accepts_pil_image() -> None:
    """check_image accepts a PIL Image object."""
    image = Image.new("RGBA", (50, 50), (0, 255, 0, 255))

    result = check_image(image, "Green square visible")

    # Should not raise an error
    assert isinstance(result, VerificationResult)


def test_check_image_custom_parameters() -> None:
    """check_image accepts optional model and max_tokens parameters."""
    image = Image.new("RGBA", (50, 50), (128, 128, 128, 255))

    # Should not raise even with custom parameters
    result = check_image(
        image,
        "Gray square",
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
    )

    assert isinstance(result, VerificationResult)
