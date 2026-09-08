# Early Access progress and evidence

Criteria: [early-access-criteria.md](early-access-criteria.md).
All release gates remain incomplete unless evidence below explicitly proves
them. Last completed development milestone was a single-shard prototype;
the current goal is substantially broader.
The current checkpoint comes first. Historical measurements and feature gaps
apply to their named source snapshots, not to today's build.

## Current source work — 2026-09-08

**ed27f24** completes three native screenshot/critique/improvement passes on
the shard map: compact landmark labels and full names on demand, a centered
board, consolidated summaries, wider objective text and clearer contextual
actions. [Before/after frames and validation](evidence/shard-ui-2026-09-08/README.md)
include 25 targeted tests, a bounded input audit, and five native cases with
95 province selections and four exact command comparisons. Seven final PNGs
were inspected; the accepted native run averaged about 25% of one CPU core.
This source work is newer than the preserved Mac archive below.

The development-only concurrent campaign model now supports two independent
realms buying buildings/troops and settling a shared day after both mark Ready.
Shared realm purchases and solo compatibility are checkpointed. Independent
PvE encounters, conflict claims, human PvP and playable network presentation
remain open; the selectable multiplayer mode is still shared-realm co-op.

## Current packaged checkpoint — 2026-09-07

The latest preserved Mac development archive is clean source **2d9520a**:
[runnable artifact, exact source and inspected packaged frames](evidence/shardbound-package-2d9520a/README.md).
It includes the recent attack motion, contact feedback, overlay sound fix and
inspection icons. Five packaging tests, extracted-app native smoke, an earned
125% casualty forecast, retained inventory/signature verification and a separate
LaunchServices smoke pass. The previous package remains preserved.

Economy and army-result extractions are verified prerequisites for concurrent
campaign PvP. Shared-world independent realms, claims and Ready coordination
remain to be built; battles retain ordinary turns. Existing multiplayer is
shared-realm co-op. The new package does not inherit the older build's full
linked-campaign verification. Windows, human listening/playtests and overall
Early Access acceptance remain open. **G01–G19 remain incomplete.**

## Earlier playable checkpoint — 2026-09-07

The latest preserved Mac development archive is clean source **7b5562d**:
[runnable artifact, exact source and packaged frames](evidence/shardbound-package-7b5562d/README.md).
It now includes the painted environment/portraits, illustrated terrain and role
miniatures, icon toolbars and stats, richer sound, compact tactical controls,
varied saved adventure locations and the existing shared-realm implementation.
Ready evacuation guidance and singular foe text are corrected. No new game
rules or framework API were needed for this refresh.

[Ordinary validation](evidence/shardbound-candidate-validation/README.md) covers
**1,542 current cases** across seven staged runs and the two display checks;
all 110 game/framework/cross-game Python files match across those runs. Stale
paid-route assertions were repaired, two superseded experiment runners and four
dedicated tests were removed, and every initial failure is retained. **159
expensive cases remain deferred**; two packaged-campaign mock cases passed
separately. A small seed-0 Standard model audit completes **24/24** linked
journeys, including eight recoveries, using the existing autoplay policy.

The extracted frozen app passes installed assets/audio, settings and saved-input
checks plus direct and actual lost-capital recovery campaigns across nine
processes: **976 native inputs, 17 UI save/reloads and seven exact process joins**.
Both endings restore at 125% and return to title. All 53 retained package frames
were inspected, using exact-hash representatives for duplicates. A second
extraction, local ad-hoc signature and LaunchServices smoke pass. The archive is
49,259,991 bytes; its manifest and full hash are retained with the evidence.

The campaign phase bodies average about 26.61% of one core at the requested 25%
allowance and 30 FPS native cap; startup/cleanup and the uncapped sole build job
are outside that timing. Expensive jobs ran serially and ended. The ordinary
UI-only attempt encountered the locked Mac before any game observation, then
closed its own process. Human playtests/listening, artifact co-op connectivity,
clean-account/Windows and current sustained acceptance remain open. A manual-only
Windows build workflow and concrete runtime handoff are prepared but unexecuted.
No cancelled matrix/soak, remote dispatch or publication was performed.
**All G01–G19 gates remain incomplete.**

## Earlier playable checkpoint — 2026-09-06

The latest preserved Mac development archive is clean source **32f354c**:
[build identity, full tests and packaged frames](evidence/shardbound-package-32f354c/README.md).
It includes the CPU caps, About screen and isolated profiles from the prior
archive, plus lethal attack warnings and battle health labels that remain within
their pieces. Selected-unit corner ticks distinguish selection from targeting.

