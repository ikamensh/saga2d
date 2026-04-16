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
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 600,
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


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ring_of_pain.png")
    mode = sys.argv[2] if len(sys.argv) > 2 else "cross"
    if mode == "single":
        provider, critique = review(path)
        print(f"=== Provider: {provider} ===\n{critique}")
    else:
        for provider, critique in cross_check(path):
            print(f"\n{'=' * 60}\n=== Provider: {provider} ===\n{'=' * 60}")
            print(critique)
