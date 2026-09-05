# Working in parallel on this repository

Two agents may be active at once. This file is the channel: append a dated
note under "Notes" when you start or finish something another agent should
know about, and read it before touching shared files.

## Ownership

| Area | Owner | Notes |
|---|---|---|
| `warband/`, `tests/warband/`, `tools/fuzz_warband.py`, `tools/verify_warband.py`, `docs/warband-*.md` | Warband agent (branch `warband`) | |
| `eador/`, `tests/eador/`, `docs/eador-*.md`, `docs/early-access-*.md` | Shardbound agent (branch `main`) | |
| `tribes/`, `tests/tribes/` | shared; small edits only, say so here | Warband moved Tribes' renderer, effects, sound synth and fonts into saga2d |
| `saga2d/`, `tests/framework/`, `DESIGN.md`, `README.md` | shared | additions must serve two games; merge often to avoid drift |

## Protocol

- Work on your own branch in a git worktree (`git worktree add .claude/worktrees/<name> -b <name>`);
  never `git add -A` in a tree another agent may be editing.
- Merge `main` into your branch regularly and keep the branch a clean
  fast-forward for main; leave the fast-forward of `main` itself to the user
  or to the agent that owns main's working tree.
- The whole suite (`uv run python -m pytest tests -q`) must stay green on
  every commit, including the other game's tests.
- Framework changes: say what both games need from them, in DESIGN.md.

## Notes

- 2026-09-05 (Warband agent): branch `warband` holds the RTS and nine
  framework additions (render3d camera, effects, synth, fonts, update_image,
  Minimap, mouse modifiers, UI order stride, render3d.scale); it is merged
  with main up to `300ac87` and fast-forwards cleanly. Next: content depth
  (units, buildings, upgrades, difficulties), then settings/saves — the
  settings file and autosave/slot browser will be offered as saga2d pieces
  since Shardbound's gates G10/G12 want the same.
- 2026-09-05 (Warband agent, later): merged main's hardened `saga2d/save.py`
  with the named slots/summaries (`76619dd`; both test files green). Backend
  performance changes that affect every game: pyglet `debug_gl` is turned off
  in `saga2d/__init__.py`, `draw_image` pools its GPU sprites, and sprite
  appearance setters skip unchanged values (`0630136`). A pixel-level pyglet
  test lives in `tests/framework/test_pyglet_backend.py` and skips without a
  display. `tools/perf_warband.py` is the frame-time evidence tool.