The clean checkout passes **1,264 tests in 188.44 seconds**. The actual extracted
frozen app passes its save/settings/input/audio smoke and the new earned casualty
diagnostic at 100% and 125% text size, including an unchanged State and exact
reload. Two packaged battle frames were inspected independently; a second
extraction passes local ad-hoc signature verification. Test and build jobs ran
serially and ended. This refresh does not repeat full frozen campaigns or claim
Windows, clean-account, human/listening or sustained acceptance.
**All G01–G19 gates remain incomplete.**

[The remaining audit CPU follow-up](evidence/remaining-audit-cpu-31c4bee/README.md)
adds the 25% cooperative allowance to resource-breakpoint, Aerie and Relief
audits, including paid preparation and detached quotes, plus Pin's model-only
preparation. Fifty-six focused tests pass; two small serial CLI checks average
about 28–29% of one core including startup and report writing, with unchanged
outcomes. No cancelled matrix or soak was restarted. That increment changes
development tools only; the subsequent autoplay change below is not packaged.

[Current source d643410](evidence/autoplay-survival-d643410/README.md) lets another
ready ally act before retrying a predictably lethal player autoplay attack. It
preserves the earned Control Adept that the earlier policy needlessly lost.
The full suite passes **1,275 tests**; four current earned branches pass **165
native inputs, 24 forecast layouts and 17 exact command/save/reload joins** through
rewards and paid replenishment. Inspected images show the surviving veteran and
paid aftermath. Tribes fuzz and a bounded 12-model/12-scene Shardbound run pass;
the random campaigns end in defeat and do not count as winning strategies.

The three paid campaign policies were rerun at the 25% CPU allowance. Sustain is
unchanged; Mobile completes with worse total time and casualties; Control stops
at its existing policy bound with the first shard still playing. All 767 saved
commands and the unfavorable outcomes are retained. The historical three-army
completion claim does not apply to this source. A local autoplay fix does not
establish campaign balance or manual depth. The independent UI-only attempt again
timed out before observing any game, and its launched app was closed. All jobs
ended; no cancelled large matrix or soak was restarted. The Mac archive above
predates this battle-policy change. **All G01–G19 remain incomplete.**

[Verification preparation and cleanup in 9bcca4b](evidence/verification-helper-cpu-9bcca4b/README.md)
extend the 25% cooperative allowance to save/result preparation and the older
Relief prototype's searches. Both verifiers close their initial and restarted
rendering backends. Nine focused integration checks pass; one tiny real prototype
run completes in 1.11 seconds at about 42% of one core including startup and
report writing. This is not a strict CPU quota or battery-life measurement. No
native window or large stress job was launched, and all jobs ended. This changes
development tools only; game/framework bytes remain those of d643410.

[Directed Control and pacing in f78359d / 990c377](evidence/directed-control-990c377/README.md)
add 184 explicit commands from the historical earned turn-6 opening to first-shard
victory at turn 9. The paid Adept/Skyrider purchases, two infusions, three battles
and one actual Militia casualty are retained with agent rationales and mistakes.
The opening used autoplay; the next two linked shards remain unplayed in this
continuation. Native input matches all 184 command/save/reload joins across 794
events, with three screenshots inspected. The run averages 25.44% of one core
over 66.37 seconds at the default CPU allowance and 30 FPS native cap.

The retained replacement prototype now shares that CPU allowance through its
battle and investment loops. Save verification also requires an actual written
slot and a replaced live State after F9, and rejects read-only queries counted as
gameplay commands. Forty-five focused integration tests pass in 18.20 seconds.
All jobs ran serially and ended; no large matrix, soak or packaged refresh was
run. **All G01–G19 remain incomplete.**

[The directed Foundries continuation](evidence/directed-foundries-03ded5e/README.md)
extends the same journal to 428 commands and second-shard departure at turn 4.
Seven victories retain all five troops, with actual paid support recruitment,
three ordinary rests and earned Channeling II. The shared mana pool is exhausted
in the eight-round capital battle; the departure retains 158 gold and 17 crystals.
All commands resume from exact serialized results. The additional second-shard
commands still need native replay, and the finale remains in progress at this
checkpoint. A fresh UI-only attempt stopped at the locked Mac before observing
the game; its own process was closed. No human-playtest, full-campaign or release
gate credit is claimed. Game and framework source hashes remain unchanged.

