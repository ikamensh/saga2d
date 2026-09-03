# Worker Smart Notes — Saga2D

## Project
- 2D game framework (Python 3.12+, pyglet backend, mock backend for headless testing)
- Repo: `/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d`
- Run tests: `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q`
- Smoke test: `uv run python scripts/smoke_game_move_to.py` (no env vars needed)

## Key Architecture
- `saga2d/` — core package: Game, Scene, Sprite, actions, audio, UI components, util (tween, timer, fsm)
- `saga2d/rendering/` — camera.py, sprite.py, particles.py, animation.py, layers.py
- `saga2d/ui/` — component.py (base Component + _UIRoot), components.py (Label/Button/Panel), widgets.py (List/Grid/DataTable/etc), layout.py, theme.py
- `saga2d/backends/` — mock_backend.py (headless), pyglet_backend.py
- `tests/` — 2795+ tests (headless), organized by area (actions/, core/, rendering/, systems/, ui/, integration/, kodo_test_*.py, test_kodo_*.py)

## Test Counts (2026-03-25, post-Stage 5 final)
- 2795 passed, 3 skipped (game.run() under SAGA2D_HEADLESS), 0 failures (excluding visual_verify)
- ~31s runtime (headless)

## Stage 1 Status — COMPLETE (2026-03-25)
- Scope: Environment Setup & Smoke Testing — game loop, push/pop scenes, backend protocol, Game + Scene/SceneStack
- Smoke script `scripts/smoke_game_move_to.py` validates Game→Scene→Sprite→MoveTo E2E

## Stage 2 — Core Engine & Actions Edge Cases (2026-03-25)
### Investigation results
- Game.tick(NaN/Inf/negative): already guarded with ValueError — no new bug
- Do(non-callable): already guarded with TypeError — no new bug
- Repeat(times=float/NaN): already guarded with TypeError — no new bug
- **F42**: Repeat(times=negative_int) silently accepted — no-op instead of error
- **F43**: MoveTo(scalar/1-tuple) leaked raw IndexError/TypeError

### Fixes applied
- F42: `saga2d/actions.py` — Repeat.__init__ raises ValueError for negative times, TypeError for bool
- F43: `saga2d/actions.py` — MoveTo.__init__ validates position with iter()/next(), gives clear TypeError messages

### Files changed
- `saga2d/actions.py` — F42 + F43 fixes
- `tests/test_kodo_stage2_regression.py` — NEW, 20 regression tests (6 for F42, 14 for F43)
- `tests/test_kodo_stage2_core_actions.py` — updated 2 tests to expect new exceptions
- `tests/test_kodo_new_edge_cases.py` — updated 1 test to expect ValueError
- `tests/kodo_test_rendering.py` — updated 1 test to expect ValueError; fixed 2 stale timer regex patterns
- `test-report.md` — added Stage 2 section with repro steps, fixes, verification
- `.kodo/test-coverage.md` — updated gap table statuses for exercised/fixed items

## Stage 3 — UI/Rendering Edge Cases (2026-03-25)
### Investigation results (11 bugs confirmed via runtime probes)
- ProgressBar ctor: NaN/Inf bypassed setter validation (stored directly)
- Button.text=None: crashed downstream in _estimate_text_width
- ParticleEmitter.position=NaN: silently stored, crashed at burst time
- AnimationPlayer.update(NaN): frozen permanently (elapsed became NaN)
- Camera.enable_edge_scroll/key_scroll: NaN margin/speed accepted
- Camera.world_bounds: NaN + inverted bounds accepted
- Tooltip(delay=NaN/Inf/-1): misbehaved or never showed
- Sprite.tint=(NaN,...): NaN passed to backend via min/max quirk
- Sprite.move_to((NaN,0)): NaN-duration tween created

### Fixes applied
- F44-F56: 13 validation bugs fixed across 8 source files
- 16 existing tests updated to expect stricter validation
- 84 new regression tests in `tests/test_kodo_stage3_ui_rendering_regression.py`
- 2 acceptable edge cases documented with tests (DataTable short col_widths, Grid zero cell_size)

### Files changed
- `saga2d/ui/widgets.py` — F44, F51, F54, F55
- `saga2d/ui/components.py` — F45
- `saga2d/rendering/particles.py` — F46
- `saga2d/animation.py` — F47
- `saga2d/rendering/camera.py` — F48, F49, F50
- `saga2d/rendering/sprite.py` — F52, F53
- `saga2d/ui/screens.py` — F56
- `tests/test_kodo_stage3_ui_rendering_regression.py` — NEW (84 tests)
- 9 existing test files updated (16 tests total)

