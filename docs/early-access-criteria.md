# Shardbound Early Access acceptance criteria

Status: **not release-ready**. Baseline: commit `2d26787`, 2026-09-05.
The existing single-shard game proves the framework/game seam. This document
sets the bar before further implementation; passing the old slice's tests
does not meet this bar. Each gate needs evidence from the release candidate,
not a plan, feature count, historical test run, or a promise of future work.

## Product promise

A compact, replayable fantasy strategy game in which developing a realm,
choosing a hero build, investigating dangerous sites, and commanding a
persistent army are all consequential. Players should enjoy the current
campaign and want a different run. The goal includes sustained strategic
depth and presentation quality, not only a stable technical demonstration.

Valve's [Early Access guidance](https://partner.steamgames.com/doc/store/earlyaccess)
requires a playable product with value in its current state and accurate
expectations about unfinished work. Our gates below are project quality
criteria, not claims about Valve's numerical requirements. Preparing a
release candidate is authorized; publishing, purchases and external messages
remain separate actions requiring the user's authorization.

## Acceptance gates

| ID | Required result | Evidence required to pass | Baseline |
|---|---|---|---|
| G01 | A complete campaign with a beginning, escalation, climax and ending, plus a quick standalone shard mode. At least three linked shards with meaningful carryover and a choice of the next challenge. | Play the entire campaign through real input, save/restart between shards, reach both completion and recovery/loss paths. Record duration and decisions; repetitive padding does not count. | One short shard only. |
| G02 | Replayable worlds that change decisions: at least three terrain/encounter themes, different routes and stronghold approaches, seed and difficulty selection. | Review generated worlds across 100 seeds per theme; connected/reachable objectives, fair openings, at least three materially different successful routes. | Same 19 cells, capitals, route and guard bands each run. |
| G03 | Four heroes have distinct abilities and at least two viable advancement paths each, with meaningful player choices at multiple levels. | Build-specific manual and automated scenarios demonstrate different action/resource decisions. Earned choices persist through saves, defeat recovery and shard transitions. | Passive fixed stat growth. |
| G04 | Recruitment, spells and equipment support counterplay. Initial content floor: 10 recruitable troop roles, 8 usable spells/active abilities, 12 discoverable equipment/relic items; at least three complete viable army/build plans. | Every content entry is reachable, explained, rendered, saved and exercised in a relevant scenario; role distinctions cannot be palette swaps or small stat changes alone. Balance evidence identifies costs, counters and tradeoffs. | Four recruits, two spells, no equipment. |
| G05 | Sites are adventures with choices, differentiated enemies/rewards and consequences. Initial floor: 12 authored encounter patterns across three themes and three tactical objectives. | Complete every pattern at least once; decisions have visible consequences and alternatives; seeds produce varied encounter sequences. | Site names differ, battles/rewards largely identical. |
| G06 | The rival follows observable, consequential strategy and can be countered. Its attacks use finite forces/resources; targets, army strength and warnings are comprehensible. | Simulate and manually play defense, interception, counterattack and rival defeat. No infinite safe XP/income farm, inexplicable territory flip, or weaker defense caused by conquest. | Scheduled frontier flips and regenerating attacks. |
| G07 | Realm development has meaningful tradeoffs and resource sinks. Economic, military and magical investment can each contribute to victory. | Compare at least three strategies across 100 seeded runs and difficulties. Test upkeep pressure, recovery, scarcity and bankruptcy; no universally dominant opening or permanently useless currency. | Temple/swordsmen route dominates; crystals have only one small expense. |
| G08 | Manual tactics offer advantages through positioning, terrain, abilities and objectives. Exact previews explain immediate consequences. | Public-command tests and real-input encounters for movement, occupancy, range/line of sight, retaliation, statuses, guard/wait, spells, objective wins/losses, retreat and AI responses. Manual play can improve on auto-play; auto-play remains optional. | Basic movement, damage, cover, retaliation and two spells. |
| G09 | First-time players can learn inside the game without reading repository docs. Contextual guidance, objectives, disabled-action reasons and an inspectable codex exist. | Three independent first-run walkthroughs without code knowledge; additionally three human playtests before a release-readiness claim. Record confusion and fixes, not only successful scripted paths. | Static field guide only. |
| G10 | Every screen works with mouse and a complete keyboard path. Supported display sizes, HiDPI, text scaling, volume/mute and reduced animation settings are usable and persist. | Real-input and screenshot matrix at 1280×720, 1280×800, 1920×1080 and HiDPI; keyboard-only campaign section; settings restart test. No clipped text, hidden controls or color-only critical information. | Fixed 1280×800 layout; incomplete keyboard paths; no settings. |
| G11 | Presentation consistently communicates actions and consequences: identifiable units, terrain, animation, readable effects, distinct sound cues, music/ambience and clear results. | Inspect screenshots and recorded gameplay from every major state and content family, review audio at player volume, exercise mute/reduced motion. Original or licensed assets with provenance. | Simple procedural art; no Shardbound audio or action animation. |
| G12 | Progress is protected: separate manual slots and rolling autosaves, save browser with useful metadata, quicksave/load, save before risky transitions and after resolved progress, accurate recovery from invalid files. | Restart from all campaign/battle/choice/result phases; retained manual saves survive autosave/new-game; truncated/invalid/newer-version file leaves current session intact and shows a useful message; write failures preserve previous saves. | One overwrite-only slot; malformed payload can crash UI. |
| G13 | Game save schema is versioned and content-aware, validates invariants, and has an explicit compatibility policy. | Fixture-based older/current/newer schema tests; same subsequent commands yield same results after reload; unsupported saves are refused without mutation. No arbitrary dictionary failures leaking into player flow. | Unversioned dataclass JSON. |
| G14 | Standalone release artifacts launch outside the repository without Python, uv or a terminal. Windows x64 is the primary Steam target; other targets are advertised only after verification. | Build reproducibly, install/run from a clean directory/account on each claimed target, test assets/fonts/audio/saves, quit/relaunch, and record OS/build/hash. Verify clean Windows runtime before claiming Windows readiness. | Source checkout launch only; package excludes game. |
| G15 | Stable and responsive during sustained play. | Zero crash/data-loss/soft-lock defects in a full campaign test matrix, at least 1,000 generated campaign/battle runs, 100,000 input steps, and a two-hour real-backend soak. Record p50/p95 frame times and memory growth on named hardware; target p95 <33ms in normal play and no unexplained sustained growth. | 314 tests and short soaks; no long-run/performance report. |
| G16 | Tests protect behavior without pinning implementation or one lucky strategy. | CI/reproducible local checks cover all public game journeys, rules and failure paths; replayable failing seeds; tests trace to these gates. Existing Tribes/framework regressions remain green. | Good slice-level tests; narrow content/strategy coverage. |
| G17 | Saga2D stays easy to learn and accumulates useful deep primitives. No game rules, content IDs or game imports enter the framework. | Each addition has a demonstrated cumbersome caller problem, tiny documented interface, public integration tests and a runnable example independent of Shardbound. Review whether existing primitives suffice before adding one; cross-game regression checks. | HexGrid and measured paragraphs meet this intent. |
| G18 | Player-facing scope, controls, known issues, version, credits and support/feedback instructions match the actual candidate. A gameplay capture and local store-description draft describe only current capabilities. | Audit documentation and media against the packaged build; no placeholder claims, copied Eador branding/assets, or unverified platform/support promises. | Source docs only; not a release pack. |
| G19 | A final independent review finds no unresolved release blockers and the creator can assess the concrete candidate. | Requirement-by-requirement evidence audit plus independent game/architecture review. Human playtest feedback from G09 is resolved or explicitly assessed; user sees runnable artifacts and evidence before any publication request. | Not performed for an EA candidate. |

