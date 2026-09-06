# Autoplay survival and current campaign limits — 2026-09-06

Source **d643410a889cc8f097c2d497c2b9ce65d0c1263d** lets another ready ally act
before retrying a player autoplay attack whose forecasted reaction is lethal.
Each actor may defer once; movement and spent orders remain spent. Enemy order,
unit statistics, prices and the save schema are unchanged. This belongs in
Shardbound's battle policy, with no new Saga2D API.

The earned Control example exposed a real avoidable loss: the former policy
killed a two-HP Rune Adept before other ready attackers finished the same Guard.
The new policy preserves the Adept. Four public-behavior regression cases cover
that exact earned save, a deferred archer revisited after an ally spends the
enemy's reaction, bounded execution when every available attack is lethal, and
unchanged enemy ordering. Autoplay can still lose troops and make strategically
poor decisions.

## Current decisions through native controls

The audit authenticates each historical journal and earned starting save, then
executes both current continuations. Historical results remain separately
identified. The native verifier consumes the fresh report, checks current source
hashes, reproduces every journal command through actual controls, and performs
F5/F9 after each command through rewards and immediate paid replenishment.

| Earned decision | Current branch | Result | Fallen troops | Living battle HP | Replacement gold / crystals |
|---|---|---|---|---:|---:|
| Control | Autoplay | Win, round 5 | None | 140 | 0 / 0 |
| Control | Manual attack order | Win, round 5 | None | 140 | 0 / 0 |
| Mobile | Autoplay | Win, round 5 | Warden | 126 | 55 / 0 |
| Mobile | Withdraw Warden, then autoplay | Win, round 5 | Militia | 122 | 20 / 0 |

All four branches finish at two mana and restore any missing target roles.
Current Control autoplay now matches the manual branch's survival and expense;
the older 65-gold/two-crystal advantage described in
[the historical comparison](../army-decisions-474b41a/README.md) no longer applies
against this autoplay implementation. Mobile's manual choice still transfers a
casualty and saves 35 gold at the cost of four living HP.

The retained native receipts cover **165 inputs, 24 forecast layouts and 17
exact command/save/reload joins**. The three retained PNGs were opened and
inspected: the lethal warning at 125%, Control's surviving Adept after rewards,
and Mobile's paid manual aftermath. These are native continuations from earned
model preparation, not complete native campaigns or independent player tests.

## Full policy follow-up includes an unfinished attempt

The three existing Standard seed-7 Foundries→Throne policies ran serially with
their default 25% CPU allowance. All **767 recorded commands** retain contiguous
before/after states and exact saved continuation.

- Sustain completes all three shards with the same 230 commands and final save
  as the historical pilot: 35 summed shard turns, four fallen troops, no tactical
  defeats and 345 recruitment gold.
- Mobile completes, but takes 63 summed shard turns, 38 fallen troops, three
  tactical defeats and 1,600 recruitment gold. Its historical pilot took 44
  turns, 32 losses, two defeats and 1,250 gold. At their first divergence, the
  new battle policy preserves a wounded Warden; subsequent recovery, recruitment
  and rival timing differ. The local survival fix does not make this whole
  automatic campaign policy better.
- Control remains **playing**, on its first shard at turn 50, after the existing
  40-iteration final-assault policy bound. This is not campaign completion or
  defeat. It has 16 battles, 15 fallen troops, one tactical defeat, and 1,115 gold/26 crystals spent on
  recruitment. Its final state is healthy and ready at 23/24 mana; the policy
  consumed its final iteration waiting for mana. At the matched turn-46 first-
  shard endpoint, the old policy had won while the current one was still playing.

The reports preserve these unfavorable results. The old three-completion claim
is historical evidence, not a result for current source. Mana readiness, rest,
replacement of injured veterans and rival interception all affect these scripted
journeys; changing unit prices from these runs would not isolate army balance.
A complete deliberately directed Control campaign remains useful next work.

## Other verification and limits

The complete suite passes **1,275 tests in 170.20 seconds**. Three initially
failing journey assertions assumed an incidental turn or mana value from the old
autoplay result. The final journey respects the visible rival's next-turn capital
attack; paired spell-cost assertions use earned starting mana. Victory and exact
saved restoration remain required. No game-rule workaround was added for those
tests.

Tribes' required cross-game fuzz passes 60 AI games and 20 random-input runs.
The bounded Shardbound run passes 12 model runs and 12 scene runs with 2,161 input
events, including 236 inputs verified inert during playback. Random campaign
cleanup ends in defeat; these are invariant/save checks, not 12 winning campaigns.
No cancelled stress matrix or two-hour soak was restarted. All expensive jobs
ran serially and ended. These checks do not measure battery life.

`verification.json` checks every retained report's source hashes against the
named commit, unchanged-source flags, native input-report hashes and journal
joins. Original temporary paths in raw reports are retained as provenance; the
corresponding files are copied into this directory without changing their bytes.
`sha256.json` identifies the retained files.

The independent UI-only attempt timed out before observing the app: zero inputs,
screenshots or walkthrough credit. Its separately identified launched process
was closed. The preserved Mac archive remains source **32f354c** and predates this
autoplay change. No new package, human acceptance, broad balance conclusion or
release gate is claimed. **G01–G19 remain incomplete.**
