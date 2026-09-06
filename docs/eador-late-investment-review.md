# Late investment: bounded review and replacement experiment

**Recommendation:** an optional, explicit role change is worth a small interface
review. It is not an economy repair. Normal incoming recruitment price plus one
hero action can exchange a veteran for a fresh specialist; retirement permanently
loses the outgoing troop and its rank/XP. Keep ordinary recruitment and passive rest
unchanged. No replacement command, reserve, refund, garrison purchase, income
revision or new upkeep rule has been added to the game by this experiment.

## What is actually scarce

The retained paid seed-0 Standard Commander / Frontier / Economy army reaches
turn 11 at Cinderwood `(1,0)` with six troops, 421 gold, 37 crystals and two actions.
It already owns Barracks, Marketplace and Temple. Ordinary public purchases of
Archery and Mage Tower cost 130 gold / 2 crystals, leaving **291 gold / 35 crystals
and all five buildings**. These purchases also raise mana from 6/14 to 10/18;
the tactical comparisons below account for that actual benefit.

At its current Quartermaster discount, one each of Pikeman, Warden, Ranger,
Sapper, Adept and Skyrider costs 250 gold / 6 crystals. That entire hypothetical
basket is affordable. Actual recruitment still rejects **“Your army is full.”**
without changing the save. Roster capacity, veteran commitment and available
travel actions constrain this state more than money does. Waiting once after
the two buildings increases the treasury from 291 to 332 gold after upkeep.

An observation of this same complete paid route reproduces the ordinary policy's
final result exactly. Its gold ledger is:

| Source or expense | Gold |
|---|---:|
| Starting funds | 100 |
| Income after ordinary troop upkeep | +370 |
| Site / conquest / interception rewards | +185 / +100 / +25 |
| Buildings | −170 |
| Recruits | −123 |
| Final treasury, victory on turn 12 | **487** |

This route is not rich at every point: buying Temple on turn 3 leaves **2 gold**.
A global income reduction would affect a real opening commitment. Conversely,
small late fees would not address passive income exceeding the entire building
and recruitment bill in this example. These are one route's accounting and real
saved decisions, not a claim that every mode or player has the same economy.

## Three possible follow-ups

| Option | Useful decision | Why it can fail / evidence needed |
|---|---|---|
| **Atomic camp replacement — preferred small scope** | Give up a named veteran and one travel action to buy a different role at the normal price. The slot is available immediately, without deliberately sacrificing a soldier in battle. | It enables role access; it does not make abundant gold scarce. Test exact retirement/quote/save behavior and a manual specialist order, with keeping and ordinary resting as controls. Do not turn it into repeated cheap healing or claim it is a recurring economic sink. |
| **Finite province defenders — defer** | Invest outside the hero's full roster so the expedition can explore instead of intercepting every threat. Use purchased finite soldiers with lasting wounds, never free respawns. | Larger rule change: current rival movement fights province guards only when the hero is absent; when present it launches hero defense directly. Simply adding garrisons would ignore the paid defenders in that battle. Combined deployment and rival route prediction also need design. Must prove defense is not weaker with the hero present and that it cannot restore safe income farming. |
| **Separately versioned late-income revision — defer** | Change the source of excess income instead of adding routine clicks or fees. Investigate marginal province income and rewards after the opening. | No new tactical option by itself, and broad balance risk. The turn-3 two-gold commitment argues against an opportunistic global cut. Start with a cash-flow comparison of a few actual paid openings and late investments, then matched validation. Preserve existing frozen difficulty IDs and saved world values. No tuning numbers are proposed here. |

Additional stat buildings would mostly postpone the same full-roster problem.
Arbitrary fees on existing travel, spells or recruiting would create upkeep or
clicks without establishing a new investment decision.

## Executed replacement prototype

The tool changes only a cloned, validated save for the proposed operation. It
retires troop 1, inserts a new level-1 / XP-0 troop at the same formation index,
allocates a fresh ID, pays the ordinary discounted gold/crystal cost, and spends
one hero action. No funds, experience or bodies are returned. Every later build,
wait, travel, tactical round and reward uses the game's public commands.

All **19 local branches** compare saves after every tactical round with an
uninterrupted duplicate; final states, round logs and unit states match exactly.
The initial terrain, objective and defending party also match between same-turn
branches, apart from enemy IDs shifted by the new player ID. These are explicit
automatic tactical policies, not manual acceptance scenarios or optimal play.

