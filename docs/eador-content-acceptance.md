# Hero paths and content acceptance

This audit inspects game source `1b54ad5` and adds only a verification tool and
integration tests at `03a0493`. Game/framework code is unchanged. G03/G04 remain
incomplete. The immediate gap is **demonstrated player decisions across whole
builds**, not another content ID or an unexplained new ability.

## What changed the next action

All eight preferred disciplines complete the same paid Standard seed-7 campaign
through Foundries and Throne. Each earns rank 2 on the first shard, rank 3 on the
second, then spends its fourth advancement on the remaining discipline. Each
also completes a separate journey with actual capital loss and the single
recovery expedition during shard two. No ranks, XP, money, equipment or troops
are inserted. Earned choices and full transition states roundtrip exactly.

This rules out a progression/continuation blocker on these routes. It does not
prove eight balanced manual builds. The shared policy buys a Barracks, refills
with Swordsmen, invests in recovery and uses explicit tactical autoplay. Its
success cannot establish three different viable army plans.

`tools/audit_eador_disciplines.py` varies only the preferred offered discipline.
It reuses the existing paid itinerary and input driver. The model and UI paths
call the same game commands; the UI driver rejects unadapted mutations. Recovery
uses its real retinue controls. Every report retains each decision's full before
and after state, full phase checkpoints, and the final state. Native UI reports
also retain every input and exact F5/F9 reload count. Ordered playback is finished
through the visible Space control, so these are not natural-playback or manual
combat observations.

Direct model results, **one seed and one policy per path**:

| Hero | Preferred discipline | Sum of three shard turns | Fallen troops | Mana spent | Recruitment gold | Pre-assault recovery turns |
|---|---|---:|---:|---:|---:|---:|
| Commander | Quartermaster | 35 | 3 | 104 | 383 | 3 |
| Commander | Tactician | 31 | 2 | 80 | 405 | 0 |
| Warrior | Duelist | 36 | 8 | 132 | 450 | 4 |
| Warrior | Vigor | 38 | 10 | 140 | 495 | 6 |
| Scout | Pathfinder | 35 | 8 | 96 | 585 | 5 |
| Scout | Skirmisher | 32 | 11 | 112 | 540 | 5 |
| Wizard | Channeling | 43 | 8 | 188 | 450 | 11 |
| Wizard | Restoration | 37 | 6 | 135 | 450 | 5 |

These are policy outcomes, not isolated skill-effect measurements. Different
battles, losses and recovery decisions accumulate after choosing a path. Mana
counts actual battle expenditure; pre-assault recovery counts only that policy's
final-approach waits. The separate recovery routes include deliberate neglect to
lose the capital and must not be compared to direct routes as pacing results.
Forty targeted progression/journey integration tests pass, including all eight
recovered campaigns. [Retained current evidence](evidence/shardbound-disciplines-03a0493/README.md)
provides exact source and scope.

## G03: evidence by requirement

