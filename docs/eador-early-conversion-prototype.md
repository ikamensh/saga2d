# Earlier control-army investment: an executed negative comparison

The proposed Sapper/Adept/Skyrider conversion is **not a worthwhile general
investment for this immediate Duskspire assault** in the bounded plans tested.
It costs real money, veteran development and actions, but the retained army performs
better. Its failure does not establish that those roles are useless: the same
control party has existing paid manual Watch demonstrations, and the converted
party handles the smaller returning expedition with fewer wounds here.

This narrows the [resource-breakpoint diagnosis](eador-resource-breakpoints.md).
The base policy is not merely forgetting to buy an obviously stronger army.
Money can constrain a multi-role purchase, yet there is no demonstrated reason
to make that purchase for this objective. Changing income or adding a fee would
not create that missing tactical value. No production economy, AI, combat rule,
profile or schema changed.

## Exact earned starting point

The retained seed-0 Standard Commander Frontier state is turn **6**, one step from
Duskspire: **144 gold / 21 crystals / one action**, hero **44/44 HP, 6/14 mana**.
Barracks, Market and Temple are already built; Moonstone is equipped.

| Existing troop | Rank / XP | Current / maximum HP |
|---|---:|---:|
| Militia 1 | 3 / 0 | 18 / 32 |
| Militia 2 | 3 / 0 | 16 / 32 |
| Archer 3 | 3 / 0 | 28 / 28 |
| Swordsman 4 | 2 / 9 | 36 / 38 |
| Swordsman 5 | 2 / 3 | 38 / 38 |
| Swordsman 6 | 2 / 0 | 38 / 38 |

The finite rival is at `(0,-1)`, returning toward `(1,-1)` with one turn remaining.
Its soldiers are Guards at **21/42 and 5/42 HP**, plus an Archer at **20/20**.
Duskspire separately has five 42-HP Guards and two Archers. This is a rout objective,
not a seal or extraction route that intrinsically needs mobility/control.

The main conversion preserves the original Militia/Archer core of the existing
control demonstration. It permanently retires Swordsmen 4, 5 and 6 for:

- Sapper: **42 gold / 1 crystal / one replacement action**, fresh rank 1, 26 HP;
- Tower plus Adept: **121 gold / 4 crystals / one replacement action**, fresh rank
  1, 28 HP; the Tower costs 75/2 and itself takes no action;
- Skyrider: **60 gold / 3 crystals / one replacement action**, fresh rank 1, 28 HP.

Total **223 gold / 8 crystals / three actions**, with no refunds, free XP, troop
injection or reserve pool. Sapper and Adept replace the same upkeep as the retired
Swordsmen; Skyrider adds one upkeep. Every actual quote and retirement is retained.

## Funding and the returning rival

Staged buying gets Sapper and Tower on turn 6, Adept on turn 7, and Skyrider on
turn **9**, with **20 gold / 22 crystals / one action** left. Three ordinary turns
provided 99 gold after upkeep. The rival has reached Duskspire but has not yet paid
for recovery. The converted army beats the wounded expedition there in two rounds,
with no troop deaths and 17 total missing HP. Its Sapper actually uses Smoke.

That last recruitment action matters: the expedition consumes the remaining action,
so the garrison assault waits until turn **10**. With automatic tactics it loses
that battle, leaving only Militia 2 at 5 HP. Five combat troops die, in addition to
the three earlier permanent retirements.

Waiting until all 223 gold is present before purchasing is worse here. Two
replacement actions fit on turn 9; the third requires turn **10**. The rival's real
paid recovery has now restored both Guards to 42 HP, costing its treasury 58 gold.
The full party takes four rounds and loses Sapper and Skyrider against that expedition,
then loses the garrison assault on turn **11**. This is actual finite recovery and
paid force persistence, not a free turn-based respawn.

## Retained-party and retirement controls

The following use the explicit automatic combat command. “Deaths” counts combat
troops; it does not include retired troops. A failed assault leaves the campaign
playing with real wounded survivors/defenders; it is not a lost-capital result.

