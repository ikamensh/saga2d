# Realm difficulty: first measured candidate

Three game-owned policies are implemented in schema v12. Standard retains the
original realm rules. This report covers the first Accessible/Challenge values
in [the proposal](eador-difficulty-proposal.md), **not tuned-mode acceptance**.
Challenge's measured recovery tail prompted the separate
[mana-four comparison](eador-difficulty-candidate.md). New Challenge games now
select `challenge-2`; the original `challenge-1` remains meaningful and the
historical results below have not been rewritten.

## Public rules and protected progress

`State.new(..., difficulty='standard')` and `State.new_campaign` select a profile
from `eador.difficulty.DIFFICULTIES`. `state.difficulty` names the mode;
`state.rules_id` identifies its immutable saved record, and `state.rules` supplies
the title, description and realm parameters. Loading v11 or earlier assigns
`standard-1` without resetting its treasury, rival, provinces or active battle.
Unknown saved IDs/future versions fail through `SaveFormatError`.

`recovery_preview()` reports capped hero HP/mana gains, an up-to HP amount per
surviving troop, and a blockade reason. It and end-turn share deterministic
desertion selection, so an unpaid Acolyte contributes no healing bonus. Recovery
is calculated against the current bill before income/payment, not the following
turn's treasury. This distinction has a public saved-state regression.
`expedition_funding(recovery=False)` returns the actual arrival gold/crystals;
advance/recover and presentation use the same query. `replay()` returns a fresh
run using the original seed, mode and exact rules ID without changing this state.

The rival's starting treasury, roster, paid refits, surviving identities and
ordinary two-turn hostile warnings are unchanged. Profiles alter its opening
schedule and first paid replacement window. Realm gold rounding happens once,
after encirclement removes blocked production. Crystal income, prices, combat
stats, sight and authored deadlines are unchanged. Saga2D gains no difficulty or
strategy-game abstraction. Frozen IDs protect these parameters; they do not
promise historical compatibility for every future combat/content change.

## Matched first-candidate audit

Source game files are the combined `31de99b` checkpoint, including Observatory.
The report retains exact source hashes and all 32,400 rows with purchases: seeds
0–99 × four classes × three themes × direct/north/south routes × three paid
plans × three modes. No measured source changed during the 522-second run.

Plans keep the former explicit purchase order: Economy buys Market, Barracks,
Sword, Temple; Sustain buys Temple, Acolyte, Barracks, Sword; Spells buys Tower,
Barracks, Sword, Temple. They refill Swordsmen, retain one Acolyte for Sustain,
take first/free approaches, use actual optional automatic combat, and intercept
visible threats. Final recovery requires no more than six missing HP and mana
within four of maximum. A 60-turn/40-assault-loop bound records unfinished games.
Seed zero's full combinations repeat exactly. This is a disclosed policy audit,
not a player study or claim of optimal play.

Each row below contains 3,600 runs. Means include unfinished runs.

| Mode / plan | Wins | Mean turns | p90 turns | Troops lost | Final recovery turns | Crystals spent / left |
|---|---:|---:|---:|---:|---:|---:|
| Accessible / Economy | 3,600 | 11.46 | 14 | 2.46 | 0.75 | 0 / 36.21 |
| Accessible / Sustain | 3,600 | 12.21 | 15 | 3.04 | 1.32 | 0 / 38.15 |
| Accessible / Spells | 3,600 | 12.11 | 14 | 2.49 | 1.26 | 2 / 35.86 |
| Standard / Economy | 3,600 | 13.25 | 16 | 2.72 | 1.98 | 0 / 40.02 |
| Standard / Sustain | 3,600 | 15.23 | 21 | 3.55 | 3.71 | 0 / 45.12 |
| Standard / Spells | 3,600 | 14.59 | 18 | 2.77 | 3.21 | 2 / 41.72 |
| Challenge-1 / Economy | 3,600 | 16.25 | 21 | 2.88 | 4.90 | 0 / 49.09 |
| Challenge-1 / Sustain | 3,486 | 22.04 | 35 | 3.43 | 9.45 | 0 / 64.96 |
| Challenge-1 / Spells | 3,600 | 17.42 | 22 | 3.18 | 6.54 | 2 / 50.86 |

Accessible improves average attrition and recovery friction. Challenge adds a
large mana-recovery tail: 114 Sustain runs remain playing at the policy bound,
mostly Wizard/Frontier. None of the bounded audit's campaigns ended in defeat;
individual battles can be lost and recovered. No trial deserted troops. Lower
starting crystals do not fix recurring surplus; these plans buy no crystal-priced
specialists and deliberately choose free approaches. Paid specialist/approach
comparisons remain necessary, and further explicit economy sinks may be needed.

In the seed-zero Warrior/Frontier/south Sustain tail, the policy stopped at turn
51 with one troop loss, no battle defeats, a healthy five-troop army, 16/18 mana,
2,511 gold and 186 crystals. Directly assaulting through public commands then won
on the same turn with three survivors. This proves that particular bound is not
an unwinnable map, but does not excuse the policy's 30 recovery turns.

## Counterplay and integration evidence

- **947 full tests passed** at the combined first checkpoint. Generation covers
  100 seeds/theme/mode, connected objectives and valid sources; **14,400 actual
  opening battles** cover every class and adjacent direction after an affordable
  Barracks/Swordsman purchase.
- Six genuine v11 fixtures preserve exact gameplay continuation across a new
  game, battle, reward, rival order, departure and recovery. Earlier content
  fixtures, including the actual pre-Observatory Barrow, differ only in the new
  schema/ID metadata. Existing tactical assertions remain intact.
- Later focused coverage passes **116 campaign/pressure/rival tests**, including
  48 class/middle/finale paths and 24 recovery paths across modes. Standard's
  existing seed-17 policy is unchanged. New modes can secure the central frontier
  before the distant Rootward Watch. Without that preparation, the original
  Accessible seed-17 policy loses three classes' capitals while walking toward
  a vacated rival position; Scout catches the expedition. Those losses are not
  removed from the observed limitations.
- Challenge's military-only fortified camp reaches encirclement with three gold
  and cannot pay after withdrawing from an injury encounter. Buying its requested
  Market before filling the last slots leaves 46 gold, pays the wounded army, and
  breaks out with six survivors. Tests retain exact blocked-HP equality, supply
  restoration, paid replacement identities and eventual neglect defeat.

Native selection/readout verification belongs to root's UI checkpoint. This
model evidence does not relabel mock commands as native input or complete
G02/G07. The [follow-up comparison](eador-difficulty-candidate.md) isolates
mana-four `challenge-2`, with exact Challenge-1 save-continuation fixtures before
the subsequent new-game selection change.

Reproduce the original audit with the recorded source revision:

```sh
uv run python tools/audit_eador_difficulty.py --seeds 100 --report /tmp/difficulty.json
```

[Summary/source hashes](evidence/difficulty-matched-plans.json) and
[all detailed rows, compressed JSON](evidence/difficulty-matched-plans.rows.json.gz).
