"""Ask a vision-capable LLM to critique a rendered saga2d screenshot.

Uses Gemini via the Generative Language API (GOOGLE_API_KEY). Falls back
to OpenAI (OPENAI_API_KEY) if the first call fails. Input is a PNG path;
output is the model's short critique printed to stdout.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


PROMPT = """You are an experienced 2D game art / UI critic reviewing a SKETCH
screenshot from an early prototype. It is intentionally minimal.

Please keep your answer under 250 words and structured as:

1. What works visually
2. Top 3 concrete issues a game dev would reject ("would not ship")
3. One suggestion that would most raise perceived quality without new art
4. Any rendering bug or layout collision you can see

Be specific — reference elements by position (e.g. "top-center 'S' node").
Do not be polite at the expense of useful critique.
"""


def load_env() -> dict[str, str]:
    secrets = Path.home() / "ai-workspace" / "secrets" / "llm-providers.md"
    env: dict[str, str] = {}
    if secrets.is_file():
        for line in secrets.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                if k and v and k not in env:
                    env[k] = v
    for k, v in os.environ.items():
        env[k] = v
    return env


def call_gemini(image_b64: str, api_key: str, model: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                    {"text": PROMPT},
                ],
            }
        ],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from e


def call_openai(image_b64: str, api_key: str, model: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"

    def _do(token_field: str) -> str:
        body = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
            token_field: 1200,
            "temperature": 0.4,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]

    # gpt-5.x rejects `max_tokens` and wants `max_completion_tokens`.
    # Try the modern field first; fall back on older models that still
    # require the legacy name.
    try:
        return _do("max_completion_tokens")
    except urllib.error.HTTPError as e:
        if e.code == 400:
            # Re-read the body; some older models require `max_tokens`.
            return _do("max_tokens")
        raise


def call_claude(prompt: str, api_key: str, model: str) -> str:
    """Call Anthropic Messages API for a text-only synthesis step."""
    url = "https://api.anthropic.com/v1/messages"
    body = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return "".join(
        part.get("text", "")
        for part in data.get("content", [])
        if part.get("type") == "text"
    )


SYNTH_PROMPT = """You are synthesising two independent visual reviews of the
same game UI screenshot. Extract signal from noise: items BOTH reviewers
raise are high-signal (CONSENSUS); items only one raises are noise (DRIFT).

{reviews}

Output *exactly* this structure, nothing else:

## CONSENSUS
- <issue>: <≤15 words describing how both reviewers framed it>
- (list every issue both raise, even if phrased differently)

## DRIFT (single-reviewer, treat as noise)
- Reviewer A only: <issue>
- Reviewer B only: <issue>

## RECOMMENDED NEXT ACTION
<one concrete change that addresses the highest-impact consensus item,
≤40 words>

Under 250 words total. No preamble, no closing remarks.
"""


def _try_gemini(image_b64: str, key: str) -> tuple[str, str] | None:
    for model in ("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"):
        try:
            return (f"gemini/{model}", call_gemini(image_b64, key, model))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")[:300]
            print(f"[gemini/{model}] HTTP {e.code}: {err_body}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[gemini/{model}] {e}", file=sys.stderr)
    return None


def _try_openai(image_b64: str, key: str) -> tuple[str, str] | None:
    for model in ("gpt-5.1", "gpt-4o", "gpt-4o-mini"):
        try:
            return (f"openai/{model}", call_openai(image_b64, key, model))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")[:300]
            print(f"[openai/{model}] HTTP {e.code}: {err_body}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[openai/{model}] {e}", file=sys.stderr)
    return None


def review(image_path: Path) -> tuple[str, str]:
    """Return (provider_used, critique_text).

    Single-model path kept for backward compatibility. Prefer
    :func:`cross_check` to silence single-model drift (iter-6 lesson).
    """
    env = load_env()
    image_b64 = base64.b64encode(image_path.read_bytes()).decode()
    r = None
    gemini_key = env.get("GOOGLE_API_KEY")
    if gemini_key:
        r = _try_gemini(image_b64, gemini_key)
    if r is None:
        openai_key = env.get("OPENAI_API_KEY")
        if openai_key:
            r = _try_openai(image_b64, openai_key)
    if r is None:
        raise RuntimeError("No LLM provider succeeded (checked Gemini + OpenAI).")
    return r


def cross_check(image_path: Path) -> list[tuple[str, str]]:
    """Call Gemini AND OpenAI in parallel and return every critique that
    came back. The caller can then extract consensus from overlaps.

    This is the iter-7 fix for single-model drift: a single reviewer's
    feedback oscillates round-to-round (``keras.dev`` iter-6 meta-note).
    Agreement *across independent models* in the same round is the real
    signal; disagreement is noise.
    """
    env = load_env()
    image_b64 = base64.b64encode(image_path.read_bytes()).decode()
    results: list[tuple[str, str]] = []
    gemini_key = env.get("GOOGLE_API_KEY")
    if gemini_key:
        r = _try_gemini(image_b64, gemini_key)
        if r:
            results.append(r)
    openai_key = env.get("OPENAI_API_KEY")
    if openai_key:
        r = _try_openai(image_b64, openai_key)
        if r:
            results.append(r)
    if not results:
        raise RuntimeError("No LLM provider succeeded (checked Gemini + OpenAI).")
    return results


def synthesise_consensus(
    critiques: list[tuple[str, str]],
    env: dict[str, str] | None = None,
) -> str | None:
    """Use a neutral third model (Claude Haiku) to extract consensus.

    Returns the synthesis string on success, or ``None`` when no
    ANTHROPIC_API_KEY is available or the call fails. Fewer than two
    critiques yields ``None`` — there's nothing to compare.
    """
    if len(critiques) < 2:
        return None
    env = env if env is not None else load_env()
    api_key = env.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    reviews_block = "\n\n".join(
        f"--- Reviewer {chr(65 + i)} ({provider}) ---\n{text}"
        for i, (provider, text) in enumerate(critiques)
    )
    prompt = SYNTH_PROMPT.format(reviews=reviews_block)
    for model in ("claude-haiku-4-5-20251001", "claude-sonnet-4-6"):
        try:
            return call_claude(prompt, api_key, model)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")[:300]
            print(f"[claude/{model}] HTTP {e.code}: {err_body}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[claude/{model}] {e}", file=sys.stderr)
    return None


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ring_of_pain.png")
    mode = sys.argv[2] if len(sys.argv) > 2 else "cross"
    if mode == "single":
        provider, critique = review(path)
        print(f"=== Provider: {provider} ===\n{critique}")
    else:
        critiques = cross_check(path)
        for provider, critique in critiques:
            print(f"\n{'=' * 60}\n=== Provider: {provider} ===\n{'=' * 60}")
            print(critique)
        synthesis = synthesise_consensus(critiques)
        if synthesis:
            print(f"\n{'=' * 60}\n=== Synthesis (Claude) ===\n{'=' * 60}")
            print(synthesis)
