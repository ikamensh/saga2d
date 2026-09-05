# Linked campaign model: v8 checkpoint

The three-shard model is implemented; this document records its model evidence.
Native UI journeys, human play duration and decision quality still gate G01 and
Early Access acceptance. The accepted [decision](linked-campaign-decision.md)
explains the chosen limits and remaining balance risks.

## Public play and persistence

`State.new_campaign(seed, hero_class)` starts Frontier's Westwatch. Existing
travel, build, recruit, tactical and reward commands play the active shard.
`state.campaign.phase` is `playing`, `departure`, `recovery`, `completed` or `lost`;
`state.status` remains the local shard result. Pending battles and rewards must
finish before a departure or final ending.

`advance(offer_id, troop_ids=(), relic_ids=())` selects one of two saved offers.
Rootward requires its Border Watch before Duskspire; The Foundries requires both
marked provinces when starting the assault. The last choice is an unrestricted
rout or a separately authored seal with two uncontested phases by round eight.
`encounter_at(destination, kind='conquest')` exposes the actual upcoming authored
encounter, including an expedition interception taking precedence over the gate.
`assault_blocked_reason` explains an unmet contract without spending an action.

A transition keeps hero choices and up to two surviving troops and two relics,
refills the levy to three troops, and heals travelers. Hero rank caps are 3/4/5;
troops cap at 3. Local buildings reset. Starting gold is 100 plus at most 40
exported gold; crystals are 4 plus at most 2 exported crystals. Local Mage Tower
mana is recomputed rather than accumulated.

The first capital loss offers `recover(...)` or `abandon_campaign()`. Recovery
spends the run's one retry, keeps current knowledge and selected survivors, and
restores the recorded entry world with 60 gold and two crystals. The failed
attempt's turns and deaths remain in its eventual shard record. A second loss
ends the run. Entry checkpoints contain only province and initial rival records;
past shards retain bounded summaries, not nested live states.

Schema v8 stores linked metadata and validates phase, stage, contracts, rank
caps, offers, history and entry checkpoints. Versions 1–7 remain standalone with
their recorded worlds and active combat unchanged. Rootward's required Watch
must exist in both current and recovery maps; deleting either is a load error.
The final ritual's target, deadline and required phases are validated explicitly.
Rejected transition selections leave the entire current save unchanged.

## Executable acceptance evidence

At `8b95b58`, the complete suite passed **697 tests**, including **45 linked
campaign tests**. They execute actual three-shard victories across every class
and offered contract, save/restart at transitions and active objectives, loss,
recovery and second loss, foundry capture/loss/recapture, rejected selections,
corrupt saves, and an actual pre-v8 combat fixture with exact continuation.

The [retained route report](evidence/shardbound-linked-routes-2026-09-06.json)
contains **880/880 completed campaigns**: seeds 0–49, four heroes, two middle
contracts and two finales (800 runs), plus 80 runs that lose stage two, reload,
recover and finish. The economic policy uses public commands and explicit
tactical autoplay. Source fingerprints cover every game module and the policy.

| No-recovery stage | Runs | Mean turns (range) | Mean deaths |
| --- | ---: | ---: | ---: |
| Westwatch | 800 | 12.01 (9–20) | 3.73 |
| Rootward | 400 | 14.63 (11–25) | 1.24 |
| The Foundries | 400 | 12.74 (11–19) | 0.90 |
| Break the Throne | 400 | 10.90 (8–15) | 0.51 |
| Seal the Gate | 400 | 10.85 (8–16) | 0.36 |

Complete normal runs averaged **36.57 turns (29–53)**; recovery runs averaged
**48.46 (39–68)**, including the failed attempt. Rank caps were reached in all
stages for this policy. These are strategy-turn counts, not measured human play
time. A competent recovery remains viable despite its lower budget. The final
stage's low deaths indicate meaningful inherited strength; they do not establish
that its tactical choice is balanced across every skill/relic build.

The manual final-seal journeys verify holding independently from rout. A
Commander uses seven bodies to screen the seal and guards for two phases.
Warrior, Scout and Wizard instead purchase two Archers, rotate the rear veteran
on round two, Pin both approaching flank Guards, and Heal the exposed Archer.
Each wins by holding at round two with **all defenders and player troops alive**;
the smaller-army journeys save at progress one and again after victory. Guarding
only the starting deployment reaches deadline failure with a living hero and
returns to a recoverable campaign position. No unit stats or layout were changed
to produce these demonstrations.

The [randomized linked report](evidence/shardbound-linked-stress-2026-09-06.json)
starts 100 runs in each stage through real prior-shard victories. Across 300
prefixes it checked **39,372 states**, **6,873 paired saved combat rounds**,
**1,265 saved reward choices**, **100 saved recovery transitions**, and **9,331
rejected ordinary commands** for unchanged state. It also exercised 97 accepted
and 1,792 rejected Pin orders. All source fingerprints remained unchanged.
These random prefixes mostly remain in progress; forced cleanup is recorded
separately and must not be interpreted as the random policy's win/loss rate.
A seed-222 cleanup regression was fixed in the driver: it now leaves a defended
capital by a safe flank instead of repeatedly challenging the same expedition.
No game rule changed for that fix.

After merging the current CampaignScene, input reload seam and display/settings
work at `29325df`, **721 full tests** passed. The integrated linked smoke passed
12 model runs plus 12 scene runs with 2,010 random input activations, including
CampaignScene and recovery. The unchanged second-client check also passed 60
Tribes AI games and 20 monkey runs. These checks complement the larger retained
model reports; the UI owner's native-chain evidence is recorded separately in
[eador-linked-ui.md](eador-linked-ui.md).

## Scope still to assess

The capped retinue prevents importing a finished economy, but it does not prove
equal value for every troop/relic selection. The route policy prefers trained
Swordsmen, healing and two familiar relics; wider build comparison remains useful.
The foundry requirement causes observable recapture pressure, while its extra
travel may still feel repetitive. Repeating a successful screen can also reduce
the final seal's challenge after it is learned. Three contract-bearing stages
are a coherent compact run; native input, human pacing and decision evaluation
remain necessary before marking G01 complete.
