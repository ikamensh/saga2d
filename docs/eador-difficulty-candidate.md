# Challenge recovery candidate and policy comparison

The proposed new-game profile is **challenge-2**, with 4 mana recovered per turn.
It preserves Challenge-1's 90 gold / 2 crystal grant, 80% gold income, HP recovery,
finite rival funds and forces, announced operation delays, and linked funding.
**Following review, the new-game catalog selects challenge-2.** Existing saves
retain their recorded profile. The measurements below preceded that switch;
they do not declare difficulty or the economy complete.

The original [32,400-run report](eador-difficulty-model.md) remains unchanged.
All candidate experiments below used clean source **445b069**, with hashes checked
before and after each run. Candidate checkpoints were explicitly created from a
fresh Challenge start by changing only the known `rules_id` through the public
save loader. No ongoing player save or new-game catalog was changed. The candidate
has identical starting parameters, so this isolates mana recovery.

## Matched rules comparison

Each profile uses the same 100 seeds × 3 themes × 4 heroes × 3 routes × 3 purchased
plans: **10,800 campaigns**. The policy, first/free site approaches, automatic
tactics, six-HP recovery tolerance and within-four-of-maximum mana reserve are
unchanged. The 60-turn/40-assault-step bound also remains unchanged. Every final
state roundtrips exactly; all 108 seed-zero repeats are deterministic. The small
policy-hook extraction also reproduces all 108 original seed-zero Challenge
results, purchases, events and final-save hashes exactly.

| Plan | Mana 3 → 4 mean turns | Mean casualties | Recovery turns | Unfinished runs |
|---|---:|---:|---:|---:|
| Economy | 16.25 → 13.81 | 2.88 → 2.74 | 4.90 → 2.77 | 0 → 0 |
| Sustain | 22.04 → 16.31 | 3.43 → 3.30 | 9.45 → 4.73 | 114 → 2 |
| Spells | 17.42 → 15.57 | 3.18 → 3.04 | 6.54 → 4.41 | 0 → 0 |

The candidate wins **10,798/10,800**, with no campaign defeats. Its p90 turns are
18 / 22 / 19 respectively. This is not uniformly easier: 403 Economy, 401 Sustain
and 1,167 Spells cases take longer, because recovery changes encounter timing and
subsequent decisions. Purchase counts change in 1,398 / 1,868 / 1,899 matched
cases. Individual battle defeats change from 1 / 10 / 6 to 4 / 16 / 5. These are
explicit automatic-policy outcomes, not evidence of optimal play or enjoyment.

The remaining cases are Wizard / Frontier / direct / Sustain, seeds **2 and 78**.
Both stop playing at turn 48 with healthy armies, no battle defeats, nine rival
interceptions and 32 mana-recovery decisions. They keep replenishing a near-full
Wizard reserve between paid replacement expeditions. A live-position pursuit
policy alone does not remove these two loops. The turn limit is a development
policy bound, not a game deadline or proof that either map is unwinnable.

Exact rows and all hero/theme/route breakdowns:
[candidate report](evidence/difficulty-mana4-full.json),
[compressed rows](evidence/difficulty-mana4-full.rows.json.gz).

## Replaying the original 114 unfinished cases

All rows below replay the same case identities. “Reserve 8” spends less time
waiting for mana before the final advance; it keeps the six-HP recovery tolerance.
“Live pursuit” checks the visible expedition position after every turn instead of
walking to a position recorded before the detour. Neither adds waits or changes
game rules, purchases, rewards, automatic tactics or policy bounds.

| Profile and policy | Wins / unfinished | Mean turns | Casualties | Recovery turns | Battle defeats | Recruitment gold |
|---|---:|---:|---:|---:|---:|---:|
| Mana 3, original | 0 / 114 | 48.85 | 3.07 | 31.93 | 1 | 217.92 |
| Mana 3, reserve 8 | 114 / 0 | 14.12 | 5.98 | 3.58 | 9 | 200.93 |
| Mana 3, live pursuit | 25 / 89 | 45.29 | 3.47 | 29.30 | 0 | 215.25 |
| Mana 3, both policies | 114 / 0 | 14.16 | 6.02 | 3.79 | 12 | 211.52 |
| Mana 4, original | 112 / 2 | 21.27 | 4.42 | 9.33 | 1 | 169.77 |

Reserve 8 fixes these solver tails by accepting considerably greater attrition;
it is not a cost-free policy repair. The original's smaller casualty count also
excludes the final assault because those campaigns stopped before winning. Mana 4
reduces the recovery tax with less attrition than reserve 8. Its 114 cases buy 298
Swordsmen and 147 Acolytes in total, alongside the same 114 Temples and Barracks.

