# Late realm decisions: two bounded experiments

**Recommendation: ship neither candidate.** The small remittance change removes
money without changing the tested investment decisions. Two-soldier outposts buy
some attrition relief, but fail their proposed job of protecting the warned
province and require unresolved deployment, rival-planning and bankruptcy rules.
Keep G07 open. Neither conclusion justifies a global income cut or larger automatic
fees on the existing game commands.

## Concrete remaining failure

The game now has useful optional [Infusion](eador-crystal-economy-proposal.md) and
[replacement](eador-army-replacement-interface.md) choices. Their action costs,
spell access and lost veterans matter. In the retained late paid army, their gold
costs still do not force an investment choice: 421 gold funds the two missing
buildings, a fresh Warden replacing a veteran, and Infusion together, leaving
252 gold before the required wait. Rest then improves health/mana and earns more
money. The competing cost here is the last travel action, not financial scarcity.

This follows the existing [source-attributed ledger](eador-late-investment-review.md):
370 net income and 310 battle/site rewards versus 293 building/recruit spending
on the example route. The early Temple commitment leaves just **2 gold on turn 3**.
Thus a rich ending is not evidence that the entire opening can absorb a cut.
Historical [v9](eador-economy-v9.md) and [difficulty](eador-difficulty-candidate.md)
matrices also report large surpluses, but their different source versions remain
historical evidence; they are not relabeled as current balance tests.

## Candidate R1: limit marginal province remittance

This runtime parameter experiment pays full gold from Westwatch, Marketplace and
the two richest other owned provinces; further provinces remit 25%. The current
saved mode's percentage still applies, with one final rounding. Encirclement
still blocks home/Market production. Crystal production, purchases, passive
recovery, combat and rival finances are unchanged. The richest-two rule is
unambiguous, but would need a visible explanation if ever used in a real game.

Nine selected pairs repeat the existing public automatic policy: three paid plans
(Economy, Sustain, Spells) for seed-0 Commander/Frontier in Standard and current
Challenge, and seed-7 Scout/Elderwild in Standard. Both variants execute real
campaign commands; each repeats exactly. This is **18 selected campaigns**, not
another broad balance matrix.

| Paid case | Plan | Victory turn, both | Gold: ordinary → R1 |
|---|---|---:|---:|
| Commander / Frontier / Standard | Economy | 12 | 487 → 443 |
| same | Sustain | 13 | 488 → 436 |
| same | Spells | 13 | 427 → 375 |
| Commander / Frontier / Challenge | Economy | 10 | 347 → 326 |
| same | Sustain | 14 | 494 → 449 |
| same | Spells | 14 | 442 → 397 |
| Scout / Elderwild / Standard | Economy | 9 | 255 → 237 |
| same | Sustain | 9 | 252 → 234 |
| same | Spells | 13 | 305 → 263 |

Every pair has identical purchases **and their timing**, combat casualties,
recovery waits and mana spent. No run has upkeep shortfall or desertion. The
first reduced income occurs on turn 6; the actual turn-3 two-gold Temple survives
unchanged. In the already-earned late state, prospective R1 income is 43 instead
of 51, but all quoted investments remain affordable. After buying both buildings,
replacing with Warden and infusing, the following treasury is **284 instead of
292**. Existing wealth is not retroactively removed.

**Reject this candidate:** it changes bookkeeping without demonstrating a
changed decision, and reduces the marginal value of conquest while leaving
Marketplace's fixed benefit intact. Increasing the cut until a selected treasury
looks small would be tuning to a target number, not evidence of better play.
A future separately versioned income policy would first need a real alternative
purchase or route decision, plus preserved opening/recovery viability. Do not
change any existing frozen rules ID to try it.

## Candidate O1: dispatch two finite defenders

The prototype dispatches two fresh ordinary recruits to an adjacent owned
province while the hero is in an owned camp. It costs their actual current prices
and one hero action; normal recruitment prerequisites apply. Their normal upkeep
is charged before the rival acts. These troops have no Commander bonus, experience,
free healing, refund or respawn. This is a hypothetical new order applied only to
a detached validated save. The ensuing rival clash, survivor HP, retreat and
player interception use existing public rules.