[Four remaining retained economy prototypes](evidence/retained-prototype-cpu-83e01be/README.md)
now share the default 25% CPU allowance through paid preparation, cloned battle
comparisons and recovery. Full-speed execution requires explicit `--cpu-percent
100`. Their existing experimental rules and sample matrices are unchanged.
Sixteen tests pass in the main checkout at `3c1d546`; a single short real helper
probe yields at about 29% of one core during its measured work. No default matrix
or native window was launched. All test/probe processes ended, then the directed
finale resumed. This changes development tools only; all G01–G19 remain open.

[Paid Vault continuation](eador-vault-continuation.md) now follows an earned
two-crystal unseal through production and veteran replacement. In this seed-7
example it captures production two turns earlier and retains the original
Militia, finishing 38 gold and two crystals ahead at the same turn-11 endpoint.
The report includes the free route's actual 14-gold replacement and all exact
reloads. It establishes this local tradeoff, not general scarcity or balance.

## Earlier About-screen checkpoint — 2026-09-06

The prior Mac development archive is clean source **a6851fb**:
[build identity, screenshots and verification](evidence/shardbound-package-a6851fb/README.md).
It now includes the CPU caps, an in-game About screen and `--data-dir PATH` for
isolated saves/settings. The About screen identifies the actual packaged source
and explains current scope, unfinished work, controls, credits and local feedback.
The [local store-description draft](shardbound-store-draft.md) remains unpublished.
These use existing game screens and framework file configuration; no new
framework API or schema was needed.

Eleven focused integration tests pass on this source. Native title checks cover
216 configurations, 15 About pages and 372 inputs; their pre-commit source hashes
match the candidate. The extracted frozen app and LaunchServices smoke pass,
including exact build identity, About return, saves, settings and installed audio.
Six packaged frames and three larger-text source About pages were inspected.
The fresh independent UI-only attempt encountered a locked Mac and observed no
game, so G09 gains no walkthrough or human-playtest credit. Test processes ended.
The full packaged campaigns and sustained candidate checks are not yet repeated
for this archive. **All G01–G19 gates remain incomplete.**

Later [paid investment checks](eador-authored-investment-comparison.md) reproduce
the small Sapper timing tradeoff on current source and through native controls:
51 inputs, seven exact reloads, and 12 versus 23 missing HP from the same earned
army after Smoke-now versus Guard-now. Both finish R4 without deaths at two mana.
Preparation is model-owned and the continuation uses automatic rounds; this is
neither a full native paid campaign nor optimal manual play. A real Sealed Vault
regression also fixed a harness detour that could explore away from its named
target. Investment audit CLIs honor the 25% CPU allowance and default to a bounded case.

[Three persistent paid army plans](eador-army-plans.md) complete first Standard
seed-7 Foundries→Throne model pilots while maintaining different recruitment and
retinue policies. Their differences matter: sustain takes 35 total shard turns
and four casualties, mobile takes 44/32, control takes 82/22 and loses all its
troops in the final battle. These outcomes establish execution, not three viable
or balanced manual builds. All 897 public commands resume from exact saved states;
capital recovery was not needed or tested. The next depth work must test deliberate
protection, movement and control decisions from these actual earned formations.
Fifteen combined audit/budget/journey tests pass on `64cfe7a`; all jobs ended.
This work changes only development tools, tests and evidence. The game/framework
bytes remain those in the preserved `a6851fb` archive.

[Older audit CPU limits](evidence/audit-pacing-8312c84/README.md) now cover nine
previously unrestricted standalone commands, including preparation and repeats.
The 62 focused integration checks and two small serial CLI probes pass; all
Saga2D jobs ended. These tools retain existing matrix choices and add small-case
filters to the economic comparisons. No cancelled stress work was restarted.

[Two historical earned order comparisons](evidence/army-decisions-474b41a/README.md) carry
actual casualties through immediate paid replenishment: protecting the Adept
avoids 65 gold/2 crystals, while withdrawing the Warden transfers the loss to
Militia, saving 35 gold at the cost of four living HP. These local examples do
not establish three complete manual plans, and G04 remains incomplete.

Source **0b4e163** adds [explicit casualty forecasts](evidence/casualty-forecasts-0b4e163/README.md)
and a retaliation explanation in the Field Guide. Twenty-nine focused tests,
30 native reading layouts and 170 inputs pass. Both earned decisions now replay
through native controls to the exact paid aftermath; the additional lethal Pin
also matches its forecast after reload. Screenshots were inspected. This UI
change is newer than the preserved Mac archive above. A fresh independent
walkthrough timed out before any UI observation; G09 still has no credit from
that attempt. All release gates remain incomplete.

