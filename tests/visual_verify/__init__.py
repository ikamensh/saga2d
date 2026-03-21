"""Visual verification tools for screenshot tests.

This package provides AI-powered visual quality assurance for game framework
screenshot tests. It integrates Claude's vision API to verify that rendered
scenes meet human-readable assertions about their visual appearance.

Public API:

    check_image(image, assertion) -> VerificationResult

Example usage::

    from tests.visual_verify import check_image

    image = render_scene(setup, tick_count=5, resolution=(800, 600))

    result = check_image(
        image,
        "The main menu panel is centered with three vertically stacked buttons"
    )

    assert result.passed, f"Visual check failed: {result.reasoning}"
"""

from tests.visual_verify.ai_checker import (
    VerificationResult,
    check_image,
)

__all__ = [
    "check_image",
    "VerificationResult",
]
