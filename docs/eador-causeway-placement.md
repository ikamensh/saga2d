# Causeway: actual Ruins arrival and production proposal

This is the retained pre-production audit. The [production record](eador-causeway.md)
adds real entry/retry, native input and the existing Tower infusion alternative.
The recovery checkpoints below follow the audit's rest policy; they are not the
earliest possible entry when crystals and a spare hero action fund infusion.

This follow-up supersedes the original proposal's unreviewed emphasis on
anchoring. Independent review found a valid **caster-priority** route: Archer,
hero and Acolyte (or Warden) finish the Rune Adept before it acts. It is retained
as a third plan. Equal-healing comparisons leave a modest real tradeoff; there
is no need to change HP, rules or AI to force Guard.

The proposal is one optional Ruins extraction site with the existing prototype
layout, finite roster, one free assembly, one-move cargo penalty and round-five
deadline. A single assembly is sufficient here: the tactical alternatives are
caster focus, anchoring, occupied push landing and a Scout flank. G05 asks for
meaningful authored choices, not twelve unique mechanics or twelve pairs of
deployment buttons. A nominal second toggle or fee would add no demonstrated
value. Production implementation and native acceptance are separate from this
source-attributed model audit.

## Safe replacement with a structural witness

Use the same narrow policy reviewed in Relief `49fb921`: inspect ordinary sites
in coordinate order, and replace the first with an unchanged same-kind site
whose exact gold/crystal/relic reward matches, whose `q` is no farther east,
and whose defender multiset is a subset of the replaced roster. Inherit the
replaced reward, and directly install the authored four-enemy roster; the
ordinary eastern extra Guard must not be appended.

For Ruins, exclude negative `q`, authored sites, the capital and the direct
road's fixed Crown source `(1,0)`. Negative `q` excludes home, Den, Explorer's
Camp, Observatory, Vault and the western fallback `(-2,1)`; the actual Watch
and Aerie are excluded by content kind. Neither possible Watch location is
overwritten when it actually holds Watch. The unchanged witness may itself be
the home Shrine; this preserves that original affordable source exactly.

The guarantee is structural. Of the twelve cells at `q>=0`, one is the rival
capital, one is Aerie and one is Watch. The other **nine ordinary cells use only
Tower, Barrow and Shrine**. Reserving `(1,0)` still leaves eight cells and three
kinds. Two must match. Equal kinds have equal ordinary rewards; a later `q`
has the same defenders, or the same defenders plus the ordinary eastern Guard.
Thus the later duplicate has an unchanged no-farther-east/no-larger-roster
witness. The implementation should fail clearly if later content invalidates
this invariant; it should not silently consume a unique source.

The 1,000-seed audit records every selected province and witness, and verifies
the complete reward multiset and every other province byte-equivalent after a
copied proposal mutation. Only site name/kind and finite site guard kind/HP
arrays change. Conquest defenders, province terrain, income, crystal yields,
ownership, roads and all authored sources remain exact.

| Selected position | Seeds |
|---|---:|
| `(0,-2)` | 405 |
| `(0,-1)` | 492 |
| `(0,1)` | 81 |
| `(0,2)` | 22 |

Seed seven chooses the ordinary Shrine at `(0,1)`, keeping home Shrine's exact
45-gold/two-crystal/Moonstone reward and Brigand/Goblin encounter. Its chosen
source remains optional: marching through the province does not explore it.
Keeping a reward obtainable behind a harder battle alone would be insufficient;
the witness explicitly preserves the original easier site and its entire world
location. This is a site-roster guarantee, not a proof of a globally shortest
or safest travel itinerary.

## Actual purchased travel

The audit uses current main `ef9a67f` game code and **unmodified Ruins** for all
travel. Commander follows the existing western support preparation; Scout
uses the smaller Explorer preparation. Both then travel to the selected
source and recover through ordinary commands. Automatic preparation combat and
the rest helper's real rival interceptions are retained explicitly. No source
is explored or changed during these journeys. The subsequent battle comparison
installs the hypothetical site only in a copy of each recorded arrival.

| Party | Actual total purchases | First fully healthy arrival | Mana |
|---|---:|---:|---:|
| Commander, six bodies | 279 gold, 2 crystals | Turn 9, hero level 3 | 10/18 |
| Scout, five bodies | 175 gold, 2 crystals | Turn 6, hero level 3 | 6/18 |

Both retain original Militia 1/2 and Archer 3 at level three, plus purchased
Warden 4 at level three. Commander also retains purchased Acolyte 5 at level
two. Their earned Moonstone remains equipped. Commander pays Barracks 45,
Warden 55, Temple 65, discounted Acolyte 39, and Tower 75 gold/two crystals.
Scout buys only Barracks, Warden and Tower. No troop is replaced or lost.

Commander has already intercepted the real rival during turn seven before
its healthy arrival. One more public recovery turn provides 14 mana at turn
ten; a second provides 18 at turn eleven. Its treasury goes from 347 gold/39
crystals at arrival to 465/53 at turn eleven through actual owned income and
upkeep. Those turns are not free injected mana.

