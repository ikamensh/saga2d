# Three paid army plans

This development audit asks whether three different formations remain usable
through an entire linked campaign. It does not add game rules, framework APIs,
troops, money, experience or relics. G04 remains incomplete: the first executable
policies use explicit tactical autoplay, so their results cannot establish
manual depth, player understanding or balance.

## Candidate formations

| Plan | Paid persistent formation | Earned advancement order | Travelling priorities |
|---|---|---|---|
| Sustain, Commander | Two Swordsmen, Pikeman, Acolyte, Archer, Militia | Quartermaster, Tactician, Quartermaster, Quartermaster | Swordsman and Acolyte |
| Mobile fire, Scout | Two Rangers, Warden, Archer, Militia | Pathfinder, Skirmisher, Pathfinder, Skirmisher | Warden and Ranger |
| Control, Wizard | Sapper, Rune Adept, Skyrider, Acolyte, Militia | Channeling, Restoration, Channeling, Channeling | Skyrider and Rune Adept |

Every plan starts with the shipped two Militia and Archer. Purchase order is
disclosed in `PLANS`; missing roles are restored in that order. Buildings and
both recruitment currencies must be affordable. A full army retires its weakest
surplus member through the ordinary one-action paid replacement. No refund or
replacement experience is invented. Departures carry up to two actual surviving
veterans, in roster order to agree with the UI's checklist. Later shards rebuild
buildings when missing roles require them and purchase the formation again. A real lost capital
uses the one available recovery expedition, with its actual smaller budget;
terminal failure and finite policy bounds remain in the report.

An earned Merchant Seal is equipped for purchases, then exchanged for the plan's
preferred owned battle relic. Newly discovered relics are kept and duplicates
distilled through the offered choice. Both skill paths and the chosen two relics
are recorded as public commands. The tool follows the existing economy audit's
finite itinerary, rest/readiness policy and visible-rival interception. It does
not silently substitute Swordsmen when a specialist plan becomes expensive.

## Reproduce one bounded attempt

```sh
uv run python tools/audit_eador_army_plans.py --plan sustain --output /tmp/shardbound-sustain.json.gz
```

One invocation runs one candidate campaign, default Standard seed 7 through
Foundries then Throne. `--plan mobile` and `--plan control` select the other
formations; `--finale gate` probes the deadline and seal objective. Defaults
cooperatively target 25% of one CPU core. Run these sequentially. The tool has no
batch/matrix option; `--cpu-percent 100` explicitly removes its cooperative cap.

Each command retains full before/after saves and actual gold/crystal deltas. The
next command resumes from `State.from_json` of that result, rather than merely
comparing a serialization and continuing on the original object. Each battle
records its starting formation, earned state, rounds and result. Source hashes
identify the exact code used. These are actual autoplay rounds, including any
abilities the shipped policy selects, never evidence of deliberate manual use.

## Manual comparisons still required

* Sustain: Acolyte Heal while the hero attacks, Pikeman Brace against an actual
  melee entry, Archer Pin and Militia Rally. Compare an equally paid Warden
  substitution against a cheaper, faster Swordsman. Ranged attacks, expired Brace
  and a moving objective counter a stationary formation.
* Mobile fire: shoot before moving with Rangers and the Skirmisher hero; clear
  Pin before movement, and Swap the carrier to an exit while keeping its order
  for Evacuate. Enemy Pin, occupied escape cells, forest/smoke sight and the
  Warden's shorter movement are counter-scenarios. Rangers do not intrinsically
  Pin or ignore rough ground: that terrain benefit must be earned as Pathfinder.
* Control: Smoke the enemy firing lane while preserving friendly magic; Repulse
  an unanchored enemy into an empty landing; fly across a blocked line and land
  legally. Smoke also screens the enemy, Guard/Brace resist Repulse, occupied
  landings block movement, and Pin can deny flight reach. Shared mana creates an
  actual choice between Wizard Bolt and Acolyte Heal. Once-per-battle charges do
  not support an indefinite control loop.

Paired commands must begin from the same earned saved state and retain both
outcomes and later paid recovery. A favorable tactical example and an automatic
campaign completion are separate evidence, not substitutes for one another.

## Historical first serial pilots

On the historical source retained under `shardbound-army-plans-cd351a9`, one
Standard seed-7 Foundries→Throne attempt per plan completed all three shards.
The Commander integration check also passed, covering actual paid replacements,
an assembled target roster and exact command-by-command saved continuation.
The CLI reports retain complete command journals and source hashes; all runs
used the default 25% cooperative budget. These are working-source pilots, with
no native input or manual-order credit.

| Plan | Total shard turns | Fallen troops | Tactical defeats | Recruitment gold | Recruitment crystals | Battles starting with the full target roster | Exact saved commands |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sustain | 35 | 4 | 0 | 345 | 0 | 26 / 33 | 230 |
| Mobile fire | 44 | 32 | 2 | 1,250 | 0 | 33 / 37 | 299 |
| Control | 82 | 22 | 1 | 1,365 | 33 | 24 / 41 | 368 |

All three paid to restore their formation after losses; none used a
capital recovery expedition. Mobile fire's many losses and Control's 46-turn
opening shard are significant weaknesses of these automatic policies. Control
completed its final battle with **no surviving troops**, so campaign victory
does not establish a durable control army. The report preserves those outcomes.
Sustain's smaller losses alone do not prove dominance: hero, roster, mana,
investments and actions differ throughout these journeys.

The next useful step is deliberate manual play from these earned formations,
especially keeping ranged troops out of melee and deciding when specialist
orders justify their purchase. Adding content IDs or altering game balance from
these three automatic outcomes would outrun the evidence. Actual capital-loss
recovery for these three rosters remains unverified.

## First earned order comparisons

