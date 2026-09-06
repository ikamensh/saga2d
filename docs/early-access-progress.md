# Early Access progress and evidence

Criteria: [early-access-criteria.md](early-access-criteria.md).
All release gates remain incomplete unless evidence below explicitly proves
them. Last completed development milestone was a single-shard prototype;
the current goal is substantially broader.
Entries below are chronological checkpoints; their measurements apply to
the named source snapshot, and later entries supersede earlier feature gaps.

## Current playable checkpoint — 2026-09-06

The preserved Mac development build is source **0e27175**. It includes the
three-shard campaign, three saved difficulty modes, eight authored adventure
families, ten recruitable roles, twelve relics, and 100/125 reading size for
Codex, Guide and expedition briefings. [Exact artifact and native evidence](evidence/shardbound-integrated-0e27175/README.md)
identify what is playable; all G01–G19 release gates remain incomplete.

This source passes 1,041 tests and both games' bounded fuzz checks. Native
mode/old-save, full Challenge recovery and four Explorer journeys pass 1,089
inputs and 47 exact reloads. A separate 138-record guidance matrix covers every
current approach at both reading sizes and all three supported window sizes.
The extracted frozen app and macOS app-launch smoke pass with isolated saves,
settings restart and all shipping audio assets. Screenshots were inspected.

Source development after that packaged checkpoint adds readable purchase
catalogues and Hero equipment, with an optional Tower infusion command. These
changes are not in the preserved `0e27175` app. The next work concerns recurring
economic choices, the ninth authored encounter and readable reward decisions.
Resource surpluses, complete text scaling,
human playtests, Windows/clean-account execution and candidate-specific stress
remain open. The README's first framework example is now an asset-free runnable
game; its mouse and keyboard controls were exercised with mock and native input.
The changes above compose existing Saga2D primitives and add no strategy rules
to the framework.

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

## World, objective, capability and audio integration — 2026-09-06

- `cc14670` makes Border Watch a visible expedition: inspect the actual layout,
  defenders, reward and one-action cost; return without spending; aim at its
  seal with O; save after the first holding turn; win or reach the deadline.
  The full native manual journey, terminal reload and one-time reward passed.
  See [eador-hold.md](eador-hold.md).
- Three generated themes are merged, with title/CLI selection in `a926b54`.
  Frontier, Elderwild and Ruins expose different terrain, route rewards and
  defenders. The model audit completed 720 prepared victories across heroes,
  themes and three routes, plus 100-seed-per-theme random campaigns. These
  show viable policies, not balanced difficulty or all viable builds. Title,
  save, replay and map headings preserve the selected world. See
  [eador-worlds.md](eador-worlds.md).
- `5d5842b` exposes Archer/Storm Quiver Pin with an exact forecast, legal target
  markers, a movement-status badge and visible cooldown. Watch Bell heroes use
  the Brace button through their capability. The native input journey also
  earns the Bell and uses it in a subsequent saved battle. There are five
  recruit roles, four active capabilities plus Guard, eight relics and eight
  site definitions; Explorer's Camp is not an authored encounter pattern.
  See [eador-pin.md](eador-pin.md).
- `c2299dd` connects two original music loops and twelve cues through the
  existing game audio manager. A tiny game-owned app factory supplies asset,
  theme and save defaults; no rule or content ID entered Saga2D. Preferences
  apply before playback, overlays retain music, disabled orders stay silent,
  and saved terminal results do not replay victory cues. The source packaging
  smoke decodes and plays every installed WAV and tests live mix/cleanup.
  Human listening approval is still outstanding. See
  [eador-audio.md](eador-audio.md).
- Packaging now snapshots its spec and deterministic package-data list,
  verifies all audio against provenance, and records installed data hashes.
  Source and relocated-snapshot smoke pass. The old frozen macOS artifact is
  unchanged and does not represent these additions; Windows remains untested.
- Latest full suite passed **643 tests**; an additional manual movement,
  attack, Bolt, Heal and refused-cast audio journey also passed. Both fuzz
  drivers passed after integration, including random visible Pin orders.
  General native scenes, settings, Pin and Watch journeys passed. Screenshots
  were inspected; fixes include briefing overlap, cramped title controls,
  battle-header placement and overflowing help text.