The CPU follow-up in **c759e6c / b621acf** adds a 30 FPS helper to seven older
native verifiers and forwards the 25% allowance through Extraction, Causeway and
Hero equipment preparation. It also closes native windows left open by Guard
and Hero checks. [Bounded measurements and verification](evidence/development-cpu-b621acf.json)
record 76 passing integration tests, exact paced/unpaced campaign outcomes,
three passing standalone checks, and inspected native frames. A 110-frame battle
settling loop takes 3.91 seconds at 28.12 FPS and 22.63% of one core, preserving
State and closing its window. The Causeway CLI averages about 27% including
startup. These are development-tool changes; the game and framework are unchanged.
All jobs ran serially and ended; cancelled long campaigns and the soak remain stopped.

## Earlier playable checkpoint — 2026-09-06

**Later source changes:** [frame pacing and test CPU budgets](evidence/frame-pacing-069f79c/README.md)
address the user's CPU/battery report. Normal play now sleeps between frames
(60 FPS cap, 15 inactive); native policy checks cap at 30 FPS and model fuzzers
default to a cooperative 25% of one core. Heavy jobs run serially. Native map,
battle/input, independent example and display checks pass. The `219bcf9` two-hour
soak was deliberately cancelled at 583 seconds; its cleanup is verified and it
does not count as completed sustained testing. The large stress job also ended
early with exit 143. The archive below predates the CPU changes.

[Earned discipline journeys](eador-content-acceptance.md) now cover all eight
preferred paths through rank 2, rank 3, departures and actual recovery: sixteen
model runs and eight native recovered campaigns, with 3,874 inputs and 102 exact
reloads. Those reports name their own source `03a0493`. Native/model retinue orders
differ, so no whole-state equality between those policies is claimed. Paired
manual hero builds and three distinct complete paid armies remain G03/G04 gaps.

The preserved Mac development build is clean source **219bcf9**, with twelve
authored encounter patterns and ordered battle playback. It includes three
linked shards, three difficulties, ten recruitable roles, twelve relics,
paid troop replacement, Tower infusion, complete tactical forecasts/history,
measured campaign/battle HUDs and 100/125 reading settings.
[Archive, source identity and verification](evidence/shardbound-package-219bcf9/README.md)
identify the exact playable checkpoint. **All G01–G19 gates remain incomplete.**

The combined source suite passes **1,207 tests**. The extracted frozen app
completes direct and lost-capital recovery campaigns across nine processes:
**984 native inputs, 17 UI save/reloads and seven exact process joins**. Both
routes reload their completed ending and return to title at 125% reading size.
The policies use automatic rounds and visible Finish playback, so they verify
campaign/save behavior without claiming manual tactics or human playtime.
Installed assets/audio, LaunchServices and the local ad-hoc signature pass.
Six actual package screenshots were inspected; independent package review found
no issue with the archive, source mappings, import closure or journey receipts.

[Runebound Causeway](eador-causeway.md) brings authored pattern coverage to
**12/12**. Its seven paid native plans pass 1,645 inputs and 93 exact reloads,
including Tower infusion, a deadline loss and finite wounded manual retry.
An unchanged ordinary site retains the same reward. Independent review compares
3,000 complete worlds and reproduces 806 exact command/save reloads. Its named
source passes 300 random campaigns, 10,009 random scene inputs, Tribes fuzz and
the complete briefing matrix. Counts alone do not close G05 or prove enjoyment.

[Ordered battle playback](eador-battle-feedback.md) shows movement, abilities
and reactions in sequence. Space/Finish skips it; reduced motion keeps pieces
still. Rules resolve once, saves record that completed turn, and modal input
cannot issue another battle order. Three clean-source native journeys retain
393 inputs, seven reloads and 637 watched frames. Independent lifecycle review
passes 25 tests. Its named 300-campaign/20-scene stress run checks 47,716 trace
events and 10,004 random inputs. The [combined Causeway journeys](eador-causeway-feedback-integration.md)
add 610 native inputs and 34 reloads; both final saves are byte-exact with the
pre-playback runs. These reports keep their own source revisions.

The combined checkpoint also passes 12 linked model campaigns, 12 scene runs,
3,004 random inputs and 327 inputs verified inert during playback, plus Tribes'
60 AI games and 20 random-input runs. The [90-second native playback probe](evidence/shardbound-playback-soak-449e40e/README.md)
verifies the adapted paced driver on an earlier source. It is not the two-hour
candidate soak or evidence of no memory growth.

Causeway, its shared duplicate-source/reward handling, battle traces and playback
stay in Shardbound. Saga2D's existing scenes, layers, input ownership and measured
UI primitives suffice. The [Scene.measure example](framework-ui-measurement.md)
remains independent of this game; this increment adds no framework API or schema.

