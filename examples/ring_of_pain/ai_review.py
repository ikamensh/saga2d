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
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
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


def review(image_path: Path) -> tuple[str, str]:
    """Return (provider_used, critique_text)."""
    env = load_env()
    image_b64 = base64.b64encode(image_path.read_bytes()).decode()

    # Try a Gemini model list in order of preference.
    gemini_key = env.get("GOOGLE_API_KEY")
    if gemini_key:
        for model in ("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"):
            try:
                text = call_gemini(image_b64, gemini_key, model)
                return (f"gemini/{model}", text)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode(errors="replace")[:300]
                print(f"[gemini/{model}] HTTP {e.code}: {err_body}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                print(f"[gemini/{model}] {e}", file=sys.stderr)

    openai_key = env.get("OPENAI_API_KEY")
    if openai_key:
        for model in ("gpt-5.1", "gpt-4o"):
            try:
                text = call_openai(image_b64, openai_key, model)
                return (f"openai/{model}", text)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode(errors="replace")[:300]
                print(f"[openai/{model}] HTTP {e.code}: {err_body}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                print(f"[openai/{model}] {e}", file=sys.stderr)

    raise RuntimeError("No LLM provider succeeded (checked Gemini + OpenAI).")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ring_of_pain.png")
    provider, critique = review(path)
    print(f"=== Provider: {provider} ===\n{critique}")
