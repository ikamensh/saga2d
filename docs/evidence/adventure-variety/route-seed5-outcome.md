# Seed 5: declared Caravan → guided Courier route

The declared fresh Commander/Standard route reached its reward endpoint on
turn 3 with one campaign action remaining. All six troops survived. The Courier
ended by evacuation in round 2: Warden Swap delivered the unspent Commander to
the southern exit while the enemy Pikeman and Archer remained alive. Veil Censer
was kept unequipped; Moonstone remained equipped. Final treasury: **112g/10c**.

## Actual route and stop

| Attempt | Turn | Terminal round | Result |
| --- | --- | --- | --- |
| Westwatch Shrine | 1 | 2 | Rout; Moonstone kept/equipped |
| Briarwood conquest | 1 | 2 | Rout; Tactician 1 selected |
| Briarwood Caravan | 2 | 2 | Rout; Merchant Seal kept |
| Greenwater conquest | 2 | 2 | Rout; all six purchased/starting troops retained |
| Greenwater Courier, guided | 3 | 2 | Escape; 50g/2c and Veil Censer; Tactician 2 selected |

There were seven actual enemy phases across these five battles. The two
campaign end-turns were mandatory action refills, not elective recovery.
Neither hero nor Warden crossed the declared half-health recovery threshold.
No defeat, retreat, campaign retry, rewind, alternate seed, autoplay or injected
army/resource change occurred. Play stopped after the final reward choice,
before the T5 bound and without completing the linked campaign.

The two rests advanced the rival's attack countdown from 3 → 2 → 1 and its
treasury from 60g → 81g → 102g. Its six troops remained at Blackfen; no
interception occurred. Those timing consequences remain in the journal.

## Actual ledger

Command numbers below are one-based positions in `route-seed5.json.gz`.

| Command | Event | Gold change | Treasury after |
| --- | --- | ---: | ---: |
| Start | Fresh campaign | — | 100g / 4c |
| 1 | Barracks | −45 | 55g / 4c |
| 2 | Warden | −55 | 0g / 4c |
| 18 | Shrine reward | +45 | 45g / 6c |
| 33 | Briarwood reward | +25 | 70g / 6c |
| 35 | First mandatory rest, after upkeep | +18 | 88g / 7c |
| 53 | Caravan reward | +65 | 153g / 7c |
| 56 | Swordsman, Merchant Seal equipped | −34 | 119g / 7c |
| 57 | Archery Range | −55 | 64g / 7c |
| 58 | Archer, Merchant Seal equipped | −27 | 37g / 7c |
| 86 | Greenwater reward | +25 | 62g / 7c |
| 87 | Second mandatory rest, after upkeep | +20 | 82g / 8c |
| 88 | Guided Courier entry fee | −20 | 62g / 8c |
| 105 | Courier reward | +50 | 112g / 10c |

Buildings cost 100g, recruits 116g and guided entry 20g: **236g spent**.
Battle rewards provided 210g/4c; net rest income provided 38g/2c.
Thus `100 + 210 + 38 − 236 = 112g`, and `4 + 4 + 2 = 10c`.
The Seal saved 19g on the two later recruits (34g/27g versus 45g/35g).
The actual schedule and purchase balances match the declared forecasts.

## Wounds and tactical decisions

The army took 37 health damage during battle commands. Moonstone Heal restored
11 health to Militia 1 at command 61 for 4 mana; mandatory rests restored 15
army health. Eleven wounds remained at the endpoint. All six troops are level 2:
Militia 1 **22/28**, Militia 2 **28/28**, Archer 3 **24/24**, Warden 4 **42/42**,
Swordsman 5 **35/38**, Archer 6 **22/24**. The Commander reached level 3 with
Tactician 2, **44/44 health and 14/14 mana**.

Pin prevented the lone Briarwood Brigand reaching the line in its first phase.
In Greenwater, forest blocked immediate shots; guarded advances, a later
Archer reposition and protected melee finishes cleared the conquest. In the
Courier, the veteran Archer pinned the Pike from its safe starting tile, the
Swordsman screened the northern approach, and Warden/Militia/Commander removed
the southern Brigand. At command 103 (`commands[102].after`), Swap had placed
the unspent carrier on `(3,0)` and evacuation was legal. Command 104 escaped
with enemy Pike **18/28** and Archer **20/20** still alive.

One input error is retained: after command 4, Warden occupancy invalidated the
Archer's previously inspected route to `(1,1)`. The move was rejected with exact
state unchanged. Updated reachability was inspected and a different legal move
was played; the failed input and reason were not removed from history.

## Provenance and limits

The journal contains **107 successful explicit public commands**, their reasons,
before/after saves and one rejected move. Execution began at
`37a4e6056196f13ef125664ddd1c4601ee0719f8`; later integration commits changed
neither the authenticated game/framework source nor the director. Every
continuation checked those hashes. Commands through 74 ran in the exclusively
held slot; all later director invocations used the shared OS-lock wrapper, so
seed 12 could reason independently while actual model processes remained serial.
Each director process used `CpuBudget(25)`.

Fresh linked-campaign initial SHA256:
`4066862f3c5060dffc2962f512d707acabb18bd18d698f11a77ce42045453a60`.
It exactly matched the retained zero-order predecessor. Final journal SHA256:
`cdccd3ef5ae9750098d371b6c31de7c97196aaa4091c2b7f56bebe564ccda846`.

This is one declared agent-directed public-command route. No native input replay
or visual/human-playtest credit is claimed by this record. It demonstrates the
earned local discount/equipment/extraction sequence, not optimal play, a full
campaign result, isolated causality versus other seed differences, or broad
strategic balance. Any later native replay needs its own receipt.