## Stage 4 — Integration/Lifecycle Edge Cases (2026-03-25)
### Investigation results (2 bugs confirmed via runtime probes)
- F57: flush_pending_ops exception left stale ops in queue, leaking across ticks
- F58: Direct scene ops (push/pop/replace/clear_and_push) outside tick() didn't flush deferred ops from on_exit/on_reveal
- Also: deferred ops cap (1000) silently discarded ops — now logs warning and clears

### Areas verified correct (no bugs)
- Scene stack transitions during active actions/timers (owned sprites removed, timers cancelled, non-owned survive)
- Exceptions in on_enter (rollback), on_exit (finally block cleanup), on_reveal (propagates)
- Repeated Game init/teardown (5+ cycles clean, singleton guard works, double teardown safe)
- Deferred ops FIFO order, nested ops from on_enter during flush, 1000-cap for deferred path

### Fixes applied
- F57: `saga2d/scene.py` — flush_pending_ops() clears queue on exception before re-raising
- F58: `saga2d/scene.py` — added `_flush_after_direct_op()` method; called after each direct `_apply_*` in push/pop/replace/clear_and_push
- Deferred ops cap: both flush methods now log warning and clear remaining ops

### Files changed
- `saga2d/scene.py` — F57 + F58 fixes + _flush_after_direct_op method
- `tests/test_kodo_stage4_lifecycle_regression.py` — NEW, 37 regression tests
- `tests/integration/test_adversarial.py` — 3 tests updated (pending_ops == 0 after auto-flush)
- `tests/kodo_test_core.py` — 2 tests updated (negative dt ValueError, on_exit outside tick auto-flush)
- `tests/test_kodo_adversarial_fresh.py` — 1 test updated (on_exit push outside tick auto-flush)
- `scripts/stage4_probe.py` — NEW, 41 runtime probes

## Stage 4 Gameplay Workflow (2026-03-25) — NO BUGS FOUND
### What it exercises
- Full gameplay loop: Game→GameplayScene→player/enemy/ghost/coin sprites
- Input handling via mock backend inject_key → handle_input → update movement
- AABB collision detection (custom sprite_rect + aabb_collides helpers)
- Scene transitions: push PauseScene, pop via pop_on_cancel, push InventoryScene, replace VictoryScene
- Timers (scene.every, scene.after) + composable actions (Repeat, Sequence, MoveTo, FadeOut/In, Delay)
- Entity state preservation across push/pop (save in on_exit, re-create sprites in on_reveal)
- Camera follows player, draw_world_rect debug overlays

### Key insight: owned sprites removed on push-over
- `_cleanup_exiting_scene(permanent=False)` still calls `_cleanup_owned_sprites()`
- Users must save entity state in on_exit and re-create sprites in on_reveal
- Scene-owned timers survive push-over but are cancelled on permanent exit

### Files created
- `scripts/stage4_gameplay_workflow.py` — standalone headless script
- `tests/test_kodo_stage4_gameplay_workflow.py` — 24 pytest tests (16 workflow + 8 AABB unit)

## Bugs Fixed (F-numbered)
- F1-F10, F12, F15-F16, F18-F19, F21-F33, F42-F58 (46 total)
- F42: Repeat(times=negative_int) now raises ValueError (actions.py)
- F43: MoveTo position validation — clear TypeError for scalar/short-tuple/non-numeric (actions.py)
- F44: ProgressBar constructor NaN/Inf bypass — ctor now validates value + max_value (widgets.py)
- F45: Button.text=None crashes downstream — setter now rejects None with TypeError (components.py)
- F46: ParticleEmitter.position=NaN silently stored — setter now validates isfinite (particles.py)
- F47: AnimationPlayer.update(NaN) freezes permanently — now skips frame, recovers (animation.py)
- F48: Camera.enable_edge_scroll(NaN,NaN) silently breaks — now validates isfinite (camera.py)
- F49: Camera.enable_key_scroll(NaN) silently breaks — now validates isfinite (camera.py)
- F50: Camera.world_bounds=NaN/inverted silently corrupts — now validates finite + ordering (camera.py)
- F51: Tooltip(delay=NaN/Inf/-1) misbehaves — now validates finite + >=0 (widgets.py)
- F52: Sprite.tint=(NaN,...) passes NaN to backend — now validates isfinite (sprite.py)
- F53: Sprite.move_to((NaN,0)) creates NaN tween — now validates isfinite (sprite.py)
- F54: DataTable(row_height<=0) accepted — now raises ValueError (widgets.py)
- F55: Grid(cell_size=negative) accepted — now raises ValueError; zero remains accepted (widgets.py)
- F56: SaveLoadScreen(slot_count<=0) accepted — now raises ValueError (screens.py)
- F57: flush_pending_ops exception left stale ops in queue — now clears queue before re-raising (scene.py)
- F58: Direct scene ops didn't auto-flush deferred ops from on_exit/on_reveal — added _flush_after_direct_op() (scene.py)