[Two historical saved decisions](evidence/army-decisions-474b41a/README.md) continue
through real rewards and immediate paid replenishment. Using three ready
attackers before the wounded Adept preserves it and avoids a 65-gold/2-crystal
replacement, with the same round and mana. Withdrawing the wounded Warden saves
35 replacement gold but transfers the casualty to Militia and leaves four less
living HP. Both are local model-command examples; no rest, native continuation
or complete manual campaign is claimed for that report. G04 remains incomplete.

## Current autoplay follow-up

[Source d643410 and retained current reports](evidence/autoplay-survival-d643410/README.md)
defer a predictably lethal player autoplay attack once while another ready ally
can act. The earned Control decision now preserves the Adept in both branches,
so manual attack ordering no longer saves replacement money against current
autoplay. Mobile's wounded-Warden withdrawal still trades a Militia casualty for
35 less replacement gold and four less living HP. The four current branches pass
native continuation through paid aftermath: 165 inputs, 24 forecast layouts and
17 exact command/save/reload joins.

The same three full campaign policies were also rerun, sequentially at the
default 25% CPU allowance. Their current results include a bounded unfinished
attempt:

| Plan | Completion | Summed shard turns | Fallen troops | Tactical defeats | Recruitment gold / crystals | Exact saved commands |
|---|---|---:|---:|---:|---:|---:|
| Sustain | Three shards | 35 | 4 | 0 | 345 / 0 | 230 |
| Mobile fire | Three shards | 63 | 38 | 3 | 1,600 / 0 | 357 |
| Control | First shard still playing; policy bound | 50 | 15 | 1 | 1,115 / 26 | 180 |

Sustain's complete journal is unchanged. Mobile's first divergence preserves a
wounded Warden, then the policy spends time recovering that veteran instead of
replacing a casualty with a fresh troop. Its complete campaign worsens. Control
spends the last of its 40 final-assault iterations waiting for mana and stops at
turn 50 in a ready, healthy state. Its partial totals cannot be compared directly
with the old three-shard totals. At matched turn 46 on the first shard, the old
policy had won and current Control was still playing.

These results distinguish a correct local survival improvement from an effective
whole-campaign policy. The completed directed Control continuation below examines
actual Tower infusion, specialist purchases, protection and rival timing. It
does not make these automatic policies effective or establish comparative
balance across the three builds.

## Directed Control first shard

[The directed continuation on unchanged game source](evidence/directed-control-990c377/README.md)
now follows the historical earned turn-6 opening through first-shard victory at
turn 9. Its 184 explicit commands include two paid specialist replacements,
two Tower infusions, three recovery turns and three battles. Repulse, flight,
shared-mana healing and attack order all entered the decisions. One rank-3
Militia died after an agent underestimated overlapping Guard attacks; that error
and the actual wounds remain recorded. The opening before this journal used
autoplay. This retained first-shard receipt is superseded in scope by the
completed continuation below; its original evidence remains unchanged.

All 184 commands replay through real native controls and exact F5/F9 continuation:
794 input events, 66.37 seconds, averaging 25.44% of one CPU core. The final
departure holds 140 gold, nine crystals and the four living specialists. This
provides one paid, directed first-shard itinerary; comparisons across builds and
counter-scenarios remain necessary for G04.

## Completed directed Control continuation

[The complete retained journey](evidence/directed-control-complete-718afc9/README.md)
continues that same historical turn-6 opening through Foundries and Throne:
**556 explicit commands, 15 battle victories and two battle casualties**. There
are no player autoplay commands after the earned anchor. The agent had source,
reachability and forecast access; this is not an independent human playtest.

| Directed segment | Capital victory turn | Wins / casualties | Gold / crystals paid | Campaign rests |
|---|---:|---:|---:|---:|
| Westwatch, beginning T6 | 9 | 3 / 1 | 150 / 11 | 3 |
| Foundries | 4 | 7 / 0 | 305 / 6 | 3 |
| Throne | 3 | 5 / 1 | 305 / 3 | 2 |

These expenses include buildings and infusions as well as recruitment, unlike
the recruitment-only columns in the autoplay tables. Recruitment and replacement
alone cost 360 gold and seven crystals within the continuation. Two paid
retirements are separate from its two battle casualties. The historical opening's
earlier costs and battles are outside these totals; the capital-turn sum of 16
includes its elapsed turns.

The earned Adept and Skyrider travel between shards, while new Acolytes, Sappers
and buildings use actual expedition funds. Foundries claims both required
provinces and defeats the finite rival expedition before its capital assault.
Throne instead takes the southern plains route and attacks the adjacent capital
while the real expedition is away at Frostmere. Capturing that capital ends the
campaign without fighting its remaining five expedition troops.

Both casualties expose mistakes in the agent's tactics: overlapping Guard attacks
kill Westwatch's Militia; moving the Throne Sapper out of cover allows two Guards
and a Wolf to kill it. Both outcomes remain recorded. The final army retains
Adept, Skyrider, Militia and Acolyte, with 61 gold, three crystals and six mana.
Channeling 2 and Restoration 1 were earned; Channeling 3 was never offered. No
retreat, recovery expedition, alternate simulation or rewind was used.

After `Game.close()`, source **75c2b60** exactly replays every original command,
forecast, currency delta and saved state into a separately attributed derived
journal. Its native continuation passes **2,403 inputs and 556 actual F5/F9
joins**, averaging **25.24% of one CPU core** over 193.74 seconds. The historical
opening is loaded, not replayed through native controls. The later **325c5c5** map
UI change has separate verification and is not the source of this full replay.

This supplies the previously missing complete directed Control continuation.
Other directed builds, counter-scenarios, independent player understanding,
capital recovery and optimal or comparative balance remain unproven.
**G04 and all G01–G19 remain incomplete.**