The retained Accessible pursuit state is on turn 6 with one action, 172 gold,
23 crystals and a wounded full army. Three surviving rival troops are visibly
about to attack Heartwood. The original state and subsequent saved/uninterrupted
branches are kept in the report.

| Choice | Direct investment | Intercept turn | Hero-army deaths | Army wounds left | Mana left | Gold / crystals left |
|---|---|---:|---:|---:|---:|---:|
| Intercept immediately | none | 6 | 1 | 18 | 2 | 197 / 23 |
| Rest, then intercept | none | 7 | 0 | 19 | 8 | 230 / 26 |
| Existing Tower + Infusion, then wait/intercept | 75g + 5c; 1 action | 7 | 0 | 19 | 14 | 155 / 21 |
| Prototype two Pikemen, then wait/intercept | 56g + 4g first upkeep; 1 action | 7 | 0 | 10 | 12 | 170 / 26 |
| Prototype Pikeman + Archer, then wait/intercept | 55g Archery + 53g troops + 4g upkeep; 1 action | 7 | 0 | 10 | 12 | 118 / 26 |

**Both outposts die and lose Heartwood.** The Pikes leave a Guard at 24 HP and an
Archer at 2 HP; the mixed pair leaves a Guard at 24 HP and Archer at 10 HP. The
weakened expedition plans to return home instead of pressing another attack.
The hero then intercepts it and recaptures Heartwood. Both waiting controls also
recapture it, so no permanently protected territory or freed route is claimed.
The outpost deaths are **two additional purchased soldiers**, separate from the
zero hero-army deaths in those rows. None of these solvent branches tests guard
bankruptcy. Wound totals count surviving hero troops only.

There is a genuine local tradeoff: the Pikes spend 60 gold and the action for
nine fewer surviving wounds and four extra mana over ordinary rest. The existing
Tower/Infusion option spends 75 gold and five crystals for six extra mana over
rest, plus permanent Tower/spell access. The mixed outpost costs more here while
leaving the same final hero army; the extra Archery building is a permanent asset,
so it is not silently treated as money that disappeared. This is insufficient
evidence to add an entire defender system as a general economy remedy.

**Defer outposts, rather than strengthen them to force this case to win.** A
useful next tracer would have to protect an actually threatened holding or free
an earlier objective action compared with ordinary interception, without making
repeated garrison purchases an income-farming loop. It must also answer:

- When the hero is present, paid defenders must contribute without weakening
  defense. Current hero defense ignores province guards; combined deployment is
  not implemented by this prototype.
- Rival route planning must account for finite defenders and avoid repeat losing
  attacks. A path cost based on guard count is not sufficient evidence of that.
- One transparent upkeep forecast must include both forces and specify which
  soldiers desert when money is short. Current desertion selects only hero troops;
  merely adding outpost upkeep is not a complete bankruptcy implementation.

No reserve pool, new battle mode or framework abstraction is warranted by this
single attrition result. Current encirclement/desertion tests remain valid; these
solvent local experiments do not extend their acceptance to hypothetical guards.

## Reproduction and limits

[Tool](../tools/prototype_eador_late_realm.py),
[retained report](evidence/late-realm-prototype.json), and
[original paid inputs](evidence/crystal-service-comparison.examples.json).
Source **456742c** records hashes for the game, policy helpers and prototype;
none changed during execution. All nine ordinary/R1 pairs repeat exactly, and
the five local pursuit branches match after a saved continuation and without it.
The late existing-wealth comparison never subtracts hypothetical past taxes.

The two runtime subclasses are explicitly **non-production experiment adapters**.
They do not edit difficulty registries, frozen IDs, world generation, tactical
formulas, game commands or schemas. Their JSON is evidence of the experiment,
not a supported new policy save. A production candidate would need a new immutable
rules identity and explicit migration/continuation tests before UI integration.
No native/UI, all-difficulty balance, bankruptcy or G07 completion claim is made.

```sh
uv run python tools/prototype_eador_late_realm.py --report /tmp/late-realm.json
```
