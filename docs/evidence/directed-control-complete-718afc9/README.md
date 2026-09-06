# Completed directed Control continuation — 2026-09-06

The earned turn-6 Control opening now continues through **556 explicitly
selected commands, 15 battle victories and two troop casualties**, ending with
the three-shard campaign completed. There are no player autoplay commands in
this continuation. The earlier opening used autoplay; this is agent-directed
play with source inspection, legal-move queries and damage previews, followed by
deterministic model and native-input verification.

## Original decisions and derived verification

The fixed starting save is `commands[38]['before']` (zero-based index 38) in the
[historical Control journal](../shardbound-army-plans-cd351a9/control.json.gz).
That file's SHA-256 is
`6609eb4f334a956f6d6873e378b0b87bdd6901f3ad2f4688226265b8ede0b72a`;
its recorded source is `2d775de99dd1699d8f71e34e9cf63e4c4e57cda2`.

- [journal-original.json.gz](journal-original.json.gz) preserves the original
  decisions, rationales, forecasts, currency deltas, complete before/after saves
  and disclosed mistakes. Its recorded execution source is
  `664869096489f9de608329aca9c7863e4ede4ef9`, with per-file source hashes. Later
  evidence and tooling commits did not change the authenticated game bytes
  during play. The directory suffix `718afc9` identifies the retention point,
  not the source of every later check.
- [journal-current.json.gz](journal-current.json.gz) is a **derived replay** on
  `75c2b605341ece531682c916645dba4da6e75173`, after `Game.close()`. All 556
  commands, recorded forecasts, currency deltas and serialized states matched
  the original. The only changed files in the original authenticated manifest
  were `saga2d/game.py` and `saga2d/testing.py`. Its `replayed_from` record
  identifies the original bytes and verification implementation. This adds no
  decisions or new playthrough credit.
- [replay.log](replay.log), [replay.py](replay.py),
  [journal-validator.py](journal-validator.py) and [director.py](director.py)
  retain the verification and recording implementations, including original
  local paths. [summary.json](summary.json) is the original journal's accounting,
  computed by the retained [summary.jq](summary.jq).

The subsequent map-objective UI change is source **325c5c5**. The full replay
below belongs to **75c2b60**, not that later UI source; its separate UI evidence
does not extend this replay's attribution.

## Actual journey and costs

| Segment | Commands | Capital victory turn | Wins / casualties | Paid gold / crystals | Campaign rests |
|---|---:|---:|---:|---:|---:|
| Westwatch, starting at T6 | 1–185 | 9 | 3 / 1 | 150 / 11 | 3 |
| Foundries | 186–429 | 4 | 7 / 0 | 305 / 6 | 3 |
| Throne | 430–556 | 3 | 5 / 1 | 305 / 3 | 2 |

Each departure command is counted with the shard it leaves: 185 advances to
Foundries and 429 to Throne. The recorded capital turns sum to 16, including the
historical opening's elapsed turns; the continuation itself contains eight
campaign end turns. Its battles total 58 rounds and 44 actual enemy phases.

The **760 gold / 20 crystals** paid within this continuation comprise 360 gold /
7 crystals for recruitment and replacement, 400 gold / 4 crystals for buildings,
and 9 crystals for three infusions. The first two paid replacements also consume
two actions and permanently retire a rank-3 Militia and Archer. These retirements
are separate from the two battle casualties. Later shards carry the earned Adept
and Skyrider, leave the other survivors as garrisons, and pay to rebuild the
roster. Shard transitions reset expedition funds through normal rules, so these
expenses are not one uninterrupted treasury balance.

Westwatch uses Repulse, flight, shared-mana healing and two infusions to finish
at T9. A rank-3 Militia dies when the agent overlooks overlapping Guard attacks.
Foundries captures both required foundries, defeats the real rival expedition at
Frostmere and takes the capital at T4 with no casualties. Its paid infusion costs
one action and three crystals; its eleven Heals restore 200 HP.

Throne takes the southern plains route to High Pass, then assaults adjacent
Duskspire at T3 while the actual rival expedition is at Frostmere. Its capital
battle finishes in round 7. Sapper #13 dies at command 524 after an exposed
position allows two ten-damage Guard hits and a four-damage Wolf hit. That error
is retained without replacement or rewind. The rival still has five living
troops in the final save; capital victory marks its intent defeated. This is
not a victory over that expedition in combat.

Throne's treasury reconciles as 140 starting gold + 125 battle rewards + 101 net
rest income − 305 purchases = **61 gold**. It ends with **3 crystals and 6/26
mana**. Six Heals restore 105 HP, including 79 through the Acolyte. Final survivors
are Wizard 43/48 HP, Adept 18/36, Skyrider 16/36, Militia 28/28 and Acolyte 26/26.
The Wizard has Channeling 2, Restoration 1 and level-4 XP 40; Channeling 3 was
never offered. There was no retreat, tactical defeat or recovery expedition in
the continuation. Recorded mistakes and rejected orders remain in observations;
no branch simulations, rerolls or resource injections were used.

## Native continuation and session cleanup

The [native receipt](native/verification.json) on **75c2b60** records **2,403 input
events and 556 exact command/save/reload joins**, through the completed final
state. Each F5 reads the actual save; each F9 requires a new live State with exact
content. The replay begins by loading the authenticated historical save. It does
not perform the earlier opening through native controls.

The run took **193.74 seconds wall and 48.90 seconds CPU**, averaging **25.24% of
one core**, with the 25% cooperative budget and existing 30 FPS native pacing.
This is a process CPU measurement, not a strict operating-system quota or a
battery-life test. [native.log](native.log) records completion; captured frames
are retained under `native/`.

The focused framework and verifier checks pass **280 tests in 11.08 seconds**
([log](framework-tests.log)). The separate native `Game.close()` check opens and
closes two explicitly ticked sessions with six updates
([log](game-close-native.log)). These checks and the replay ran serially and
exited. They do not constitute a new full-suite run or a refreshed package.

[SHA256SUMS](SHA256SUMS) identifies the retained files. This evidence establishes
one completed paid continuation and exact replay of its decisions. It does not
establish a human playtest, a fully native opening, an optimal policy, comparative
army balance, the alternate Gate finale, recovery behavior or release readiness.
**G01–G19 remain incomplete.**