G01–G19 remain incomplete. Linked-stage rules and a minimal shared native
window API are developing independently. Next acceptance work includes the
complete linked UI, broader content/build/economy choices, settings and
presentation, then a new packaged candidate and candidate-specific stress.
The shipping logical canvas uses letterboxing for smaller windows; arbitrary
logical resizing and text scaling are not established by that evidence.

## Support roles and extraction controls — 2026-09-06

- `b3485fe` exposes Acolyte healing, Ranger movement after shooting and Warden
  Swap through mouse and keyboard, with exact forecasts and paged recruitment.
  Signed combat feedback respects reduced motion. Its layering uses the small
  shared `Scene.screen_layer()` scope; rules and effect styling stay in Eador.
  See [support-role evidence](eador-roles.md) and the independent
  [framework layering demo](framework-screen-layers.md).
- `93b5cf8` adds two authored carry-and-escape layouts with four approach
  choices, persistent wounded defenders and exactly recorded rewards. The
  integrated briefing, numbered exits, explicit Evacuate button and Codex
  make both missions manually playable. Four native paid-army routes pass,
  with 65–137 inputs and 2–5 exact reloads each. The existing full linked
  Rootward/Gate input journey also passes. See
  [extraction rules and UI evidence](eador-extraction.md).
- `7148998` fixes a separately reproduced Tribes quick-load stale-hover bug.
  Public regressions and native checks cover missing resources and smaller
  maps; the development fuzzer now reproduces both world and input seeds.
- `c691ded` retains native departure/recovery checks when every autosave is
  damaged, including refusal, a fresh manual checkpoint, arrival and exact
  reload. Arrival guidance now fits the screen while preserving damaged files.
- The integration suite passes 810 tests; both games' ordinary fuzz runs pass.
  The content/role expansion, twelve-relic target, difficulty and human
  playtests remain open, alongside the other G01–G19 requirements. These
  source increments have not updated the historical packaged artifact.

## Linked progression, display and economy baseline — 2026-09-06

- `00df6c4` makes the three-shard campaign playable through the title, challenge
  comparison, explicit veteran/relic selection, recovery and ending screens.
  `14dcd39` adds the J contract panel, numbered map targets, final ritual
  pre-entry briefing and mouse controls for larger retinues. Complete native
  Rootward/Gate and Foundries/Throne journeys, including recovery, used 356
  and 377 input activations with 11 and 13 exact manual save/reloads. Captured
  screens were inspected and clipped captions corrected. These are automated
  journey counts; their short runtime is not a measure of human pacing.
  See [eador-linked-ui.md](eador-linked-ui.md).
- V8 rule evidence includes 880 complete linked routes across heroes and
  challenge choices, plus 300 randomized runs entering all three stages.
  Every hero has a manual final-seal victory with defenders still alive.
  See [eador-campaign.md](eador-campaign.md) for source-specific reports,
  policy limits and replay commands.
- An unreadable set of rolling autosaves no longer traps a ready departure
  or recovery. An exact current manual checkpoint can protect the transition;
  stale snapshots cannot. Damaged files remain intact. Native journeys
  exercise refusal, a fresh manual save, departure and exact reloading of the
  pre-departure state. Save-browser labels identify stage, contract and
  departure/recovery/completed/lost phase (`645b545`).
- Native window sizing, fullscreen and restoration are reusable Saga2D
  operations, with a separate game-owned preference screen. Apply/Cancel,
  startup overrides, Retina sizing and a resized-window/fullscreen roundtrip
  were exercised through native input and screenshots. See
  [framework-display.md](framework-display.md) and
  [eador-display-settings.md](eador-display-settings.md). Text scaling is still
  absent; the motion preference's combat presentation is a later increment.
- The historical `31a2c88` two-hour native soak completed: 429,506 frames,
  577 journeys, p95 11.988 ms and bounded RSS plateaus. The retained
  [soak report](soak.md) names the machine, source snapshot, timing samples
  and memory limits. It predates current campaign, role, audio and display
  changes and does not pass the current candidate's G15 requirement.