The [resource attribution study](eador-resource-breakpoints.md) still identifies
later policies that stop buying while income continues. Causeway demonstrates a
local crystals-versus-time choice without establishing recurring economic depth.
Human/listening feedback, clean-account and Windows execution, remaining balance,
complete display/content acceptance and sustained candidate stress remain open.
The UI-only blind opening attempt observed no game: CUA reported a locked Mac
on both attempts. It supplies no walkthrough or human-playtest credit.

Earlier [c8ec2e2](evidence/shardbound-package-c8ec2e2/README.md) and
[56f1ffb](evidence/shardbound-package-56f1ffb/README.md) archives remain preserved.

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

## Ten authored families and complete campaign reading — 2026-09-06

Aerie Raid is integrated, using existing flight, Brace, Swap and Repulse on a
marsh-divided battlefield. Two free deployment approaches and a cheaper Scout
army have paid public-command and native-input victories. The finite failed
sortie/retry retains wounds and pays its reward once. Aerie brings the current
authored family count to ten; G05's twelve-family floor is still open.

The title and campaign transitions now use the shared 100/125 reading setting.
Selected new-run settings, retinue IDs and visible keyboard focus survive
settings changes and resize. Valid unusually long save paths no longer turn a
failed title or departure load into a layout crash: complete diagnostics page
without losing characters. Independent review reproduced the transition bug
before the fix. The shard's exhausted-action hint also fits its actual native
sidebar. [Integrated verification](evidence/shardbound-integrated-56f1ffb/README.md)
records 1,142 passing tests, both bounded fuzz checks and the native retries.

G01–G19 remain incomplete. Tactical/HUD reading, the remaining two authored
families, meaningful economy and pacing, oversized errors in remaining review
screens, candidate stress, platform verification and human feedback remain active.
The fresh Mac development package at `56f1ffb` passes isolated extracted and
LaunchServices smoke checks. Earlier artifacts retain their original attribution.

## Directed Control completion and bounded verification — 2026-09-06

The Control continuation now reaches the three-shard ending through 556 explicit
saved commands. Its historical opening used autoplay; the directed journal
starts at first-shard turn 6. Fifteen subsequent battles include two retained
troop deaths and actual paid replacements, buildings, mana and recovery. The
Foundries and Throne finish at turns 4 and 3. This supplies one complete directed
continuation, not matched evidence for every army plan or optimal balance.

At `75c2b60`, the framework cleanup change passes 280 integration tests and an
independent two-session native shutdown example. All 556 original commands
replay exactly through the changed framework. The native run then verifies 556
command/save/reload joins through 2,403 inputs in 193.74 seconds, averaging
25.24% of one CPU core. The [retained original journal, replay and screenshots](evidence/directed-control-complete-718afc9/README.md)
separate the historical opening, deterministic replay and actual native input.

Screenshot review exposed a missing reminder of the shard's contract requirement.
At `325c5c5`, the map displays the complete existing objective and ending records
use singular casualty copy correctly. [Focused tests and native saved cases](evidence/contract-objective-325c5c5/README.md)
cover five contracts in tests and three native presentation cases at larger text.
The earlier full journey remains attributed to its original source.

Game play remains capped at 60 FPS active / 15 inactive, native test input at
30 FPS, and long development tools target 25% of one core. Expensive owned jobs
run serially and have exited. Cancelled large matrices and soak were not restarted.
G01–G19 remain incomplete; matched build comparisons, content depth, current
candidate stress, platform checks and independent human feedback remain work.

## Two earned Scout paths — 2026-09-06

[Pathfinder II and Skirmisher II](eador-scout-paths.md) now have six-battle
agent-directed continuations from the same earned first skill choice. Both
follow the declared paid itinerary, spend 100 gold on two Rangers, finish at
turn 4 with no casualties or extra rest, and retain 192 gold / 18 crystals.
Pathfinder uses a Heal and ends with 13 missing army HP; Skirmisher uses no
spell and ends with 17 missing army HP plus four missing hero HP. Different
tactics mean these wound differences are not evidence of a dominant skill.

The shared journey demonstrates terrain reach versus attack-then-move, contested
Watch occupation and explicit Explorer evacuation through Swap. Both escape with
three surviving defenders withdrawing. The historical opening used autoplay;
the continuation contains no autoplay, resource injection or rewind. These are
partial campaigns and do not replace independent first runs or human feedback.

