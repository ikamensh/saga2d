# Tester (browser / display) — Saga2D

## Project shape

- **No shipped web UI** in this repo (no HTML/SPA). “Open in browser” does not apply unless a separate web front-end is added.
- **Sibling `saga2d_xvfb_consumer`:** also **no web UI** — desktop Pyglet (`python -m xvfb_consumer`), optional Linux `xvfb-run` + `xdotool`. Scope there is MessageScreen → ChoiceScreen + hub panel; not ConfirmDialog / SettingsScene / SequenceRunner / DnD unless extended.
- Interactive verification is **pyglet windowed** (`game.run()`) or **headless pyglet** via `tests.screenshot.harness.render_scene()` (`visible=False`).

## This environment (darwin, Cursor agent)

- **`xvfb-run`:** not installed (`which xvfb-run` → not found). Typical on **macOS**; Xvfb/`xvfb-run` are Linux CI patterns. For Linux CI headless GUI, install `xvfb` and wrap with `xvfb-run -a python ...`.
- **Saga2D headless smoke:** `uv run python -c "from tests.screenshot.harness import render_scene; ..."` succeeds — real pyglet backend, invisible window, framebuffer capture OK.
- **Root `test_pyglet_headless.py`:** fails on **pyglet 2.x** (`glColor3f` / immediate-mode GL removed); failure is **API mismatch**, not “no OpenGL”. Prefer harness or modern GL for a minimal display test.
- **Window size:** invisible `pyglet.window.Window(width=960, height=540)` may report different logical size (e.g. Retina); not necessarily a bug.

## Agent constraints

- **AGENTS.md:** do not launch visible fullscreen/interactive `game.run()` demos from the agent (macOS focus steal). Use `backend="mock"`, `tick()`, or `render_scene()`.
- **This session:** no interactive browser automation tool (no Playwright/Cursor browser MCP). URL fetch alone cannot substitute for clicking through a UI.

## Patterns worth reusing

- Headless graphical verification: `render_scene(setup, tick_count=2, resolution=(800, 600))` then inspect PNG (per CLAUDE.md).