- The read-only v9 [economy audit](eador-economy-v9.md) (`5c13b5e`, measured
  source `cfaf982`) completed 3,600 matched victories: 100 seeds, three worlds,
  four heroes and three fixed build policies. Marketplace-first was faster;
  Mage-Tower-first suffered fewer retreats. All plans eventually share a
  military/healing core, and crystals were spent only 0 / 0 / 2 on average.
  This is route robustness and evidence of an open economy gap, not difficulty
  balance or completion of G07. No opportunistic balance changes were made.

## Control retinue and Ruins extraction — 2026-09-06

- The integrated roster has ten recruits and eight distinct combat abilities.
  `c8f9fa4` provides saved finite Smoke/Repulse, Militia Rally, Skyrider flight
  and terrain sight. UI controls show exact Rally reach, Repulse landings,
  cloud duration/charges and crystal recruitment costs. The paid combined
  Watch route (`7d42eba`) passes through native input with 158 activations and
  eight exact reloads; all seven allies survive a hold victory. Separate
  native Smoke, Rally and Repulse journeys pass. See
  [control UI evidence](eador-control-ui.md).
- Troop silhouettes (`3fd1212`) distinguish the canister-bearing Sapper,
  tablet-bearing Adept and mounted Skyrider. Native review caught wings and
  spears obscuring adjacent health labels; existing screen layers now place
  statuses/HP above pieces and feedback above those labels.
- `69174ca` completes the [Sealed Vault tranche](eador-vault.md): the same
  purchased army escapes the free route in round four or spends two crystals
  for round two, with real differences in mana and wounds. Both native routes,
  finite retries, exact old-save continuation and 300 randomized campaigns
  pass. This brings authored battlefield families to five, not twelve.
- Combined source passes **843 tests**. Ordinary Tribes and linked Shardbound
  fuzz runs also pass after the control changes. Source/UI evidence does not
  update the historical frozen artifact or satisfy candidate-specific stress.

G01–G19 remain incomplete. Twelve relics, more meaningful authored patterns,
whole-campaign build/difficulty comparisons and ability-aware automatic play
are continuing. A new frozen artifact, candidate-specific stress, Windows
runtime, text scaling, human playtests and listening review remain required.

## Authored rout presentation and combined control integration — 2026-09-06

- Merged the validated control/flight automatic policy and finite Smoke-order
  validation; its source-specific evidence and attrition debt are in
  [eador-control-model.md](eador-control-model.md).
- Pack Hunt's initial model tracer now uses an explicit game-owned encounter
  objective. Its briefing and Codex describe the rout objective, show
  each deployment and fee, and preserve cancellation and saved entry decisions.
  Tactical rout battles now state their objective above the board. All site
  briefings show their remaining finite defender HP.
- This is the presentation checkpoint, not completion of Pack Hunt's authored
  content gate: manual route comparison and deployment tuning are still in
  progress. No Saga2D scenario API was added.
- Combined source passed **861 full tests**, 60 Tribes AI games and 20 random
  Tribes input runs, plus 12 linked model campaigns and 12 linked scene runs
  (2,227 inputs). Both Pack Hunt entry choices were captured and inspected
  natively: 22 inputs, two exact quicksave/reloads, free cancellation, correct
  rout briefing/board/Codex. Final reward/guardian copy passed 11 focused tests.

## Twelve relics, completed Pack Hunt and reusable text flow — 2026-09-06

- `3923255` completes Pack Hunt's sixth authored family with three paid-army
  manual plans and finite failed-attempt/retry evidence. The free Commander
  plan takes three rounds; its 20-gold northern approach takes two and saves
  four HP. A cheaper Warrior/Pikeman formation also wins, with greater wounds.
  The rout has no separate mission deadline, but the global 80-round exhaustion
  still applies; current briefing/board/Codex disclose this. See
  [Pack Hunt evidence](eador-pack-hunt.md). Twelve authored families remain
  required; ordinary source sites such as Muster Yard do not count as authored
  battlefield families merely because they have a new reward.
- `9d52700` integrates twelve discoverable relics, including the hero's
  Smoke, Repulse, Swap and Rally alternatives. New reward sources preserve old
  equipment availability across 100 seeds per theme. Saved existing sites and
  battle capabilities retain their prior identities. All four rewards were
  earned, reloaded, kept and equipped through native input; original icons and
  long descriptions were inspected. [Relic presentation](eador-relic-art.md)
  records the game-owned art and truthful capability/charge guidance.