Scout's subsequent recovery causes a real rival interception at turn six and
raises the hero to level four. The first fully healthy checkpoint with eight
mana is turn eight. Full recovery to the new 20-mana maximum takes until turn
eleven, with 719 gold/66 crystals versus 344/26 at the first arrival. The extra
captures/rewards, income, upkeep and level change remain in the full command
ledger. It would be wrong to treat the later Scout as the same level-three
fixture with mana edited upward.

## Fair manual comparison

Every row has an actual first affordable recovery-policy checkpoint and is also replayed
from that party's same fully recovered snapshot. All orders save/reload the
whole State exactly; attack/spell HP changes match public forecasts. All
surviving source rewards settle once. No allied unit dies in these lines.

| Commander plan | Recovery-policy campaign turn | Battle result | Missing HP | Mana spent |
|---|---:|---:|---:|---:|
| Caster focus | 9 | Escape R4 | 37 | 4 |
| Caster focus + Heal | 9 | Escape R4 | 15 | 8 |
| Guard | 9 | Escape R4 | 34 | 8 |
| Guard + Heal | 10 | Escape R4 | 12 | 12 |
| Occupied push landing | 10 | Escape R4 | 28 | 12 |
| Occupied landing + Heal | 11 | Escape R4 | 14 | 16 |

Caster priority commits three early attacks and accepts melee retaliation. It
leaves the rear Militia free to approach the exit Pike. Guard keeps the Adept
alive for another round and spends its carrier's initial order on defense; the spare
Militia still advances. Occupying the push landing frees an early Bolt but
delays that Militia, requiring another Bolt on the Pike. The positioning and
order costs are real even though all three can win in the same battle round.

The fair Guard healing line sends Militia 2 from `(2,-3)` to `(2,-1)` in round
four to finish the Ranger's last four HP, freeing Acolyte to Heal the hero. It
ends hero 38/44, Militia 26/32. Caster-focus + Heal ends hero 35/44 and the same
26/32 Militia: **Guard buys three fewer wounds for four more mana and, on the
actual low-mana arrival under this rest policy, one additional recovery turn**.
The later production audit also proves that ordinary Tower infusion instead
spends three crystals and one hero action at turn nine, leaving an action to
enter immediately with enough mana for either healed line. Occupied landing caps
Heal at the hero's fourteen missing HP and leaves the other Militia wounded;
it is a legal but comparatively expensive alternative in this measured party.
No claim of universally better recovery or optimal play follows from these
small differences.

| Scout plan | Actual checkpoint | Result | Missing HP | Mana |
|---|---:|---:|---:|---:|
| Oblique ranged escape | Turn 6, L3 | Escape R4 | 41 | 4 |
| Same orders, later full recovery | Turn 11, L4 | Escape R4 | 34 | 4 |
| Optional Heal, first affordable | Turn 8, L4 | Rout R4 | 19 | 8 |
| Same healed line, full recovery | Turn 11, L4 | Rout R4 | 19 | 8 |

Scout has no Acolyte. Healing spends its own action after reaching the exit,
so it cannot Evacuate that phase. The remaining Guard attacks during the fourth
enemy phase and dies to the leveled Scout's retaliation, producing rout. The
escape line ends before that extra enemy phase. Healing is not a free final
click that preserves the same escape outcome. The same level-four snapshot
comparison isolates this tactical cost; the first-affordable comparison keeps
the actual campaign time and rival consequence visible.

## Concrete production scope

Keep the tested layout/HP/rules and one free assembly. Add a new game-owned
source ID with its saved inherited reward, use a small duplicate-site helper
only if it simplifies the two concrete Relief/Causeway callers, and preserve
existing loaded worlds and recovery entries without regeneration. No schema,
Battle AI or Saga2D strategy abstraction is needed.

The briefing should teach caster priority alongside Guard/Brace anchoring and
occupied landing cells, show the one-charge Repulse and finite enemy roster,
and quote the actual inherited reward. It must not imply that Guard is
mandatory. Codex should use the same variable-reward guidance as Relief.

Production acceptance still needs: real low-mana and recovery preparation
helpers reusable by input adapters; a source-specific finite failure/retry and
once-only reward; an actual saved old replaced-site continuation; 100/125 text
briefing/Codex and native command/forecast journeys; independent review and
full/fuzz checks. The bounded earned comparison supports implementation, but
the authored pattern count alone will not close G05 or the release criteria.

Use a detached checkout of source `2749a725b2f6f64e47d5f5de4c1339e0fc165996`
and run `uv run python tools/audit_eador_causeway_placement.py` to reproduce the
1,000-seed source audit and sixteen actual-arrival tactical comparisons. The
default compressed report is `/tmp/causeway-placement.json.gz`. The
[retained report](evidence/causeway-placement-2026-09-06.json.gz) records source
`2749a725b2f6f64e47d5f5de4c1339e0fc165996`, 45 hashes matched to that Git
revision, 1,000 witnesses, 82 public travel-command/reloads and 650 tactical
order/reloads across sixteen comparisons. The gzip is 186,009 bytes, SHA-256
`0111c8a68ce1d80fe517c6a119bffe01dbaa0d55ac5594b6b485d61baa84c442`.
The old proposal tool was absorbed into `tools/audit_eador_causeway.py` and
deleted after production integration; its temporary content must not be run
against newly generated production worlds. The audit, original prototype regressions and 78 existing public
Guard/control/extraction tests pass. No game source changed during measurement.