### Same assault after purchasing all five buildings

The outgoing Militia is healthy, **rank 3 / XP 6**, with 32 HP, 11 attack,
3 defense and Rally. The new Pikeman has 28 HP / 10 attack / 3 defense and Brace;
the new Warden has 38 HP / 9 attack / 4 defense and Swap. Both are slower. These
are recorded battle stats, including Commander bonuses, not invented upgrades.

| Preparation before Duskspire | Price; actions | Victory turn | Battle deaths + retired | Surviving army wounds | Hero HP | Gold / crystals left |
|---|---|---:|---:|---:|---:|---:|
| Keep veteran, attack now | 0; 0 | 11 | 4 + 0 | 31 | 34 | 316 / 35 |
| Keep veteran, rest once | 0; end turn | 12 | 2 + 0 | 51 | 34 | 357 / 38 |
| Fresh Pikeman, attack | 28g; 1 | 11 | 2 + 1 | 79 | 46 | 288 / 35 |
| Fresh Warden, attack | 39g; 1 | 11 | 2 + 1 | 107 | 32 | 277 / 35 |
| Fresh Skyrider, attack | 60g + 3c; 1 | 11 | 3 + 1 | 66 | 36 | 256 / 32 |
| Fresh Militia control, attack | 14g; 1 | 11 | 3 + 1 | 101 | 42 | 302 / 35 |

Retirement counts separately from combat deaths: the Pikeman and Warden options
remove **three** original roster members in total. Wound totals count survivors
only; losing more bodies can make that number look deceptively small.

The Warden actually uses Swap on a Swordsman. The Pikeman issues Brace twice,
but no pre-hit reaction is logged, so the casualty change is not proof of a
Brace-only effect. Target selection, formation occupancy and the fresh identity
also affect automatic tactics. The Skyrider does not outperform both cheaper
specialists here. Replacing a healthy veteran with another Militia does not
reduce total roster exits; this is not a universally better fresh-body purchase.

The original three-building input and both replacement-plus-rest options remain
in the report as controls. Before Tower, fresh Militia loses five in battle plus
the retired veteran, versus four battle deaths when keeping the veteran. Keeping
and resting loses only two. A replacement can permit an earlier different army;
it does not remove the case for free recovery or make every role appropriate.

### Pursuit: spending the last action has a consequence

The second retained paid state is Accessible Commander, turn 6 at `(1,0)`, with
one action and 172 gold / 23 crystals. The rival will attack Heartwood in one turn.

| Choice | Interception turn | Battle deaths + retired | Army wounds | Ending gold / crystals |
|---|---:|---:|---:|---:|
| Keep, intercept immediately | 6 | 1 + 0 | 18 | 197 / 23 |
| Keep, rest, intercept | 7 | 0 + 0 | 19 | 230 / 26 |
| Fresh Warden, forced wait, intercept | 7 | 0 + 1 | 15 | 190 / 26 |

Both waiting branches let the rival seize Heartwood before the interception;
winning subsequently recaptures it. No permanent territory loss is claimed.
Replacement pays 39 gold plus one additional ordinary upkeep gold during the
wait, gives up the veteran, and produces four fewer survivor wounds than resting
alone. The Warden uses no Swap in this encounter. This is a weak purchase, not a
reason to replace after every battle. The last-action cost must be visible.

## Decision boundary and retained evidence

The evidence supports reviewing one optional role-change command with an exact
outgoing/incoming quote. It does **not** establish G07 completion, broadly balanced
late income, a recurring gold sink, or manual player enjoyment. Production should
wait for a UI that shows the retired identity, rank/XP and HP, fresh replacement,
normal price, action cost and changed upkeep before the player commits.

Run `uv run python tools/prototype_eador_army_replacement.py` to reproduce the
observed ledger, ordinary full-army rejection and local comparisons. The
[source](../tools/prototype_eador_army_replacement.py) and
[report](evidence/army-replacement-prototype.json.gz) retain input provenance, all
orders, intermediate rival ownership, battle logs, exact results and source hashes.
The original [paid saves](evidence/crystal-service-comparison.examples.json) are
unchanged. Prototype code remains only as a reproducible experiment while the
production interface is under review; it is not imported by the game.