| Requirement | Concrete current support | Remaining acceptance work |
|---|---|---|
| Four distinct heroes | Commander grants army attack/capacity; Warrior health/melee attack; Scout campaign actions/ranged attack; Wizard mana and initial spells (`model.py`, `battle.py`). | Compare how those differences alter a player's full build, rather than relying on class names. |
| Two paths each, repeated choices | Eight recovered journeys above earn 2→3→3+1 ranks through public commands. All eight disciplines have relevant effect tests in `test_progression.py`. | Paired earned **manual** rank-2 scenarios for both disciplines of every hero; add counters, not only favorable arenas. |
| Explained and usable choices | [Earned decision matrix](eador-choice-reading.md) exercises every offered option by keyboard/mouse, including later ranks and single-option choices. [Hero matrix](eador-reading-size.md#hero-and-equipment) shows both disciplines and complete descriptions. | Those historical matrices prove their source versions. Current natural first-run comprehension still needs independent/human observation. |
| Saves, defeat, recovery, departure | Current routes preserve full saved states before/after loss, recovery and both departures. `test_discipline_journeys.py` checks ranks at each boundary. | Broaden meaningful manual decisions across seeds/difficulties. A small saving property does not establish balance or enjoyment. |

The next manual comparison should start from the **same earned first-level
choice**, then command the two resulting paths. For Commander, compare paid
reinforcement/recovery against retaliation-free troop engagements. For Warrior,
compare chained wounded victories against protected hero attacks; automatic
Vigor results above show why passive recovery cannot simply be assumed useful.
For Scout, compare a rough-ground extraction against ranged attack-then-move
pressure with a blocked escape counter. For Wizard, compare finite Bolt tempo
against healing through the Acolyte's order, including a scenario where spending
the shared mana on one prevents the other. Record the paid preparation and
counter-scenario; do not tune a class merely because this one automatic policy
performs worse with it.

## G04: content support and highest gaps

All current entries have Codex text from the actual rule tables. The catalogue,
choice and Hero matrices cover current known entries' paging, prices, descriptions
and icons, but most retained native matrices predate `1b54ad5`. Their provenance
must remain historical. These sources establish useful support, not a blanket
current-candidate acceptance certificate.

| Content | Actual distinguishing behavior and access | Strongest relevant evidence / gap |
|---|---|---|
| Militia | No building, 20 gold/1 upkeep; Rally spends its own order to clear adjacent Pin. | [Relief Column](eador-relief.md) exercises enemy support/denial; troop/relic Rally public tests cover no order refresh. Ordinary attacks alone do not exercise this role. |
| Swordsman | Barracks, 45 gold/2 upkeep; durable damage dealer with movement 3, attack 11, defense 4. | Paid complete campaigns repeatedly use it. Relative to Warden it is cheaper, faster and hits harder but cannot Swap. No added order is justified solely by its lack of one; a paired paid replacement/positioning comparison should establish whether that direct front-line role gives enough choice under G04. |
| Archer | Archery Range, 35 gold/2 upkeep; Pin trades damage for delayed movement. | `test_pin.py`, native [role journey](eador-roles.md#player-controls-and-presentation), Relief and extraction journeys use real Pin and counterplay. |
| Acolyte | Temple, 45 gold/2 upkeep; Heal spends troop order/shared mana; improves rest. | [Role journey](eador-roles.md) and later Causeway/Explorer plans use paid healing. Compare preservation of hero orders against fielding another combat body over a complete campaign. |
| Pikeman | Barracks, 40 gold/2 upkeep; Brace pre-empts melee once, replaces ordinary retaliation. | Guard/Brace exact previews, native Guard and authored Aerie/Relief journeys. Ranged attacks/expiring stance are explicit counters. |
| Ranger | Archery Range, 50 gold/2 upkeep; shoot then move; no intrinsic Pin or rough-ground immunity. | [Role journey](eador-roles.md) and Explorer/Relic manual orders exercise movement after a shot, with Pin/occupancy costs. |
| Warden | Barracks, 55 gold/2 upkeep; Swap trades its order and both moves for ally extraction. | [Role journey](eador-roles.md) and complete Gate/Explorer plans; exact retained ally actions and exposed replacement are exercised. |
| Sapper | Marketplace, 60 gold +1 crystal/2 upkeep; one Smoke screens both sides' fire and magic. | Observatory/Smuggler Screen paid plans exercise friendly blocking, saved charges and alternative formations. Later campaign value still needs whole-plan comparisons. |
| Rune Adept | Mage Tower, 65 gold +2 crystals/2 upkeep; one Repulse needs an unanchored target and empty landing. | [Causeway](eador-causeway.md) actual hostile Repulse, Guard/occupancy/focus counters and retry; control/active-relic journeys exercise the player command. |
| Skyrider | Temple, 85 gold +3 crystals/3 upkeep; crosses rough/occupied cells but must land empty. | Aerie/Relief public and native plans demonstrate landing, Pin and Brace counters. Flight is a passive movement trait, not a ninth active counted toward the eight-ability floor. |

The eight counted active capabilities are **Bolt, Heal, Brace, Pin, Swap, Rally,
Smoke and Repulse**. Acolyte Heal and relic copies are alternate casters, not
extra capabilities. Guard, basic attacks, movement, Flight and Evacuate do not
inflate that count. Exact legality/previews, actual orders and saved outcomes
exist in the corresponding public tests and authored native journeys; what is
still missing is a current candidate record linking them to three different
complete army plans and their counter-scenarios.

| Relics | Reach / explanation / effect support | Remaining limitation |
|---|---|---|
| Moonstone, Ember Lens | Earned Shrine/Tower rewards; spell access/power/cost and actual casting; continued equipment and saved choices. | Compare equipment opportunity cost across complete builds, including removing access before a different encounter. |
| Merchant Seal, Oak Standard | Earned Caravan/Grove rewards; real recruitment reduction and recovered troop HP in `test_progression.py`; Seal used by complete paid policies. | Sale/equipment values and the Standard's extra recovery need meaningful competing choices, not only arithmetic checks. |
| Iron Crown, Wayfarer Boots | Earned Barrow/Camp rewards; no-retaliation preview and saved movement traits; Explorer demonstrates earned Boots in an extraction route. | Crown's actual safe attack and Boots' movement should each be recorded on the current packaged candidate as deliberate alternatives to spell/relic powers. |
| Watch Bell, Storm Quiver | Earned Watch/Den and later authored rewards; hero Brace/Pin capabilities plus public command tests and original medallions. | Distinguish commanding the equipped hero from merely having a Pikeman/Archer in a successful army. |
| Veil Censer, Porter's Rune, Mirror Badge, Vanguard Drum | [Four earned native journeys](eador-active-relics.md#native-earned-use-verification): purchases, source, reward, equip, later manual use and exact reloads; two complete linked Gate campaigns. | Censer saved only one early HP in its measured plan; Rune's delayed recovery was slower than a complete opening ring; Badge can expose both units; Drum continuation was autoplay. These limitations are useful counterplay evidence, not reasons to count four automatic dominant upgrades. |

Do not add more relics or abilities before comparing three complete paid rosters.
The [first persistent army pilots](eador-army-plans.md) now carry **durable
melee/sustain**, **ranged reposition/extraction**, and **Smoke/Repulse/flight
control** formations through three earned shards, with actual replacements and
distinct retinues. All finish under autoplay, but mobile loses 32 troops and
control loses 22, including its entire final army. These are executable candidates;
the manual decisions, counter-scenarios and capital-loss recovery remain open.
The [paid Sapper timing choice](eador-authored-investment-comparison.md) separately
reproduces 12 versus 23 wounds through native controls from an earned save. That
local advantage does not establish the complete control formation's viability.
The old economy study's three purchase orders eventually all fill with Swordsmen;
it therefore cannot substitute for these army-plan acceptance cases.

No reproducible game defect was found in the inspected G03/G04 routes. This
increment adds no framework interface, content, rule, schema or balance change.