## Stage 7 — Audio Subsystem Probing (2026-03-25)
### Target: AudioManager.set_volume — NaN/Inf validation gap
- **F59 (confirmed):** `set_volume(channel, NaN)` silently accepts NaN — clamped to 1.0 (full volume) by accident of `max(0.0, min(1.0, NaN))` argument order
- Root cause: `min(1.0, NaN)` → 1.0 on CPython 3.12+ (first arg returned when comparison is unordered), but `min(NaN, 1.0)` → NaN. Behavior is **argument-order-dependent** and platform-fragile.
- Impact: User sets volume to NaN → stored as 1.0 (max volume). No error raised. Inconsistent with every other hardened API (crossfade_music duration, Sprite.tint, Camera bounds, etc. all use `math.isfinite()`).
- Fix: Add `if not math.isfinite(level): raise ValueError(...)` before the clamp, matching the pattern in `crossfade_music`.
- **Other probes (all pass):** Inf→1.0, -Inf→0.0 (clamped correctly), crossfade(duration=0) works, play_sound(channel=bogus)→KeyError, double _teardown safe, _teardown during crossfade cleans up, NaN mid-crossfade→no NaN leaked (because NaN was already clamped to 1.0)
- **Not a bug:** bool values (True→1.0, False→0.0) — acceptable since bool subclasses int; non-numeric types crash with raw TypeError from max() — ugly but not silent corruption

### Files changed
- (none yet — F59 confirmed but not fixed)

## Stage 6 — Subsystem Test Mapping (2026-03-25, updated)
### Scope: Map 8 subsystems for future testing
- Audio, Input, Cursor, ColorSwap, Layout, Theme, DragDrop, Screens/Dialogs
- Full coverage table written to `.kodo/test-coverage.md` (§1–§8, ~160 feature rows)
- **Verified test counts** (from pytest runs): Audio 83, Input 33, Cursor 18, ColorSwap 25, Theme 13, DragDrop 49, Screens 42, Settings 36 = 299 total across primary test files
- **Source LOC**: Audio 375, Input 228, Cursor 66, ColorSwap 112, Layout 141, Theme 413, DragDrop 295, Screens 654 = 2284 total
- **Overall feature coverage: 75%** (143 tested / 48 untested across 8 subsystems)

### Key architecture patterns discovered
- **Audio**: AudioManager delegates to Backend protocol (load_sound, play_sound, etc.); volume hierarchy is multiplicative (master×channel×base); crossfade uses _CrossfadeProxy + tweens; sound pools track last-played to avoid repeats
- **Input**: Pipeline is poll→translate→dispatch (HUD→UI→Camera→Bindings→Scene.handle_input); 1:1 binding with key stealing; _MOUSE_EVENT_TYPES frozenset for world coord population
- **Cursor**: Tiny module (66 LOC); lazy Game.cursor property; scene pop auto-resets to "default"; pyglet backend flips hotspot Y coordinate
- **ColorSwap**: Pixel-level replacement at load time (not per-frame); PNG-only (CVE defense); cache key is tuple of (src,tgt) pairs; Game._teardown calls _clear_palettes
- **Layout**: Pure math layer (3 functions) + Component tree layer; Panel is primary container with NONE/VERTICAL/HORIZONTAL; Grid does cell-based layout
- **Theme**: 40+ kwargs, 8 resolve_* methods, 19 property accessors; _pick() null-coalescing pattern; Slate color scheme + Sky 400 accents
- **DragDrop**: Event hijacking during drag (all events consumed); _DragSession dataclass tracks ghost state; theme provides accept/reject overlay colors
- **Screens**: All transparent+modal; callbacks fire before pop; _SequenceRunner chains MessageScreens; _SettingsScene has rebind listening mode

