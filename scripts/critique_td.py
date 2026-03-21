#!/usr/bin/env python3
"""Send Tower Defense screenshots to Gemini 2.0 Flash for visual critique.

Uses the Gemini REST API with GOOGLE_API_KEY environment variable.
Scores each screen 0-10 and provides specific feedback on:
  - Grass tile seamlessness and banding artifacts
  - Tower slot visibility and clarity
  - Enemy sprite scale and distinguishability
  - HUD/UI text readability and layout
  - Path clarity and visual hierarchy
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Error: 'requests' library required. Install with: pip install requests")


BASELINE_DIR = Path(__file__).parent.parent / "td_baseline"
TITLE_IMAGE = BASELINE_DIR / "td_title.png"
GAMEPLAY_IMAGE = BASELINE_DIR / "td_game_initial.png"
ACTION_IMAGE = BASELINE_DIR / "td_game_action.png"

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def _load_image_b64(path: Path) -> str:
    """Read an image file and return its base64-encoded content."""
    if not path.exists():
        sys.exit(f"Error: Screenshot not found: {path}")
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _build_title_prompt() -> str:
    """Build the critique prompt for the title screen."""
    return """You are a professional game UI reviewer. You are looking at the **TITLE SCREEN** of a tower defense game called "Tower Defense" (a Saga2D framework example).

Rate this screen on a scale of 0-10 (10 = polished indie release quality, 0 = broken).

Provide specific feedback on ALL of the following aspects:

1. **Layout & Composition**: Is the title centered and well-positioned? Is the button arrangement clear and inviting? Is screen space used efficiently or is there excessive emptiness?

2. **Typography**: Is the title text readable and appropriately sized? Is the subtitle ("An Saga2D Example") visible but not distracting? Are button labels clear?

3. **Color Balance**: Do the colors work well together (title, subtitle, buttons, background)? Is there sufficient contrast? Does it feel cohesive?

4. **Professional Polish**: Does this feel like a finished game or a placeholder? Are there any rough edges, alignment issues, or obvious visual flaws?

Respond in this EXACT format (no markdown fences):

SCORE: <integer 0-10>
LAYOUT: <1-3 sentences>
TYPOGRAPHY: <1-3 sentences>
COLOR_BALANCE: <1-3 sentences>
POLISH: <1-3 sentences>
OVERALL: <1-2 sentence summary>"""


def _build_gameplay_prompt() -> str:
    """Build the critique prompt for the gameplay screen."""
    return """You are a professional game UI reviewer. You are looking at the **INITIAL GAMEPLAY SCREEN** of a tower defense game. The screen shows a grid-based map with grass tiles, a winding path, tower placement slots (translucent emerald squares with cyan crosses), a HUD at the top, and a build menu on the right.

Rate this screen on a scale of 0-10 (10 = polished indie release quality, 0 = broken).

Provide specific feedback on ALL of the following aspects:

1. **Grass & Path Clarity**: Are the grass tiles seamless or are there visible seams/banding? Is the winding path clearly distinguishable from grass? Does the path look like a path or just lighter tiles?

2. **Tower Slot Visibility**: Are the tower placement slots (emerald squares with crosses) easy to identify? Do they stand out appropriately without being distracting? Are they clearly buildable locations?

3. **HUD & Build Menu**: Is the top HUD (Wave, Gold, Lives, Score) readable? Is the right-side build menu clear? Are tower options (Basic/Sniper/Splash) well-presented? Is text appropriately sized?

4. **Visual Hierarchy & Polish**: Is there a clear visual hierarchy (background → gameplay elements → UI)? Does the overall presentation feel cohesive? Are there obvious visual flaws or placeholder-looking elements?

Respond in this EXACT format (no markdown fences):

SCORE: <integer 0-10>
TERRAIN: <1-3 sentences>
TOWER_SLOTS: <1-3 sentences>
UI: <1-3 sentences>
HIERARCHY: <1-3 sentences>
OVERALL: <1-2 sentence summary>"""


def _build_action_prompt() -> str:
    """Build the critique prompt for the action gameplay screen."""
    return """You are a professional game UI reviewer. You are looking at an **ACTIVE GAMEPLAY SCREEN** of a tower defense game. The screen shows enemies (small circular sprites) moving along the path, a placed tower, active wave status, and updated HUD.

