# Early Access progress and evidence

Criteria: [early-access-criteria.md](early-access-criteria.md).
All release gates remain incomplete unless evidence below explicitly proves
them. Last completed development milestone was a single-shard prototype;
the current goal is substantially broader.

## Baseline audit — 2026-09-05

- Authoritative baseline: `2d26787`; only unrelated `.gitignore` work was
  present when the release-quality goal began.
- Existing tests: 314 at the preceding milestone, confirmed by a fresh run.
- The release gap includes content/decision variety, rival strategy,
  progression choices, save robustness, usability, audio, packaging and
  release-scale testing. These are not resolved by a green baseline suite.
- Model audit reproduced a safe capital-camping strategy: by turn 65 the
  army reached level 4 with 791 gold and 66 crystals, then won at turn 68.
  Scheduled attacks provide repeated rewards without a changing opponent.
- Rival conquest can replace a four-unit eastern guard with two units,
  reducing danger when the rival expands. Crystals start at four while
  the only expense is one Mage Tower costing two.

## Gate status

G01–G19: **incomplete**. The baseline has partial evidence for basic tactical
commands (G08), public-behavior tests (G16) and framework separation (G17),
but does not satisfy their release-candidate scope.

## Progression and save reliability — 2026-09-05

- All four heroes have two rankable disciplines. Every discipline and
  relic has a tested behavioral effect; mastery can stay on its chosen
  path instead of converging into the same build at level three.
- Six adventure archetypes have distinct defending parties and rewards.
  Six relics offer equipment-versus-money choices, with explicit duplicate
  handling. Their choices and equipped effects have playable UI.
- Schema v2 validates game IDs and state invariants, including live battle
  context and pending decisions. Captured prototype fixtures migrate
  explicitly. Corrupt JSON, oversized integers and excessive nesting
  report recoverable errors at the parser boundary.
- Three manual slots, three rolling autosaves, a save browser and explicit
  previous-file recovery are usable from live campaigns and decisions.
  Failed loads preserve live state; incompatible campaigns preserve their
  backups; Save & title leaves only after writing a chosen manual slot.
- Framework additions remain generic: queued-input transition safety;
  durable, validated SaveManager writes and explicit backup reads; cleanup
  of partially initialized scenes and failed game startup.
- Standalone macOS ARM64 build and extracted-package smoke passed. See
  [packaging.md](packaging.md) for commands, hashes and limitations. That
  artifact is an earlier source snapshot; Windows and a clean-machine
  release candidate remain unverified.
- Latest checkpoint: **395 tests passed**, including complete campaign
  input, saved decisions, equipment, damaged-file recovery and safe return
  to title. Real Pyglet keyboard/mouse verification passed, including
  Shift-number backup recovery. Screenshots of shard, battles, guide,
  choices, inventory, save browser and error states were inspected at
  1280×800 / macOS HiDPI (`/tmp/shardbound-reviewed`).
- Independent review found and drove fixes for giant-number JSON escaping
  the game error boundary and repeated equipment hotkeys rotating away
  useful autosaves. Framework lifecycle tests also reproduce resource
  leaks and startup failure recovery.

G01–G19 remain incomplete. This increment advances G03–G05, G12–G14,
G16–G17; content counts alone do not establish their full release bar.
Large-scale stress evidence is running separately. Immediate design work
is a finite opponent with observable intent, resources and lasting army
losses; the current timer-driven rival remains a known release gap.

No release claim or publication is authorized by this progress log.

## Stress baseline and keyboard tactics — 2026-09-05

- The `31a2c88` source baseline passed 1,000 model campaigns and 100,039
  random public input activations with unchanged source hashes. Full
  metrics and scope limits are in [eador-stress.md](eador-stress.md).
- A two-hour real Pyglet soak of an archived `31a2c88` snapshot is running;
  [soak.md](soak.md) documents the harness and live report location. Its
  completion, final memory trend and performance gates are not yet known.
- Battle aiming now has a keyboard path: arrows and Page keys move the
  cursor, F cycles targets, Enter/Space selects or acts, 1/2 aim spells,
  and T retreats. Keyboard and mouse share one action handler. Casting
  at an empty hex no longer turns into an unintended move.
- A public keyboard-only journey moves, casts, attacks, saves, restores
  and retreats. The real Pyglet journey also passed; screenshots at
  1280×720, 1280×800 and 1920×1080 window sizes were inspected on HiDPI.
  These use the same 1280×800 logical canvas with letterboxing; they do
  not establish text scaling or a full all-screen/settings matrix.
- Both fuzz drivers passed after the keyboard input change; the Eador
  driver now includes aimed keyboard commands. Full suite passed during
  integration. The earlier 100,000-input report remains explicitly tied
  to its measured baseline.

Finite rival development is isolated on `codex/shardbound-rival`; it has
not yet been merged or accepted. G01–G19 remain incomplete.

## Codex and button-owned shortcuts — 2026-09-05

- The field codex is reachable from the shard, battle, guide, hero and
  decision screens. Its six categories describe the current troops,
  spells, buildings, skills, sites and relics using the actual rule tables.
  Inspecting it preserves the underlying scene and campaign state.
- Saga2D buttons can own an optional shortcut, including modifiers and
  aliases. Keycap, activation and disabled/visible state share one
  declaration. Shardbound's catalogues, choices, paged inventory and save
  browser now use it; separate dynamic bindings were removed. The
  independent example and behavior contract are documented in
  [framework-button-shortcuts.md](framework-button-shortcuts.md).
- The full suite passed **421 tests**; both games' fuzz drivers passed.
  Native Pyglet verification exercised the codex, campaign/battle input,
  choices, equipment, save slots and backup recovery, plus resized windows.
  Screenshots were inspected at `/tmp/shardbound-codex-final`; a crowded
  shard header found during review was corrected before this checkpoint.

This advances G09, G10 and G17. It does not establish the first-time human
walkthroughs, complete display/settings matrix or release readiness.

## Finite rival and visible counterplay — 2026-09-05

- The finite rival is merged. It moves a persistent army, fights province
  guards with ordinary tactical rules, retains casualties and wounds, and
  spends its treasury to recover/recruit at Duskspire. Interception and
  defense use that same expedition. A defeated expedition needs four turns
  before its first paid replacement, creating a saved counterattack window.
  See [rival-design.md](rival-design.md) for rules and measured model evidence.
- The map marks the army with a numbered diamond. V opens its current
  orders, target/countdown, individual health, treasury, income, upkeep and
  refit costs. Locate selects its province without advancing play. Returning
  from inspection preserves a selected province; resolving movement still
  follows the hero.
- Schema v3 preserves rival operations, soldier identities and wounded
  garrisons. Captured v1/v2 fixtures migrate without rerolling pending
  decisions or changing an existing defense's tactical continuation.
  Independent review found routing oscillation and inconsistent saved
  orders/identities; targeted regressions and fixes are included.
- Full integration passed **432 tests**, plus both games' fuzz drivers.
  Native `tools/verify_eador_rival.py` passed inspection, interception,
  retreat with lasting wounds, saved reengagement, defense and the paid
  remustering window through actual mouse/keyboard input. Initial, wounded,
  located and defeated-expedition screenshots were inspected at
  `/tmp/shardbound-rival-first`. The regular native save/input/window-size
  journey also passed after integration.

G06 remains incomplete: profitable indefinite capital camping still needs
economic pressure, and broader balance/content evidence remains outstanding.
Encirclement and unpaid upkeep are the next isolated rules increment.
