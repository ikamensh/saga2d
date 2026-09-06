# Sealed Vault: a paid exit and its campaign consequences

The existing two-crystal exit produces a useful local campaign benefit in this
earned example: earlier province income and a surviving veteran. No game rule,
price, reward, world, troop or framework interface changed. This is one Standard
seed-seven Commander comparison, not general balance or a completed release gate.

## Same entry, two ordinary continuations

The actual paid Warden/Ranger preparation reaches the Vault on **turn 5 with
131 gold, 17 crystals and two actions**. The five troops are two Militia, an
Archer, a Warden and a Ranger. Moonstone is equipped; Barracks and Archery are
built. Neither a Tower nor Merchant Seal is owned. Both alternatives resume the
same complete saved state and use the existing manual Vault routes.

After the real reward and first offered advancement/relic choices, both follow
one disclosed policy: capture production at Broken Checkpoint `(0,0)`, leaving
its Aerie adventure unexplored, then observe the first executed rival operation
after capture. Before elective recovery, intercept an imminent attack on owned
land if the expedition's current position is reachable with remaining actions.
Otherwise recover until each living combatant is missing at most six HP and the
hero holds one Heal's actual mana cost. Restore only missing entry-roster roles
at ordinary prices; buy no additional building or unused army slot. Later battles
use explicit autoplay. Every command reloads its exact complete saved result.

| Measured result | Free crossfire | Paid southern exit |
|---|---:|---:|
| Vault escape | R4 | R2 |
| Wounds / mana spent inside Vault | 58 / 4 | 13 / 0 |
| Production province captured | T8 | T6 |
| Actual interception | T7, R3 | T7, R2 |
| Troops killed in the interception | One rank-2 Militia | None |
| Replacement purchases | 14 gold | None |
| Observation endpoint | T11 | T11 |
| Final gold / crystals | 461 / 48 | 499 / 50 |

The earlier conquest changes the next battle's army. Paid reaches the T7
interception with rank-3 Militia, Archer and Warden. Free intercepts before that
conquest, losing Militia 2 at rank 2 with 9 XP; that soldier entered the battle
at its full 28 HP. Its fresh replacement is rank 1 and has 3 XP at the endpoint,
while the paid branch retains the original soldier at rank 3 with 3 XP. The
casualty difference includes this earned progression and resulting tactics,
rather than isolating wounds left by the Vault. Both heroes have full mana
before the interception; both spend eight mana across the three measured fights.

## Where the benefit comes from

Both branches receive the same Vault and two battle rewards. Paid collects
**24 more gold and four more crystals** because the central province produces
12 gold and two crystals on two earlier end turns. Avoiding the **14-gold**
replacement raises the gold advantage to **38**; paying the **two-crystal**
entry fee leaves a net crystal advantage of **two**.

The replacement price comes from earned **Quartermaster rank 2**, with Moonstone
still equipped. No Merchant Seal discount, sale, extra site reward or refund is
involved. Ordinary net income totals 234 gold / 30 crystals for free and
258 gold / 34 crystals for paid. These actual flows reconcile the final balances.

The endpoint includes deliberate observation waits. Both advance six campaign
turns: free has two recovery waits, one action refill and three observation waits;
paid has one recovery wait and five observation waits. Both preempt the threatened
attack by intercepting on T7. Consequently the next executed operation is the
rival's actual **45-gold Dread Guard recruitment on T11**, after its replacement
delay. Its final army, treasury, position and announced plan match exactly.

Thus the result demonstrates earlier capture, income and veteran preservation.
It does not demonstrate two fewer total campaign turns or that waiting through
the rival's rebuild is the best next plan. Seventeen starting crystals establish
affordability, not a competing purchase blocked by the fee. The recovery threshold,
manual routes and subsequent autoplay can all affect the outcome.

## Evidence and reproduction

The [complete report](evidence/vault-continuation-32f354c.json.gz), reproduced on
source **32f354c**, retains the
new-game preparation, identical entry, all public commands and saved states,
before/after battle rosters, XP, fees, rewards, replacement purchases and the
reason and actual income/healing for every end turn. Source hashes and runtime
identity distinguish this continuation from the older
[native Vault evidence](eador-vault.md). No native continuation or human-playtest
coverage is claimed by this source/model experiment.

```sh
uv run python tools/audit_eador_vault_continuation.py --output /tmp/vault-continuation.json.gz
```

The default CPU allowance is 25% of one core. Each branch permits at most 24
post-Vault campaign orders, separately from tactical rounds and reward resolution.
An unfinished attempt is retained at its actual bound, without cleanup turns or
forced victory. The comparison adds no broader seed or strategy matrix; G07
remains open.