Content floors prevent a shallow build from being called complete, but do
not prove depth or fun. Counts alone never pass G03–G08. We can revise a
specific design when evidence favors a better one; record the rationale
and preserve the intended player value. Do not lower the release bar to
match what happens to be implemented.

## Framework/game split

Saga2D owns rendering, input/focus, reusable layout and widgets, camera,
audio mechanics, resource lifetimes, geometry and safe save-file I/O.
Shardbound owns campaign progression, province and rival rules, economy,
content, combat/status semantics, equipment, tutorial state, save schema
and when/how gameplay is autosaved. Prefer composition and ordinary Python
commands over a general strategy-engine abstraction.

## Work order

1. Protect progression and introduce genuine choices: versioned state,
   branching hero development, varied sites/loot, safe save browser and
   autosaves. Complete each path through the actual UI.
2. Replace the rival pressure timer with finite, telegraphed operations;
   add realm tradeoffs, counterplay and scenario variation.
3. Deepen tactics/content and link shards into a campaign; rebalance across
   different strategies, not only the original solver.
4. Complete onboarding, keyboard/display/settings, animation and audio.
5. Package, perform long-run/platform/human checks, capture the release
   candidate and audit every gate. Reliability work runs throughout.

Track current evidence, incomplete gates and next work in
`docs/early-access-progress.md`. This objective remains active until all
gates are satisfied; an increment being committed is not release readiness.
