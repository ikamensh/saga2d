# Explicit Game closure — 2026-09-06

This isolated increment starts at `03ded5eb21a729ad89d745e416dcc00be8590226`
on `codex/game-close`. It adds `Game.close()` and shares final shutdown with
`run()`, `render_scene()` and independent examples. No game rules change.
See [the interface and caller problem](../../framework-game-lifetime.md).

The new public integration regression first failed at `game.close()` with
`AttributeError: 'Game' object has no attribute 'close'` (one failure, 0.02s).
The worktree initially lacked pytest; `--extra dev` installs the repository's
declared test dependencies.

After implementation, this focused command passed **26 tests in 1.10s**:

```sh
uv run --extra dev python -m pytest tests/framework/test_game_close.py \
  tests/framework/test_scene_stack.py tests/framework/test_frame_pacing.py -q
```

The tests cover explicit ticks and closure, failed exit cleanup, subsequent
Game creation, existing run-error preservation, scene lifetimes and frame
pacing. The independent mock demo also exited successfully:

```sh
uv run python tools/demo_game_close.py
```

Both demo backends report two closed sessions and six updates. The first
native attempt failed during Pyglet's `get_default_screen()` before a Game
window could be created: the display was asleep. After waking/holding the
display, the root agent ran the same native example successfully (exit 0,
0.663s wall time):

```sh
caffeinate -du uv run --extra dev python tools/demo_game_close.py --backend pyglet
```

The demo explicitly checks `backend.window is None` on Pyglet and stopped
backend state on mock after each closure. Native frames use the existing
30 FPS helper. All executions were serial; test/demo processes ended and
the native windows closed. A read-only peer review found no actionable issue.

The follow-up replaces six repeated cleanup blocks in four Shardbound
verification tools with the public operation: directed journeys, paid army
decisions, saves and results. Their initial and restarted sessions now share
the framework's shutdown behavior. **19 focused integration tests pass in
6.91s** ([retained output](verifier-tests.log)), including real input/save
journeys and observation of both stopped mock backends after restart checks:

```sh
uv run --extra dev python -m pytest tests/tools/test_directed_journey_input.py \
  tests/tools/test_army_decision_input.py tests/tools/test_verifier_preparation_budget.py \
  -k 'directed or input_reload or verifier' -q
```

This is focused evidence for the new lifetime interface, not a current full
suite or cross-game fuzz result. Those integration checks remain due when the
isolated change is merged; no release gate is marked complete here.