Rate this screen on a scale of 0-10 (10 = polished indie release quality, 0 = broken).

Provide specific feedback on ALL of the following aspects:

1. **Enemy Visibility**: Are the enemy sprites clearly visible and distinguishable? Are they appropriately sized relative to tiles and path? Can you identify them as enemy units or do they blend into the background?

2. **Tower & Projectile Clarity**: Is the placed tower clearly visible? Can you identify it as a defensive structure? If there are projectiles, are they visible? Does combat feel readable?

3. **Gameplay Readability**: Is it easy to understand what's happening? Can you track enemy movement? Is the active state (wave progress, gold changes) communicated clearly through the UI?

4. **Overall Polish**: Does the action feel dynamic and engaging visually? Are there obvious rough spots like placeholder art or scale issues? Does it feel like a real game or a prototype?

Respond in this EXACT format (no markdown fences):

SCORE: <integer 0-10>
ENEMIES: <1-3 sentences>
TOWERS: <1-3 sentences>
READABILITY: <1-3 sentences>
POLISH: <1-3 sentences>
OVERALL: <1-2 sentence summary>"""


def _call_gemini(api_key: str, image_b64: str, prompt: str) -> str:
    """Send an image + prompt to Gemini 2.0 Flash and return the text response."""
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": image_b64,
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 600,
        },
    }

    resp = requests.post(
        GEMINI_URL,
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if resp.status_code != 200:
        detail = resp.text[:500]
        sys.exit(f"Gemini API error ({resp.status_code}): {detail}")

    data = resp.json()

    # Extract text from response
    try:
        candidates = data["candidates"]
        text = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        sys.exit(
            f"Unexpected Gemini response structure: {e}\n{json.dumps(data, indent=2)[:800]}"
        )

    return text


def _parse_score(response_text: str) -> int | None:
    """Extract the SCORE value from a structured response."""
    for line in response_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("SCORE:"):
            try:
                return int(stripped.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _print_section(header: str, response_text: str) -> None:
    """Pretty-print a critique section."""
    width = 75
    print("=" * width)
    print(f"  {header}")
    print("=" * width)
    print()
    print(response_text.strip())
    print()


def main() -> None:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("Error: GOOGLE_API_KEY environment variable not set.")

    print("Sending Tower Defense screenshots to Gemini 2.0 Flash for critique...\n")

    # --- Title Screen ---
    print("Analyzing title screen...")
    title_b64 = _load_image_b64(TITLE_IMAGE)
    title_response = _call_gemini(api_key, title_b64, _build_title_prompt())

    # --- Initial Gameplay Screen ---
    print("Analyzing initial gameplay screen...")
    gameplay_b64 = _load_image_b64(GAMEPLAY_IMAGE)
    gameplay_response = _call_gemini(api_key, gameplay_b64, _build_gameplay_prompt())

    # --- Action Gameplay Screen ---
    print("Analyzing action gameplay screen...\n")
    action_b64 = _load_image_b64(ACTION_IMAGE)
    action_response = _call_gemini(api_key, action_b64, _build_action_prompt())

    # --- Output ---
    title_score = _parse_score(title_response)
    gameplay_score = _parse_score(gameplay_response)
    action_score = _parse_score(action_response)

    _print_section("TITLE SCREEN CRITIQUE", title_response)
    _print_section("INITIAL GAMEPLAY CRITIQUE", gameplay_response)
    _print_section("ACTION GAMEPLAY CRITIQUE", action_response)

    # --- Summary ---
    print("=" * 75)
    print("  SUMMARY")
    print("=" * 75)
    print()
    ts = f"{title_score}/10" if title_score is not None else "N/A"
    gs = f"{gameplay_score}/10" if gameplay_score is not None else "N/A"
    as_ = f"{action_score}/10" if action_score is not None else "N/A"
    print(f"  Title Screen:         {ts}")
    print(f"  Initial Gameplay:     {gs}")
    print(f"  Action Gameplay:      {as_}")

    scores = [s for s in [title_score, gameplay_score, action_score] if s is not None]
    if scores:
        avg = sum(scores) / len(scores)
        print(f"  Average:              {avg:.1f}/10")
    print()


if __name__ == "__main__":
    main()
