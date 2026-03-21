# User Stories for Testing

Stories are tracked across `kodo test` runs. Each story records:
- **Last tested:** commit hash when this story was last verified
- **Status:** pass | fail | partial | blocked | untested
- **Findings:** references to findings from test reports

Public API: 63 symbols in `saga2d.__all__` (see `saga2d/__init__.py`).

**Harness abbreviations:** Consumer, Fuzz, Integration, UI (D–I), Systems (J–Q), Bug Repro (R–Y), Final Verification (AA–AE).

---

## Lifecycle

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US1 | Install saga2d from source with `pip install -e .` in clean venv (63 symbols) | 721e565 | pass | Consumer | Consumer: 63 symbols import, Game(mock), tick OK |
| US2 | Import all 63 public API symbols from saga2d | 721e565 | pass | Consumer | Consumer: all 63 symbols import + exec star-import |
| US3 | Create a Game with mock backend, push a Scene, tick frames | 721e565 | pass | Consumer | Consumer: Game(mock), push(Scene), tick(0.016), top() verified |
| US4 | Push/pop/replace scenes with proper lifecycle hooks firing | 721e565 | pass | Lifecycle | Lifecycle: push→on_enter, push-over→on_exit, pop→on_exit+on_reveal, replace→on_exit+on_enter |
| US5 | Game._teardown() cleans up: singletons reset, no leaked state between games | 721e565 | pass | Consumer | Consumer: _teardown(), _current_game is None |
| US10 | Scene lifecycle: on_enter, on_exit, on_reveal fire in correct order | 721e565 | pass | Lifecycle | Lifecycle: global log confirms cross-scene hook ordering |
| US11 | Deferred scene ops: push/pop/replace during update flushes after tick | 721e565 | pass | Lifecycle | Lifecycle: push/pop/replace during update() deferred, flushed after tick |
| US12 | clear_and_push clears stack before pushing new scene | 721e565 | pass | Lifecycle | Lifecycle: clear_and_push exits all (reverse), stack=1 |
| US13 | replace() calls on_exit on replaced scene, on_enter on new scene | 721e565 | pass | Lifecycle | Lifecycle: replace→on_exit old+on_enter new, no on_reveal |

## Actions

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US6 | Create sprites, set positions, animate with actions (MoveTo, FadeIn, PlayAnim, etc.) | 6b74177 | pass | ActionStress | Sprite create/position, MoveTo, FadeOut→0, FadeIn→255 all verified |
| US7 | Build composable action trees: Sequence(Parallel(...), Do(...), Delay(...), Repeat, FadeOut) | 6b74177 | pass | ActionStress | 100-deep nesting, 500-wide Parallel, 200-instant Do chain verified |
| US8 | Action edge cases: MoveTo speed=0 (ValueError), Delay(0), empty Sequence, Repeat(0) | 6b74177 | pass | ActionStress | NaN speed bug FIXED (now ValueError); speed=0/neg rejected; Delay(0)/empty Seq/Par/Repeat(0/1) all OK |
| US9 | Sprite lifecycle edge cases: remove during action, action on removed sprite | 6b74177 | pass | ActionStress | Remove() in Sequence, do() on removed sprite (no-op), external remove all safe; instant chain Do fires after Remove |
| US22 | Parallel with finite children completes when all done | 6b74177 | fail | ActionStress | BUG: Parallel(only infinite) completes immediately (vacuous truth); finite completion correct |
| US23 | Do(callback) executes callback when reached in Sequence | 6b74177 | pass | ActionStress | Delay→Do fires at correct time; chains instantly; mid-Sequence Do verified |

## UI

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US14 | HUD renders between base scene and overlay scenes | — | untested | — | UI G |
| US15 | show_sequence() chains MessageScreens correctly | — | untested | — | Systems Q |
| US16 | DataTable, Grid, List, ProgressBar, TextBox, Tooltip, TabGroup, ImageBox | — | untested | — | UI G, Final Verification AD |

## Input

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US17 | Input binding: bind keys to actions, verify dispatch chain | — | untested | — | Systems O, Bug Repro V |
| US18 | Camera offset affects UI click coordinates correctly | — | untested | — | Bug Repro V, Final Verification AA |

## Audio

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US19 | Play sounds, music, crossfade between tracks | — | untested | — | Integration, Systems M |
| US20 | Audio with missing files: optional=True graceful, optional=False raises | — | untested | — | Final Verification AB |

## Rendering

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US21 | Use Camera: follow sprite, pan, shake, world bounds | — | untested | — | Integration, UI I |
| US24 | Camera pan_to edge cases: NaN, duration=0, bounds exceeded | — | untested | — | UI I, Final Verification AA |

## Systems

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US25 | Save game state, load it back, verify consistency | — | untested | — | Systems J |
| US26 | AssetManager: load images, fonts; AssetNotFoundError | — | untested | — | Bug Repro R,S,Y, Final Verification AB |
| US27 | CursorManager: set cursor, reset on scene exit | — | untested | — | Systems L, Final Verification AE |
| US28 | Scene stack on empty stack: pop(), replace(), verify no crash | 721e565 | fail | BugRepro | pop() empty survives, but on_exit() exception blocks pop (Bug) |

## Util

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US29 | Use timer.after() and timer.every() with chained .then() | — | untested | — | Systems N |
| US30 | Tween sprite properties with various easing functions | — | untested | — | Systems N, Bug Repro W |
| US31 | Use StateMachine for game logic FSM | — | untested | — | Systems K |
| US32 | Scene-owned timer chain (.then()) cancelled on scene exit | — | untested | — | Bug Repro U |
| US33 | Concurrent tween/timer on same property | — | untested | — | Final Verification AC |

## Events

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US34 | Event types: KeyEvent, MouseEvent, WindowEvent, InputEvent | — | untested | — | Systems O, Bug Repro V,X |
| US35 | Scene re-entrancy: push/pop/replace from on_enter, update, etc. | — | untested | — | Bug Repro T |

## UI & Rendering (moved)

| # | Story | Last tested | Status | Findings | Notes |
|---|-------|-------------|--------|----------|-------|
| US36 | Build a UI with Panel, Button, Label — click button triggers callback | — | untested | — | Integration |
| US37 | Theme and Style: apply theme, override per-component | — | untested | — | UI D |
| US38 | UI drag-and-drop: drag component, drop on target | — | untested | — | UI F |
| US39 | ChoiceScreen, ConfirmDialog, MessageScreen, SaveLoadScreen | — | untested | — | UI E, Final Verification AD |
| US40 | Scene with ParticleEmitter: emit, lifetime, cleanup on scene exit | — | untested | — | UI H, Final Verification AE |
| US41 | ColorSwap, get_palette, register_palette | — | untested | — | UI H |
