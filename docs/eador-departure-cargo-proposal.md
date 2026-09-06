# Departure cargo: measured proposal, no production rule

The 100-gold chest creates a small linked-opening choice, but does not repair the
remaining G07 economy problem. I would retain this prototype rather than implement
cargo as the next economy fix. It can support a future departure-customization
increment: an earlier broad army sometimes preserves a soldier, while carrying a
specialist can finish sooner. The controls also show several unchanged outcomes
and a strong influence from the existing arrival formation.

This follows the rejected [veteran wages](eador-veteran-upkeep-proposal.md) and
[remittance/outposts](eador-late-realm-proposal.md). No production command, schema,
profile, ordinary recruitment, recovery or income rule changed. No second price
or grant was tested.

## Exact hypothesis

- One optional chest costs **100 current gold** and occupies **one of the existing
  two troop carry slots**. It adds **100 gold** on arrival.
- Ordinary capped funding is computed **after payment**. At 511 departing gold,
  the quote is 411 remaining before departure, then 240 arrival gold instead of
  140. At exactly 100 departing gold, arrival is 200 rather than 140: only a net
  60-gold gain because payment also consumes the normal 40-gold carryover.
- Crystal funding, two relic slots, hero progression, surviving troop rank/XP,
  arrival healing and the existing fresh-Militia minimum of three troops remain.
  A chest does not buy an extra army-capacity slot or an extra hero action.
- Unselected veterans enter the existing garrison record. There is no refund,
  reserve pool, later recall or recurring shipment. The grant is ordinary cash
  after arrival; recovery uses its normal fixed funding, without a chest refund.

The tool returns a detached candidate plus a complete quote. It never mutates the
source departure. Accepting that candidate would be the atomic production action;
there is no production cargo command or save-format promise here.

## Two earned inputs and subsequent paid play

Both are Standard Commander linked campaigns. The input snapshots and the paid
specialist Watch battle are retained in the report, with source fingerprints.

1. Seed 7 wins its first shard on turn 13 with **511 gold / 28 crystals**. The
   compared retinue is Swordsmen 5 then 4, both rank 3, 42 maximum HP. Rootward is
   the offered next shard. Cargo leaves Swordsman 4 behind.
2. Seed 0 buys the actual Sapper/Adept/Skyrider control army, manually completes
   Border Watch with the existing public route, then wins the first shard on turn
   16 with **575 gold / 32 crystals**. The compared retinue is Militia 1 then
   Adept 5, both rank 3; the Adept has 36 maximum HP. Foundries is next. The primary
   cargo comparison leaves the Adept behind; a separate control keeps the Adept
   and leaves the Militia instead. The surviving rank-2 Swordsman remains in the
   garrison in all these comparisons.

Every continuation actually buys buildings/recruits, handles the visible rival,
fights the contract route and wins the next shard. Tactics use the explicit
automatic command; these are not manual-skill or optimal-play claims.

The **economy** plan is the existing Market → Barracks → Swordsman → Temple plan,
then Swordsmen. The **magic** plan buys Tower → one Adept if none was carried →
Barracks → Swordsman → Temple, then Swordsmen. Neither buys a duplicate Adept to
make the carried specialist look cheaper. Both follow the same contract itinerary
and the existing public recovery/interception policy.

Table entries are **next-shard victory turn / combat troop deaths / accumulated
battle HP loss**. Garrisoned troops are not counted as battle deaths.

| Earned departure and plan | Two veterans | One veteran, no chest | Same one veteran + chest |
|---|---:|---:|---:|
| Swordsmen → Rootward, economy | 13 / 1 / 268 | 13 / 1 / 273 | 13 / 1 / 262 |
| Swordsmen → Rootward, magic | 15 / 2 / 294 | 14 / 3 / 294 | 14 / 3 / 271 |
| Militia + Adept → Foundries, economy; keep Militia | 11 / 1 / 262 | 14 / 1 / 309 | 14 / 1 / 307 |
| Militia + Adept → Foundries, magic; keep Militia | 14 / 1 / 239 | 16 / 1 / 319 | 16 / 0 / 301 |
| Same original pair, economy; keep Adept instead | 11 / 1 / 262 | 14 / 2 / 305 | 14 / 2 / 314 |
| Same original pair, magic; keep Adept instead | 14 / 1 / 239 | 16 / 0 / 273 | 16 / 0 / 262 |

