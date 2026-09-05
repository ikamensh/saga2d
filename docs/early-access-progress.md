# Early Access progress and evidence

Criteria: [early-access-criteria.md](early-access-criteria.md).
All release gates remain incomplete unless evidence below explicitly proves
them. Last completed development milestone was a single-shard prototype;
the current goal is substantially broader.
Entries below are chronological checkpoints; their measurements apply to
the named source snapshot, and later entries supersede earlier feature gaps.

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
  journey also passed after integration. Final guide review found its
  longer counterattack copy touching the footer; shortened copy was
  rerendered and inspected at `/tmp/shardbound-rival-final`.
- The expanded UI stress run includes the codex and rival report: 20 scene
  runs, 6,007 random activations, 534 codex ticks and 48 rival-report ticks
  passed, alongside 12 model campaigns. This remains a bounded increment
  check, separate from the earlier large baseline report.

G06 remains incomplete: profitable indefinite capital camping still needs
economic pressure, and broader balance/content evidence remains outstanding.
Encirclement and unpaid upkeep are the next isolated rules increment.

## Supply pressure and audio lifetime — 2026-09-06

- An encircled Westwatch loses its production, Marketplace income and
  local recovery until a neighboring province is reclaimed. Outlying
  provinces retain production. Unaffordable upkeep causes deterministic,
  logged departures that preserve more experienced troops first.
- The shard shows the blockade and the next bill's exact gold shortfall
  before End Turn. The rival report names all three breakout routes and
  explains the lost supply. Departures also produce a visible campaign
  message; the selected capital's income display reflects its blockade.
- A native journey loads an earned older campaign at an unpaid bill,
  inspects the warning, loses troops, reloads the protected manual slot,
  and fights a breakout restoring supply. Screenshots were inspected at
  `/tmp/shardbound-supply`. Model evidence includes 400 proactive victories
  across 100 seeds and four heroes, plus the passive-camping defeat and
  wounded-breakout regressions in [rival-design.md](rival-design.md).
- Active Saga2D sound effects now respond to mute/master/effects volume,
  preserve their relative gains and release playback resources at completion
  and shutdown. AudioManager's public game API is unchanged. Real backend
  checks cover sustained effects, independent managers, natural completion
  and shutdown; this fixes shared playback mechanics before Shardbound audio
  content is added.
- The combined integration suite passed **472 tests** and the native rival,
  supply and audio checks. G01–G19 remain incomplete; broader strategic
  balance, content, presentation and release-candidate evidence are still
  required. Guard/Brace rules are merged and their player controls are the
  next UI increment.

## Defensive orders and reusable preferences/audio tools — 2026-09-06

- Guard and the fifth recruit, Pikeman, have complete keyboard/mouse controls.
  G spends the selected unit's order on Guard (+2 defense), or on the Pikeman's
  pre-attack Brace. Visible stance badges, effective defense and exact HP-loss
  previews reflect the same rules. Codex, recruitment and guide explain the
  melee/ranged counterplay. Schema v4 retains stances; independent rule review
  and source-specific evidence are in [eador-guard.md](eador-guard.md).
- Native `tools/verify_eador_guard.py` recruits the Pikeman, Guards by keyboard,
  Braces by mouse, checks disabled-key behavior, expires stances and restores
  them exactly from manual saves. Screenshots were inspected at
  `/tmp/shardbound-guard`; a hint/button overlap and crowded codex text were
  fixed and rerendered. The general native input/window journey and both
  fuzz drivers passed. This UI checkpoint is `843e763`.
- Saga2D now has a small `Settings` mapping, adopted and hardened from the
  committed Warband offering. Known preference types and game-owned validators
  reject bad values. Ordinary writes refuse damaged files; explicit reset and
  save retains their exact bytes for recovery. Preferences and campaign saves
  share private durable file mechanics. See [framework-settings.md](framework-settings.md).
  The Shardbound options screen is separate work in progress.
- `saga2d.synth` extracts pure sample composition/WAV export from the existing
  games. Tribes imports the shared functions and all 18 of its generated WAVs
  remain byte-identical. An independent native compose → WAV → playback example
  passed. Invalid audio is rejected before replacing an asset. Sound composition,
  event selection and caching remain game-owned; Shardbound audio content is
  still outstanding. See [framework-synth.md](framework-synth.md).
- The combined main suite passed **515 tests** at `143628c`. This advances the
  framework and tactical foundations, not a release-candidate claim. The
  two-hour `31a2c88` real-backend soak remains running; its result cannot validate
  later rules, UI or framework changes.

G01–G19 remain incomplete. The next content increments are an authored hold
objective and three worlds with different route/resource decisions, followed
by further active abilities, adventure choices and linked-campaign progression.