| Plan | Additional purchases | First capital result | Combat deaths |
|---|---:|---|---:|
| Keep party, attack now | 0 | Win turn 6 | 4 |
| Keep party, rest once | 0 | Win turn 7 | 4 |
| Keep party, Tower, attack now | 75 gold / 2 crystals | Win turn 6 | 4 |
| Keep party, Tower, rest once | 75 / 2 | Failed assault turn 7 | 6 |
| Replace Sword with Sapper | 42 / 1 | Failed assault turn 7 | 6 |
| Replace Sword with Adept + Tower | 121 / 4 | Failed assault turn 7 | 6 |
| Replace Sword with Skyrider | 60 / 3 | Failed assault turn 7 | 6 |
| Staged full conversion | 223 / 8 | Failed assault turn 10 | 5 |
| Keep party until turn 9 | 0 | Win turn 9 | 3 |
| Keep party + Tower until turn 9 | 75 / 2 | Win turn 9 | 3 |
| Keep party + Tower; also wait after interception | 75 / 2 | Win turn 10 | 2 |
| Fund the whole conversion first | 223 / 8 | Failed assault turn 11 | 6 |

The last retained-party control fights the expedition on turn 9 and the garrison
on turn 10, matching the staged conversion's battle dates. It therefore does not
benefit from an earlier procedural battlefield or avoiding the returned expedition.
It ends with four surviving troops, hero **36/44 HP**, and 68 missing HP across
living combatants. The conversion fails on that same garrison date.

The retirement alternative was also tested. Replacing **Militia 1** instead of a
Swordsman with Sapper or Adept still loses the turn-7 assault. Skyrider succeeds,
but with five deaths versus the unchanged party's four. A full conversion that
retains two Swordsmen—replacing Militia 1, Archer 3 and Sword 6—still loses on turn
10. It pays the same prices, but its changed upkeep, retired ranks and actual
starting positions are recorded. The negative result is not supported solely by
discarding all armoured troops.

There is a modest positive magical investment: Tower followed by immediate turn-6
assault retains the same two Swordsmen as the no-purchase victory, while the hero
finishes at **14 HP instead of 2**. Both spend their tactical mana down to 2. This
costs 75 gold and 2 crystals, no retirement or extra campaign action. It is a
specific improvement, not a blanket claim that buying Tower always helps.

## Tactical limits and an actual paid retry

Waiting changes the real seeded battlefield terrain as well as healing, mana and
rival position. Same-date comparisons above preserve that fact. A Tower adds Bolt
to the automatic player's choices, so it can change the policy's attacks and mana
allocation; the failed Tower/rest result must not be described as “more mana hurts”
in isolation.

Four bounded tactical controls use explicit hero orders that reserve mana for a
useful Heal, otherwise approach/attack in melee, then delegate remaining troops to
the ordinary automatic command. This is not an optimized manual solver. It does not
rescue the full conversion or individual Adept. The retained Tower party still wins
turn 9 but loses four troops; the simple Heal-first policy is not uniformly better.
Complete public orders, saved phase replays and used ability charges are retained.
Full conversion uses Smoke in both battles; an individual Adept uses Repulse.
No indispensable Skyrider crossing or optimal Smoke/Repulse targeting is claimed.

The failed staged conversion is also recoverable without injected resources. From
its actual turn-10 aftermath, the conventional policy buys five normal Swordsmen
for **160 additional gold**, rests to the existing HP/mana reserve, and retries.
It defeats the rival's newly **paid** single Guard on turn 13, then the persistent
wounded garrison on turn **14**. The garrison still contains the first attempt's
surviving Guards at **21, 8 and 27 HP**, and an Archer at 20. The final Militia dies;
five purchased Swordsmen survive, all now rank 2. Ending treasury is **89 gold /
37 crystals**, hero 48 HP and 12 mana.

That whole path costs **383 gold / 8 crystals**, three retired veterans and six
combat deaths. The conversion's special roles have all been lost, and the recovered
army is conventional again. This is a viable paid recovery, not evidence that the
conversion was a good investment. Separate three-turn no-purchase aftermaths are
retained for failed assaults, exposing rival recovery/recruitment; they are not
guarantees of future safety.

## Decision and reproduction

Do not use this bundle's 79-gold initial shortfall as a reason to restrict income
or force late purchases. The price competes for money and actions, but the bundle
has not earned a useful place in this immediate rout plan. Test specialist demand
against an appropriate authored objective before changing resource supply. Existing
successful role-specific encounters remain valid; neither a guaranteed global role
ranking nor a new economy feature follows from this single saved window.

Source **e81949a**, [tool](../tools/prototype_eador_early_conversion.py),
[complete compressed evidence](evidence/early-conversion-prototype.json.gz).
Twenty bounded branches and the paid retry repeat exactly. Every tactical phase
replays its actual public commands from a saved starting state, and every rejected
replacement leaves its full state unchanged. All 26 recorded source hashes stayed
fixed. There are no production changes and no native conversion workflow claim.

```sh
uv run python tools/prototype_eador_early_conversion.py
```