The economy plan mostly turns the chest into an earlier Temple and recruits,
without an earlier ending or fewer deaths. For example, Rootward buys Temple on
turn 1 instead of turn 2, and the final ordinary refill on turn 2 instead of turn
4; all three retinues still finish turn 13 with one death.

There is one concrete broader-army benefit. In the Foundries magic plan without
the old Adept, cargo buys Tower (75 gold / 2 crystals), fresh Adept (46 / 2),
Barracks (45) and Swordsman (32) on **turn 1**, leaving 42 gold. Without cargo the
same plan buys Barracks on turn 2 and that Swordsman on turn 3. Temple arrives on
turn 2 with cargo, turn 4 without it. At the actual covered Observatory on turn 3,
cargo fields six troops, including a rank-2 Swordsman; the unfunded control fields
five with a fresh Swordsman. Both bought Adepts actually use Repulse. The funded
army preserves Militia 1 at **4 HP**; the unfunded control loses it. Both finish
turn 16, but the original two-veteran magic party finishes turn 14 with one death.

Keeping the expensive Adept is not omitted from the comparison. Under magic it
finishes turn 16 with zero deaths both with and without cargo; cargo reduces
accumulated HP loss by 11 and spell use by 4 mana. Under economy it actually takes
9 more HP loss with cargo and gains no tempo. **Retinue selection changes the
initial formation:** with two troops, the Militia precedes the Adept; with only
the Adept selected, the free Militia are appended after it. These results measure
that real ordering consequence along with rank, cost and role, not pure isolated
“veteran power.” The original two-veteran baseline was not reordered to improve a
comparison.

## Boundaries, compatibility and limits

The executable checks reject two troops plus a chest, multiple chests, an invalid
survivor, duplicate normal retinue IDs, an unoffered destination and insufficient
gold without changing the original full state. Zero selected troops plus a chest
uses one slot and produces the normal three fresh Militia. The exact-price and
insufficient-funds cases are **controlled valid treasury fixtures**, not additional
earned departures.

A real cargo arrival is subsequently lost by public travel/end-turn/retreat
orders. A chest is refused during recovery; ordinary recovery restores **60 gold /
2 crystals**, never the 100-gold grant. An arrived or recovered save cannot redeem
a second chest. Reloading an old departure can replay the choice, just as it can
replay ordinary advance; the prototype does not claim to prevent save rollback.
No-chest advance is byte-identical to the direct public command. The existing 25
difficulty/compatibility tests pass, including actual v11 and frozen Challenge-1
arrival/recovery continuations. Old saved worlds and profiles remain unchanged.

The earned departures have far more than the 140 gold needed to pay while retaining
the ordinary cap. Their **price is not scarce**; the scarce thing is the carried
veteran and its formation position. If the player already leaves a carry slot empty,
the chest is a beneficial use of gold otherwise discarded at the transition. That
is not a repeatable duplication bug, but it must be shown as an intended option,
not praised as a difficult economic decision.

Cargo continuations still finish with **544–1,025 gold**. This proposal does not
create a continuing gold investment, bankruptcy pressure or standalone decision.
The six cargo runs do not improve victory turn versus their matching
one-veteran/no-cargo controls; one avoids a casualty. A later production proposal
should be justified as readable departure customization, with the exact fresh
arrival roster and funding visible. It should not be justified by consuming surplus
or by assuming a player will leave their best specialist behind. A useful further
acceptance target would be an actually chosen different paid objective approach,
not another large unchanged-policy matrix.

## Reproduction

Source **747b1bf**, after merging main's Aerie/campaign-reading checkpoint. The
[tool](../tools/prototype_eador_departure_cargo.py) retains 16 full continuations,
each repeated exactly; 202 battle continuations per pass are paired with an actual
save/load and compared in full. All 31 recorded source hashes remain unchanged.

```sh
uv run python tools/prototype_eador_departure_cargo.py
uv run pytest tests/eador/test_difficulty.py -q
```

The complete [JSON evidence](evidence/departure-cargo-prototype.json) includes the
earned inputs, quotes, exact arrivals/endings, individual purchases, real battles,
used charges, surviving HP, actual loss/recovery and rejected boundaries. Full
compatibility fixtures were not edited. No native cargo UI exists or is claimed.