### Priority gaps (largest → smallest)
1. **Theme** (🔴 45%) — 5 resolve_* + 12 property accessors untested
2. **Layout** (🟡 60%) — padding, zero-size, child>parent, negative spacing, single-child
3. **Audio** — set_volume NaN/Inf (no guard), crossfade(0), _teardown, unknown channel
4. **DragDrop** — cancel_active(), exception safety, sprite ghost, drag during scene pop
5. **Screens** — empty ChoiceScreen, key "0", double-confirm, save overwrite, rebind stealing
6. **Cursor** — missing asset, multi-cursor, non-bool set_visible
7. **ColorSwap** — _clear_palettes, duplicate source colors, non-RGBA, post-ctor swap
8. **Input** — empty/None bind args, unknown event type

### Files created/updated
- `.kodo/test-coverage.md` — comprehensive 8-subsystem coverage table with §1–§8 deep-dive, per-feature status, workflow notes, edge case suggestions

## Stage 5 — Asset/Resource Edge Cases (2026-03-25) — NO BUGS FOUND
### Investigation results (44 runtime probes, all pass)
- Missing image/sound/music → AssetNotFoundError with tried paths
- Empty string image name → AssetNotFoundError
- play_sound/play_music optional=True → returns None gracefully
- crossfade_music with missing target → AssetNotFoundError (no optional flag)
- Cache behavior correct (same handle returned for repeated loads)
- Corrupt/zero-byte files: mock backend never reads contents; PIL would fail on real decode
- ColorSwap palette errors: proper KeyError/TypeError for invalid palettes
- CursorManager missing images → AssetNotFoundError
- ParticleEmitter: deferred image validation — ctor succeeds, crashes at burst() (by design)
- Sprite.image setter with missing asset → AssetNotFoundError
- AnimationDef frame_duration ≤ 0 → ValueError
- Sprite.play() with missing frames → AssetNotFoundError
- Sprite creation after teardown → RuntimeError("No active Game")
- @2x variant selection: prefers @2x when available
- Audio channels: stop/volume on invalid channel → graceful (no crash)
- SaveManager: empty slots, corrupt JSON, binary garbage, zero-byte, non-serializable → SaveError with slot info and recovery hints
- FSM unknown event → ignored (no crash)

### Files created
- `scripts/stage5_asset_probe.py` — 44 runtime probes

### Key gaps documented (not bugs)
- Mock backend never validates file contents — corrupt media only caught by pyglet in display mode
- No optional flag on crossfade_music — users must guard missing music themselves
- ParticleEmitter deferred image validation — fail-fast alternative not available

## Key Patterns
- NaN/Inf: All public APIs validate with `math.isfinite()` (actions, tween, timer, camera, particles, widgets, sprite tint/move_to, animation.update)
- Camera: all input paths now guarded — center_on, scroll, pan_to, shake (params), update (dt), follow (target pos), enable_edge_scroll, enable_key_scroll, world_bounds setter
- Iteration safety: TweenManager, TimerManager, Component draw/update/handle_event all use `list()` snapshots
- Sprite.position setter validates finite values — prevents silent NaN corruption
- MockBackend for all headless tests; `_current_game` module-level singleton pattern
- Assets: `Sprite('sprites/knight')` resolves to `assets/images/sprites/knight.png`
- Repeat: bool is subclass of int — must check `isinstance(times, bool)` explicitly to reject it
- MoveTo: use iter()/next() for position validation — avoids index-based access that leaks raw errors
- SceneStack deferred ops: _should_defer() checks _in_tick, _flushing, _in_on_exit; direct public methods call _flush_after_direct_op() for ops queued during on_exit/on_reveal
- on_enter is NOT deferred — executes immediately (many tests depend on this behavior)

## Gotchas
- `Game.__del__` prints ImportError during Python shutdown (known F11, cosmetic)
- `Sprite` requires real asset file even with mock backend
- `SaveManager` requires `Path` not `str`
- `reversed()` on a live list does NOT protect against mutation — must use `list()` first
- Python 3.13: `min(1.0, nan)` → 1.0; `max(0.0, nan)` → 0.0 (IEEE 754 quirk)
- IEEE 754: `NaN <= 0` is False AND `NaN > 0` is False — both branches of if/else can be skipped!
- Camera.follow() NaN: without the guard, `_clamp()` with world_bounds gave platform-dependent results
