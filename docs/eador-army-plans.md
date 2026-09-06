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

## First serial pilots

One Standard seed-7 Foundries→Throne attempt per plan completed all three shards.
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