At native verifier `49d5b65`, all 225 commands match their exact saved results
through 225 F5/F9 joins and 918 input events. Screenshots of encounter entry,
ready evacuation and actual final wounds were inspected. Source hashes remain
unchanged. The two sequential native runs average 25.38% and 25.30% of one core
and close their games. [Retained journals and verification](evidence/scout-paths-78cb545/README.md)
distinguish the original execution sources from the native verifier source.
Twenty-four focused validator tests pass; G01–G19 remain incomplete.


## Visuals and sound first — 2026-09-07

The [presentation pass](eador-presentation.md) adds an original painted backdrop,
48 offline terrain illustrations, shaded castles and miniatures, and brief
command-driven projectiles, impacts and ability effects. Battlefield textures
are quieter than province illustrations. Native review found and fixed ground
rings crossing HP, repeated damage/Heal numbers overprinting, oversized labels
merging with neighboring health, and contact sparks crossing damage numbers.
Both health and damage now stay above effects, with compact labels inside their
own hex. Normal orders and saves remain immediate; enemy playback remains read-only.

Fourteen richer original cues and two revoiced music loops ship as prebuilt WAVs.
The asset build stays near its 25% CPU allowance. Native silent playback of the
complete catalogue, both full loops, live volume/mute and cleanup passes; audible
artistic review is still open. Existing Saga2D images, layers, audio and synthesis
primitives support the pass without a new framework interface.

[Retained screenshots and receipts](evidence/presentation-pass/README.md) include
nine final static frames, six native effect cases with 91 inputs and six exact
reloads, focused integration tests, and both bounded fuzz checks. The existing
60/15 FPS game caps remain. All owned expensive jobs ran serially and exited.
The adventure-route branch remains separate; visuals and sound keep priority
before additional mechanics. G01–G19 remain incomplete.

## Icon controls — 2026-09-07

Recurring toolbar labels, resource words and combat stat labels now use
original icons with numeric values, hover explanations and retained keyboard
keycaps. Primary orders and consequences remain in text. Saga2D gains reusable
layout images, optional button icons and reactive tooltips; the game owns the
artwork and meanings. Disabled spell keys now match disabled clicks, and larger
tooltip text survives screen changes.

[Icon evidence](evidence/icon-controls/README.md) retains ten inspected native
game frames, 104 recorded input/hover events, two exact reloads and 94 state
checks, plus the independent framework example, focused tests and bounded
Shardbound/Tribes fuzz checks. Native verification took 19.14 seconds wall and
4.81 seconds CPU under the existing 25% allowance and 30 FPS verifier cap.
The assets are prebuilt; game frame caps remain 60 FPS active / 15 FPS inactive.
This completes the requested icon pass without claiming a new release gate.
Visuals and sound remain the priority. G01–G19 remain incomplete.

## Character presentation and contact feedback — 2026-09-07

**de91293**, integrated with current main in **38f770e**, adds four original
painted hero portraits, clearer role equipment/materials for fourteen troop
miniatures and four heroes, and Hero level/health/mana icons. Manual attacks now
play each actual contact, including Brace and retaliation; ranged magical
weapons share an arcane visual and sound. Phase transitions clear old damage
numbers. The game uses existing framework primitives without new rules or APIs.

[Final character evidence](evidence/character-presentation/README.md) retains
18 inspected native frames, 59 input activations, two exact reloads, all eight
earned relics at 125% and unchanged runtime hashes. The final run took 22.01
seconds wall and 5.50 seconds CPU. Forty-five focused integrated tests pass,
including exact portrait packaging and co-op socket orders. Bounded Shardbound
and Tribes checks pass at the default CPU allowance. No packaged release or
large acceptance matrix was repeated; audible artistic review remains open.
**G01–G19 remain incomplete.**

## Compact tactical controls and seal feedback — 2026-09-07

Battle Auto-play, Retreat and Log now use icons, keycaps and full hover
explanations. A tighter header and fixed footer give miniatures more room;
selection, log messages and orders leave the board fixed under the pointer.
The latest event stays visible, while L opens the full log and M opens long
messages. Objectives and primary orders keep readable text.

Two original cues and ground rings announce nonterminal seal progress gain/loss.
Unchanged progress stays quiet; final results retain their existing cues. All
sixteen prior WAVs are unchanged. Existing framework primitives support this
pass without new rules, save fields or APIs.

[Retained tactical evidence](evidence/tactical-presentation/README.md) includes
eight inspected native frames at both reading sizes and three window sizes,
104 input events and three exact reload pairs. The final run takes 57.83 seconds
wall and 14.35 seconds CPU. A 38-test focused selection passes after rerunning
one journey invalidated by a concurrent verifier edit; that failure is retained.
Bounded Shardbound fuzzing passes, including actual error-reader input. The game
frame caps remain 60/15 FPS, and expensive verification runs serially at the
default 25% allowance. Human listening/playtest feedback and all release gates
remain open. **G01–G19 remain incomplete.**