- `d1c9fea` adds a native earned Censer journey: fund the army, escape with the
  reward, equip it, and hold a later Watch with every ally alive. The journey
  uses 251 input activations and 12 exact reloads; forecast/result screenshots
  were inspected. Paired model routes measure only one HP saved in the first
  enemy phase, and a poor screen blocks friendly healing. This is a modest
  tactical option, not proof of equipment balance. Earned-use journeys for the
  remaining three relics are still being integrated.
- Saga2D now provides `Label(text, width=300, wrap=True)`. Measured wrapping,
  reactive font/text changes and the next control's hit bounds reflow together,
  including beneath paused overlays. This shares the existing paragraph
  algorithm and preserves its native pixels; no game rules entered the
  framework. The [independent example and retained evidence](framework-wrapped-label.md)
  cover native input, text bounds, fonts and resizing. This primitive alone does
  not provide Shardbound text scaling.
- Combined main passes **896 tests**, with source-specific Tribes and Shardbound
  fuzz evidence retained for the integrated control, content and layout work.
- A preserved Mac development artifact at source `f63aa6f2806c` was offered for
  an opening playtest. It predates final Pack Hunt tuning and the four new
  relics. [The playtest log](eador-playtests.md) records the exact artifact and
  pending feedback; no human playtest is counted yet.

G01–G19 remain incomplete. The next increments address earned relic use, the
seventh authored encounter and larger reference text. Difficulty selection,
whole-campaign balance/pacing, complete text scaling, candidate-specific stress,
Windows runtime, human playtests and listening review remain open.

## Earned relic use through the complete input path — 2026-09-06

