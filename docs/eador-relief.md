# Relief Column: earned campaign integration

Relief is the eleventh authored encounter pattern, using existing hold, Rally,
flight, Pin and Repulse rules. It adds two free assemblies and a conditional
Frontier source. This is **11/12 content coverage, not G05 completion** or a
new combat subsystem. The [original and revised proposal](eador-eleventh-encounter-proposal.md)
retains the rejected corner geometry and its counterexamples; the results
below are actual production campaigns, not detached prototype battles.

## Placement preserves the ordinary alternative

New Frontier worlds replace one eastern ordinary site's identity and guards
only when an unchanged site at an equal or more western column has the same
site kind, exactly the same gold/crystal/relic reward, and no additional guard
kinds or counts. The selected source keeps its original reward, terrain,
province guards, ownership and income. The ordinary witness stays exact. The
four new site guards are Skyrider, Militia, Archer and Dread Guard; eastern
placement does not add a fifth Guard.

The 1,000 retained pre-integration selected/witness pairs all pass. Seed 7
changes Heartwood `(0,0)` from Grove to Relief while keeping the identical
ordinary Grove reward at Stonecross `(0,1)`: 35 gold, 3 crystals, Oak Standard.
Seed 2 selects the Barrow at `(0,1)` and leaves the same ordinary Barrow reward
at `(-2,1)`: 55 gold, 1 crystal, Iron Crown. Its sole central Tower stays a
Tower. Fixed and fallback sites remain outside selection; Elderwild and Ruins
are unchanged. This is reward-access preservation, not a claim that every
travel path takes the same time.

The Codex reads the generated/saved province's reward, and gives an explicit
absence message in worlds without Relief. The current attempt retains its
saved reward precedence. A real pre-Relief earned Grove battle at seed 7's
replaced source still loads and resolves to its byte-exact old complete State.
There is no schema bump or regeneration on load. Old replay fixtures compare
current newly generated province arrays only; frozen rules and all other
recorded fields remain exact.

## Paid plans and their tradeoffs

Standard seed 7 Commander arrives at turn 9 after 317 gold and 4 crystals of
actual purchases: Market, Barracks, Pikeman, Warden, Mage Tower and Rune Adept.
The hero and six troops have earned their advancement through the ordinary
journey. Scout arrives at turn 5 after 235 gold for Market, Barracks, Pikeman,
Archery Range and Archer; the hero and five troops form the smaller party.
Both retain the original two Militia and Archer. Costs include those buildings
and recruits, but are not presented as total campaign income or upkeep.

| Same earned party where indicated | Result | Missing HP | Mana spent |
|---|---|---:|---:|
| Commander: forward, finish support, Heal | Hold round 2 | 28 | 8 |
| Commander: western, receive landing, Repulse, Heal | Hold round 4 | 28 | 12 |
| Commander: occupy every landing cell, Guard | Hold round 2 | 40 | 0 |
| Scout: fresh Archer Pins, veteran finishes support | Hold round 2 | 44 | 0 |

Every arriving combatant survives these four plans, and defenders remain
alive after the hold. The active Commander plan trades eight mana for twelve
fewer total wounds than passive closure. It does not improve every soldier:
its Pikeman has 22/32 HP rather than the passive plan's 32/32, and its Adept is
14/32 in both. Western leaves that Adept full but distributes 28 wounds among
the Pike, Militia and Warden. It costs two more phases and four more mana;
there is no equal-efficiency claim. The paid passive solution is deliberate,
not omitted to imply that Rally suppression is universally required.

The public development preparation responds to visible rival attacks when
their targets reach a capital-neighbor province. A version that chased every
nearby expedition lost an original Militia in Challenge seed 7; waiting until
the capital itself was targeted was too late in Challenge seed 2. The retained
policy purchases and recovers while responding to that earlier visible threat.
No rival timer, difficulty rule, starting resource, army or XP was edited.
The results demonstrate viable routes, not an optimal provisioning policy.

Across Accessible, Standard and current Challenge, seeds 0, 2, 7, 11 and 29,
all 60 versions of these plans hold and preserve every arriving unit. All
1,740 tactical orders reload the entire saved State exactly. Arrival stats and
wounds vary with earned progression: western wounds are 25–28, passive 37–40,
Scout 42–44. This bounds the demonstrated classes and seeds; it is not an
all-class or difficulty-balance result.

## Failure and finite retry

In the actual Standard seed 7 forward deployment, omitting the Adept's final
support hit leaves the enemy Militia at 2 HP. It Rallies the pinned Skyrider;
the flyer lands beside the seal and the first scoring phase is lost. Guarding
thereafter loses by the round-four deadline and kills veteran Pikeman ID 4.
Resolution takes the ordinary 20-gold loss, with no reward or victory XP.

The saved site retains only an Archer at 20/20 HP and Dread Guard at 36/42 HP.
A normal 28-gold Pikeman purchase produces a fresh ID with level 1 and zero XP;
the veteran and defeated enemies stay gone. The changed western briefing lists
only those survivors and their 56/62 total HP, without dead-support advice.
Three **explicit automatic rounds** then rout that finite wounded roster. This
retry is not claimed as a manual tactical plan. The inherited 35 gold,
3 crystals and Oak Standard are resolved once; later exploration/resolution
orders reject without changing the saved State.

## Verification and reproduction

Source `c6093de` includes the integrated `ef9a67f` HUD. The retained
[evidence directory](evidence/relief-c6093de/README.md) contains exact source
hashes, 60 paid model plans and their complete order snapshots, the failed
attempt and paid retry, seven native reports/final saves and inspected images.

All seven native journeys use actual Title, travel, purchase, briefing,
selection, targeting, tactical order, save/reload, resolution and reward inputs:
Standard forward/western/Scout/passive/failed retry, Accessible seed 2 forward,
and Challenge seed 7 forward. Together they pass 1,202 input activations and
71 exact save/reloads. Both assemblies and the actual reduced-roster retry were
read at 100% and 125%; native images were inspected, including the variable
Crown Codex, first lost scoring phase, western displacement and passive result.

The five native Standard plans also run as mock input integration tests. The
existing advancement and complete-game input journeys take the preserved
ordinary Grove at `(0,1)` after explicitly declining the optional Relief at
`(0,0)`; their advancement, victory and saved-continuation assertions remain.

```sh
uv run pytest -q
uv run python tools/audit_eador_relief.py --output /tmp/relief.json.gz
uv run python tools/verify_eador_relief.py --plan forward
uv run python tools/verify_eador_relief.py --plan western
uv run python tools/verify_eador_relief.py --plan scout
uv run python tools/verify_eador_relief.py --plan passive
uv run python tools/verify_eador_relief.py --plan failed-retry
uv run python tools/verify_eador_relief.py --mode accessible --seed 2
uv run python tools/verify_eador_relief.py --mode challenge
uv run python tools/fuzz_eador.py --campaigns 300 --scenes 20 --events 10000
uv run python tools/fuzz_eador.py --linked --campaigns 60 --scenes 0
uv run python tools/fuzz.py
```

The historical prototype's source-selection probe describes the pre-integration
world at `4608d1e`; use that revision to reproduce its candidate search. The
production audit and tests above are the current-world reproduction path.