## Varied adventure locations and informed routes — 2026-09-07

New worlds now vary complete authored site packages within progression bands.
Saved worlds keep their recorded maps. Selecting a province reveals its site
before conquest; Sites and Relics in the Codex show actual source provinces and
mark cleared sources. Existing Saga2D primitives support this game-specific
generation and presentation change without a new framework API.

[Retained evidence](evidence/adventure-variety/README.md) compares 300 worlds
with the exact historical baseline, including 600 exact reloads, unchanged
non-site facts and complete reward/guard packages. Five native discovery cases
retain 186 inputs, five exact reload pairs and eight inspected frames. Focused
earned-army regressions now reach the actual site and retain changed travel,
experience, wounds, losses and paid retries. Large campaign matrices remain
deferred.

Two plans declared before their first battle complete fresh paid expeditions:
the Seal/guided Courier route finishes five battles on turn 3 with one action,
112 gold/10 crystals and 11 wounds; the Boots/northern Explorer route finishes
six battles on turn 3 with no actions, 121 gold/14 crystals and 15 wounds. Both
keep all six troops and use Warden Swap to evacuate in round 2. Neither uses
autoplay, a rewind or elective recovery. Each retains one rejected move with
unchanged state. These local routes demonstrate different actual access costs
and equipment choices, not general balance or whole-campaign strategies.

Both accepted journals reproduce through native New Campaign input at 125%
text size: 219 exact commands and reload pairs, 903 inputs and 18 inspected
screenshots. All 82 authenticated source files remain unchanged. The sequential
native runs take 44.90/45.28 seconds wall and 11.50/11.58 seconds CPU; games close
and verifier pacing remains 30 FPS with a cooperative 25% CPU allowance.
Twenty-three companion input checks and bounded linked model/scene fuzzing
also pass. This advances G02/G05 evidence without completing a gate. Human
listening/playtests, packaged-platform validation and release acceptance remain
open. **G01–G19 remain incomplete.**

## More icon controls and a gameplay movie — 2026-09-07

**660ce5e** replaces ten more recurring map and battle labels with icons:
Explore, Build, Recruit, End turn, Campaign, Rival, Guard, Bolt, Heal and End
round. Hover explanations and keycaps preserve their meaning; spell costs stay
visible. Changing travel verbs and consequential choices retain text. The army
strip uses the same level and health metrics. This uses existing primitives and
adds no framework interface or game rule.

[More-icon evidence](evidence/more-icon-controls/README.md) retains native
100%/125% frames, 199 inputs, 170 state checks, 87 tooltips and three exact
reloads. Twenty-two focused tests and the bounded two-scene fuzz run pass.

[The gameplay movie](evidence/gameplay-movie/README.md), committed in
**42aaceb**, makes the current presentation reviewable in motion: 38.90 seconds,
1,167 native frames, 33 inputs and 16 exact manual commands through an earned
Moonstone. Enemy movement, attack and retaliation finish naturally. Audio is
reconstructed from actual emitted events, shipping WAVs and effective gains;
it is not hardware-recorded sound. Four capture tests and separate video/audio
readback pass. Native capture and encoding ran sequentially with a 25% CPU
allowance; the game retains its 60/15 FPS caps. The movie uses a fixed simulation
clock and is not a performance measurement. Human listening remains open.

## Save phases across a process restart — 2026-09-07

**da98241** adds [fresh-process evidence](evidence/phase-restarts/README.md)
for campaign, battle, skill, relic, result, departure, recovery, completed
campaign and capital loss. Nine writer Games close before one separate Python
process loads each phase through title save controls, checks full state and
scene restoration, and performs its next real input. Manual primary files stay
unchanged. Two starts are current title journeys; later phases come from
authenticated earned checkpoints with their original provenance retained.

The mock integration passes, and native verification records 76 inputs in
81.77 seconds wall / 20.54 seconds combined CPU. This advances G12 at source
level. It does not add packaged-launch or backup-recovery coverage. The frozen
**7b5562d** candidate remains the last packaged checkpoint; Windows execution,
human playtests, listening and overall release acceptance remain open.

## An independent multiplayer consumer — 2026-09-07

The [counter-room tutorial](framework-match-menu.md) demonstrates MatchMenu,
MatchLobby and OnlineClient without importing a reference game or production
server catalog. Its local authority only increments the authenticated seat's
counter. The example explains the factory interfaces, JSON commands, scene
ownership, covered-scene polling and cleanup without adding a framework API.