Exact paired-policy data:
[mana 4](evidence/difficulty-worst-mana4.json),
[reserve 8](evidence/difficulty-worst-reserve8.json),
[live pursuit](evidence/difficulty-worst-pursuit.json),
[both](evidence/difficulty-worst-combined.json),
[mana 4 plus live pursuit](evidence/difficulty-worst-mana4-pursuit.json).
Each report links its retained compressed rows and records the selection source.

## Crystal spending is still an open economy problem

The three core candidate plans spend **0 / 0 / 2 crystals** and finish with
**42.15 / 48.63 / 45.47** on average. Shorter recovery lowers the surplus but does
not make crystal decisions recur. These plans take free approaches, so that alone
would not establish whether current crystal recruits are useful.

A separate **1,440-run** candidate probe covers 20 seeds × all themes, heroes and
routes with paid Control and Flight plans. Control buys Sappers and Adepts; Flight
buys Skyriders and Wardens. They actually spend **7.81 / 6.05 crystals**, including
replacements, yet finish with **51.00 / 39.81**. They win 717/720 and 718/720,
respectively; the other five remain playing. Mean casualties are 7.93 / 5.02,
and individual battle defeats total 108 / 22. Automatic use of these more expensive
roles is not demonstrated to dominate the core plans.

[Specialist report and exact rows](evidence/difficulty-mana4-specialists.json)
retain all purchases. Optional paid encounter approaches are not measured here.
Further useful crystal-spending choices are needed; lowering the starting grant
and shortening campaigns do not resolve the late surplus. This is a separate
economy task, not a reason to charge for existing actions or add arbitrary upkeep
inside this recovery experiment.

## Recommendation and verification

The accepted decision is **challenge-2 for future new games**, keeping
challenge-1 loadable with mana 3. Challenge should get its tension from constrained
funding, expansion, reinforcement choices and readable rival pressure; a near-full
mana waiting cycle adds little useful pressure. Teach the existing alternative of
an earlier assault with a smaller reserve and greater casualty risk, rather than
presenting either automatic policy as the intended way to play.

This recommendation does not close G02/G07: the two reported policy tails, crystal
surplus, limited optimal-play evidence and lack of player enjoyment evidence remain.
The checkpoint passed **1,004 full tests**, including exact actual-v11 continuation,
frozen-ID/replay behavior and candidate recovery. Standard regression fuzz passed
12 campaigns and 12 scene runs; the unrelated Tribes fuzzer passed 60 AI games and
20 random-input runs. The large candidate matrix provides the new profile's public
campaign coverage; Standard scene fuzz is not claimed as random candidate coverage.

The separate selector change captures five actual pre-switch Challenge-1 saves
in `tests/eador/fixtures/v12_challenge1_cases.json`, with their source revision.
Public tests preserve every recorded field through rest, standalone and linked
replay, next-shard advance and defeat recovery. The old mana-3 rules remain in
those outputs; new Challenge starts and their replay use mana 4. The combined
mode/campaign/pressure/rival/UI integration suite passes 152 tests after selection.

At integrated source `0e27175`, native current-mode openings and three actual
pre-switch UI continuations also pass. The separate UI fixture records source
`2ce3040` and preserves that UI's roster-order retinue selection; it does not
sort away differences from the earlier model-command fixture. New Challenge
completes the linked campaign after losing and recovering a realm, with 396
inputs and 13 exact reloads. [Retained native evidence](evidence/shardbound-integrated-0e27175/README.md)
shows both the original +3 and current +4 mana forecasts and actual completion.

Reproduce the full candidate and one-factor policy comparisons:

```sh
uv run python tools/audit_eador_difficulty.py --seeds 100 --modes challenge --rules-id challenge-2 --report /tmp/difficulty-mana4-full.json
uv run python tools/audit_eador_difficulty.py --modes challenge --worst-from docs/evidence/difficulty-matched-plans.rows.json.gz --mana-reserve 8 --report /tmp/difficulty-worst-reserve8.json
uv run python tools/audit_eador_difficulty.py --modes challenge --worst-from docs/evidence/difficulty-matched-plans.rows.json.gz --adaptive-interception --report /tmp/difficulty-worst-pursuit.json
uv run python tools/audit_eador_difficulty.py --modes challenge --rules-id challenge-2 --worst-from docs/evidence/difficulty-matched-plans.rows.json.gz --report /tmp/difficulty-worst-mana4.json
uv run python tools/audit_eador_difficulty.py --seeds 20 --modes challenge --rules-id challenge-2 --plans control flight --report /tmp/difficulty-mana4-specialists.json
```
