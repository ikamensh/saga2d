"""AI-powered visual verification for screenshot tests.

This module provides AI-driven image verification using Claude's vision API.
When the anthropic library is not available, it gracefully falls back to a
permissive checker that always passes with a warning.

Usage::

    from tests.visual_verify.ai_checker import check_image

    result = check_image(
        image=pil_image,
        assertion="The text 'Hello World' is clearly visible and centered"
    )

    if not result.passed:
        raise AssertionError(f"Visual check failed: {result.reasoning}")
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage


@dataclass
class VerificationResult:
    """Result of an AI-powered visual verification check.

    Attributes:
        passed:     True if the visual assertion was satisfied.
        reasoning:  Human-readable explanation of the verification result.
        confidence: AI's confidence score (0.0-1.0). 1.0 = very confident.
    """

    passed: bool
    reasoning: str
    confidence: float


# ---------------------------------------------------------------------------
# Anthropic availability check
# ---------------------------------------------------------------------------

_ANTHROPIC_AVAILABLE = False
_ANTHROPIC_CLIENT = None

try:
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


def _get_client() -> anthropic.Anthropic | None:
    """Lazy-initialize the Anthropic client on first use."""
    global _ANTHROPIC_CLIENT

    if not _ANTHROPIC_AVAILABLE:
        return None

    if _ANTHROPIC_CLIENT is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        import anthropic

        _ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=api_key)

    return _ANTHROPIC_CLIENT


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------


def check_image(
    image: PILImage.Image,
    assertion: str,
    *,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 300,
) -> VerificationResult:
    """Verify that an image satisfies a visual assertion using Claude's vision API.

    Args:
        image:       A PIL Image to verify.
        assertion:   A natural-language statement describing what should be
                     visible in the image. Examples:
                     - "The text 'Game Over' is displayed in large red font"
                     - "Three blue buttons are horizontally aligned at the bottom"
                     - "A health bar is visible above each unit sprite"
        model:       Claude model to use. Default: claude-3-5-sonnet-20241022.
        max_tokens:  Maximum response tokens. Default 300 (enough for reasoning).

    Returns:
        VerificationResult with passed, reasoning, and confidence fields.

    Notes:
        - If anthropic library is not installed, returns a permissive result
          with a warning in the reasoning.
        - If ANTHROPIC_API_KEY is not set, returns a permissive result.
        - The function converts the PIL Image to PNG bytes and sends it to
          Claude's vision API with a structured verification prompt.
    """
    client = _get_client()

    if client is None:
        # Graceful fallback: anthropic not available or API key missing
        reason = (
            "anthropic library not installed or ANTHROPIC_API_KEY not set. "
            "Skipping AI verification (auto-pass). Install with: "
            "pip install anthropic"
        )
        return VerificationResult(
            passed=True,
            reasoning=reason,
            confidence=0.0,
        )

    # Convert PIL Image to base64-encoded PNG
    image_bytes = _image_to_base64(image)

    # Build the verification prompt
    prompt = _build_prompt(assertion)

    # Call Claude's vision API
    try:
        import anthropic

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_bytes,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        # Parse the response
        return _parse_response(response)

    except Exception as e:
        # API call failed — return a failure result with the error
        return VerificationResult(
            passed=False,
            reasoning=f"AI verification failed: {e}",
            confidence=0.0,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _image_to_base64(image: PILImage.Image) -> str:
    """Convert a PIL Image to base64-encoded PNG string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _build_prompt(assertion: str) -> str:
    """Build the verification prompt for Claude.

    The prompt asks Claude to:
    1. Examine the image
    2. Determine if the assertion is satisfied
    3. Respond in a structured format: PASS/FAIL, reasoning, confidence
    """
    return f"""You are a visual quality assurance assistant for a game framework's screenshot tests.

Your task is to verify the following assertion about the provided image:

ASSERTION: {assertion}

Examine the image carefully and determine whether the assertion is satisfied.

Respond in this exact format:

VERDICT: PASS or FAIL
REASONING: <1-2 sentence explanation of why it passed or failed>
CONFIDENCE: <0.0 to 1.0, where 1.0 means very confident>

Examples:

VERDICT: PASS
REASONING: The text "Game Over" is clearly visible in large red font at the center of the screen.
CONFIDENCE: 0.95

VERDICT: FAIL
REASONING: The expected three blue buttons are not visible. Only two buttons are present and they appear gray.
CONFIDENCE: 0.9

Be precise and objective. Focus on what is visually present in the image."""


def _parse_response(response: anthropic.types.Message) -> VerificationResult:
    """Parse Claude's response into a VerificationResult.

    Expected format:
        VERDICT: PASS or FAIL
        REASONING: <explanation>
        CONFIDENCE: <float>
    """
    # Extract text content from the response
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    # Parse the structured response
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    verdict = "FAIL"
    reasoning = "Unable to parse AI response"
    confidence = 0.5

    for line in lines:
        if line.startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.split(":", 1)[1].strip())
            except ValueError:
                confidence = 0.5

    passed = verdict == "PASS"

    return VerificationResult(
        passed=passed,
        reasoning=reasoning,
        confidence=confidence,
    )