The focused socket integration passes in 0.29 seconds. Native input verifies
room creation, lobby handoff, both counters, a peer order under Help, return
and shutdown. Inspected screenshots caught background text peeking around Help;
the final example uses an opaque Help scene. The final native run uses 29 paced
frames and closes both clients, its Game and local server.
This advances the independent-consumer portion of G17; internet deployment and
overall release acceptance are unchanged.

## Presentation checkpoint and wrap — 2026-09-07

Manual final blows now show their contacts before the result screen
(**3488d50**, inspected frames in **5ae95d1**). Modal statistics, prices and
utilities reuse icon/value controls (**c1a3df2**). Shared attack and hit motion
adds a directional lunge, recoil and return, including retaliation and brief
defeated-figure feedback; reduced motion leaves figures still.

The [latest native preview](evidence/attack-motion/README.md) contains four cases,
505 frames and four exact UI save/load checks. The related focused suite passed
53 tests before the final casualty regression; all seven motion tests then
passed on the final source. Native screenshots were inspected. No full-suite or
package rebuild was performed for this checkpoint.

Work stopped at the user's request to conserve credits. The
[presentation handoff](presentation-handoff.md) records the boundary for a later
session. The frozen **7b5562d** package predates these changes; human listening,
playtests, Windows execution and all overall Early Access gates remain open.

## Resumed contact feedback — 2026-09-07

The user authorized continued improvements after checkpoint `c507745`.
**1e15c1e** fixes lost impact sounds when Help or Saves covers a manual shot;
20 manual-audio tests pass, including real cover/return and cover/load inputs.

The [contact-feedback evidence](evidence/contact-feedback/README.md) adds
correctly timed damage notices above the figures' faces, readable durations
across playback events/completion, and recipient-aware cleanup after movement.
Focused regressions and native 100%/125% movies pass; each native run records
four exact reloads and verifies a paused arrow resumes with one impact sound.
No rules or framework API changed. The packaged checkpoint, human assessment
and overall release gates remain unchanged.

## Concurrent campaign foundation — 2026-09-07

The user clarified that simultaneous activity belongs on the global map;
battles keep ordinary alternating turns. The
[campaign PvP scope](simultaneous-campaign-pvp.md) defines independent realms,
concurrent PvE, encounter claims and a shared Ready barrier.

The first extraction separates realm upkeep/recovery from world advancement.
Existing solo end-turn order and saves are preserved. Thirty-eight economy,
pressure and recovery checks pass, including deterministic desertion and
encirclement. A bounded linked fuzz run passes four model campaigns and two
scene journeys with 517 model and 366 scene state checks, at a 25% CPU allowance;
all four campaign runs end in defeat, so this is invariant evidence rather than
victory coverage. [Retained receipt](evidence/realm-settlement/linked-fuzz.json.gz).
Independent source review found no blockers. This is a prerequisite, not a
playable independent-realm PvP mode; the acceptance criteria remain open.

## Inspected statistics stay together — 2026-09-07

Enemy inspection now uses icon/value pairs for attack, defense and range,
fixing the detached Range value visible at 125% reading size. The three
icon-control tests pass. [Native evidence](evidence/inspected-stats/README.md)
retains both inspected text sizes, hover/layout assertions and two exact
UI reloads. No battle rules, framework interface or packaged build changed.

## Trusted room checkpoints — 2026-09-07

Room storage now uses an explicit full-state serializer in the server game
catalog, separate from each player's network view. Existing JSON formats are
unchanged. A filtered-view regression first reproduced loss of a paid campaign
and active battle; the checkpoint implementation preserves both.

Twenty-seven server/checkpoint tests pass in 3.66 seconds, including real
WebSocket processes for all three games, private-seat recovery, expiry and
restart. Shardbound's restart journey now kills the server after a real battle
order, rejoins both private seats and continues with an exact next battle order.
No public deployment occurred. Player-view filtering and independent-realm
campaign PvP remain unimplemented.

## Army results independent of world rewards — 2026-09-07

`apply_army_result` now applies a completed PvE battle's wounds, casualties,
advancement and defeat recovery to its hero without changing the battle or
world. Ordinary result acceptance retains claims, rewards and choices.
[Verification](evidence/army-results/README.md) includes 94 passing checks,
earned victory and defeat, exact saved continuation, a linked-shard advancement
cap and bounded linked fuzzing. The same fuzz campaign/scene metrics match
before and after extraction. This keeps the global campaign PvP work game-local;
separate realms, claims and Ready coordination still need implementation.