- All four new relics now have native earned-use journeys at the same integrated
  source `a288171`: Censer/Watch hold, Rune/Ruins Gate recovery hold,
  Badge/Elderwild Gate exchange hold, and Drum/Watch Pin removal followed by rout.
  Purchases, rewards, equipment and both linked departures use visible controls;
  1,316 input activations and 45 exact reloads pass. Both Gate routes complete
  their linked campaigns. [Retained relic evidence](eador-active-relics.md#native-earned-use-verification)
  includes reports, inspected forecasts/results and the explicit tactical limits.
- The shared test driver now rejects missing command adapters. Previously a
  forwarded method could mutate the model without UI input; public recovery
  and battle-movement regressions reproduce that gap. The stricter path passes
  all 904 tests and all four native journeys.
- Model evidence varies 400 continuations from four earned checkpoints, with
  16,038 full-save checks, and separately validates 300 random campaigns. These
  counts establish saved-order robustness, not 400 independently generated
  worlds or equipment balance.

G01–G19 remain incomplete. Broken Observatory, scoped larger Codex text and
difficulty design continue independently; global text scaling, content depth,
economy/pacing, platform, candidate stress and human feedback remain open.

## Observatory choices and larger reference text — 2026-09-06

- Broken Observatory is the seventh authored family, using the existing hold
  objective, finite guards and saved approach data. Native purchased Sapper and
  paired Rune armies pass 610 inputs and 26 exact reloads at `46a5aa8`, with all
  allies alive. The same Rune orders show the two-crystal lane saves six wounds,
  with no phase saved. [Reports and inspected images](eador-observatory.md)
  preserve that limited comparison alongside finite retry and old-save evidence.
- Codex reading size now offers 100/125%, with measured whole-entry pages and
  persistent Apply/Cancel/restart/recovery. It explicitly affects reference
  content only. A native resize regression found and fixed cached text metrics
  being reused at the wrong scale; the framework caches physical glyph metrics
  and converts them at the current viewport scale, without a new public method.
  [Reading-size verification](eador-reading-size.md) includes old and current
  saved rules. Root inspected larger entries, Settings and the paid Observatory.
- Combined integration passes 924 tests, the independent native resize metrics,
  pixels and clicks in both directions, Tribes' 60-game/20-scene fuzz and
  Shardbound's 12-campaign/12-scene linked fuzz. These are development checkpoints.

G01–G19 remain incomplete. Three-mode difficulty is under model review and
matched evaluation; its UI is next. Global text scaling, remaining authored
patterns, campaign economy/pacing, platform checks and human feedback remain open.

## Saved realm modes and honest economic readouts — 2026-09-06

- Three title/CLI modes now select frozen, saved realm parameters. Old saves
  acquire Standard metadata without replaying grants or changing live battles.
  Map, Hero, Rival, save browser and linked briefings show the saved mode, actual
  production modifier, capped recovery and model-owned expedition funding.
- Native `3638b69` runs select all three modes, purchase and recover an army,
  change the next-run choice and reload exact progress in fresh Games. Three
  complete linked input journeys use 1,108 activations and 35 exact reloads;
  Accessible also loses a realm, launches its funded recovery and completes.
  [Source hashes, inputs and inspected images](evidence/shardbound-difficulty-2026-09-06/README.md)
  preserve the scope. The combined source passes 958 tests and both games'
  bounded fuzz checks.
- The matched 32,400-run model audit finds Accessible's plans finish sooner
  with fewer casualties on average. Challenge's sustain plan has a long mana
  recovery tail, and every plan leaves excess crystals. Difficulty selection
  is implemented; tuning and meaningful recurring resource sinks remain work
  in progress. No difficulty or campaign policy entered Saga2D.

G01–G19 remain incomplete. Larger guidance text and the eighth authored encounter
are separate increments. Content depth, economy/pacing, candidate-specific
stress, platforms and human feedback remain open.

## Readable decisions and the ninth encounter — 2026-09-06

Smuggler Screen is integrated at `5941f60`. Its paid western, northern and
smaller Scout plans exercise Smoke, Rally, flanking and finite failed-attempt
recovery. All five native journeys pass with the new measured result panels:
1,073 inputs and 58 exact reloads. The integrated suite passed 1,083 tests;
both games' bounded fuzz checks passed. [Retained evidence](evidence/shardbound-results-screen-5941f60/README.md)
separately attributes the eight-outcome result matrix and current Screen runs.
The earlier `0e27175` Mac artifact predates these changes.

G01–G19 remain incomplete. Reward reading, explicit paid troop replacement,
remaining campaign layouts, economy/pacing, content depth, candidate stress,
platform checks and human feedback remain active work.

## Paid role access and larger decision screens — 2026-09-06

At `ad9026b`, players can explicitly retire a veteran and buy a fresh recruit in
the same formation slot. The review shows lost rank/XP, full cost, one-action
payment, role and upkeep. Its native saved Warden assault demonstrates a manual
Swap → Heal rescue, while the retained comparisons keep ordinary rest and its
lower-cost outcomes visible. This does not resolve the economy gate.

Reward choices and campaign plans now use the same 100/125 reading setting.
The replacement native matrix passes 120 complete reviews and 1,170 inputs;
the integrated suite passes 1,108 tests. Real filesystem-error overflow bugs
were reproduced and fixed before the checkpoint. [Evidence and inspected frames](evidence/shardbound-replacement-ad9026b/README.md)
distinguish this source from earlier artifacts and isolated model stress.

G01–G19 remain incomplete. Remaining reading layouts, replacement input stress,
additional authored patterns, economic balance, candidate-specific stress,
platform verification and human feedback remain active work.

## Complete save metadata and a smaller framework interface — 2026-09-06

Saves now show complete phase metadata, including results awaiting acceptance,
and page whole slots around larger text or actual filesystem errors. Explicit
backup restoration and failed save-before-title recovery pass through native
controls. Rival intelligence also supports the shared reading size with its
complete current orders, finite army and economic/breakout advice.

`Scene.measure(component)` removes the repeated temporary attachment needed
to measure prospective UI trees. It supplies the actual theme/font context
without taking ownership or activating controls; save and rival layouts use it.
The independent example verifies that measured cards match their eventual
rendered sizes. No game or pagination policy entered Saga2D.

At `f3a59e2`, the suite passes 1,119 tests and both games' bounded stress checks.
Native verification covers the independent example, 54 save pages and 90 rival
layouts. [Retained checks and inspected frames](evidence/framework-ui-measurement-f3a59e2/README.md)
preserve source attribution. Replacement scene stress is now integrated too;
[its report](eador-replacement-fuzz.md) separates random input coverage from
the dedicated successful paid journeys.

G01–G19 remain incomplete. Campaign transitions/retinue and tactical/HUD
reading, the tenth and remaining authored patterns, meaningful economy,
candidate-specific stress, platforms and human feedback remain active work.
