# Three difficulty choices

Proposal for root review, 2026-09-06. **No difficulty rules are implemented.**
Keep Standard exactly equal to the current game. Add Accessible for learning and
recovering from an expensive mistake, and Challenge for earlier investment and
interception decisions. Start with realm resources, recovery and the finite
rival's announced windows; keep tactical damage, prices, capabilities, authored
deployments and objective deadlines unchanged.

## Recommended first candidate

These values are tuning hypotheses, not measured balance conclusions.

| Rule | Accessible | Standard, current | Challenge |
|---|---:|---:|---:|
| Starting grant: gold / crystals | 130 / 6 | 100 / 4 | 90 / 2 |
| Player realm gold yield | 100% | 100% | 80% |
| Base army HP recovered per end-turn | 8 | 6 | 6 |
| Mana recovered per end-turn | 6 | 4 | 3 |
| First rival operation: first shard / later linked shard | 4 / 3 turns | 3 / 2 turns | 2 / 2 turns |
| Delay before first paid replacement after expedition destruction | 5 turns | 4 turns | 3 turns |
| One linked recovery expedition's grant: gold / crystals | 90 / 4 | 60 / 2 | 60 / 2 |

Gold yield applies once to the total effective player province plus Marketplace
income, rounded down after encirclement removes blocked production. It does not
alter province ownership, reward amounts, prices, rival revenue or upkeep.
Challenge's 20% reduction must be labeled as player realm income in the UI;
province inspection should explain how listed production contributes to that
total. Apply the same starting grant on later shard arrival, then the current
carryover caps of +40 gold / +2 crystals. Recovery uses its separate grant.

Temple, Acolyte, Oak Standard and skill HP bonuses stay additive as today; the
hero retains its current additional recovery. Encirclement blocks all recovery
and capital/Marketplace income at every difficulty. Challenge keeps today's HP
recovery because extending wounded-army waiting would amplify the current
attrition problem. Mana pacing makes spell conservation and the timing of a
recovery turn more important without changing a spell's combat effect.

The rival still pays for every replacement and healed HP at Duskspire. All
ordinary hostile operations retain their two-turn warning, all movement and
retreat routes remain visible, and no difficulty grants free upgrades or a second
expedition. Its starting treasury remains the current 60 gold, with the current
80/90 grants on linked stages two/three. Difficulty changes initial scheduling
and the post-defeat window, not an already saved treasury or countdown.

## Decisions this should change

- **Opening liquidity:** 90 gold still funds the established Barracks/Swordsman
  opening exactly, but leaves no buffer. Market-first leaves 30; Tower-first
  leaves 15. The player must earn a site reward or accept a weaker first army.
  Accessible leaves room to repair an early purchase mistake. Fewer starting
  crystals makes Tower, a paid site approach and a specialist compete earlier.
- **Expand or recover:** Challenge earns less during a rest and recovers less
  mana. Capturing a productive route, accepting some wounds or reducing spell
  expenditure can beat simply waiting. Accessible makes a cautious recovery
  affordable; the rival still eventually threatens supply.
- **Intercept or finish a detour:** the earlier first operation can interrupt
  a long opening adventure. Destroying the expedition still creates a real
  counterattack window; Challenge shortens it by one turn without restoring
  soldiers for free. Accessible permits one more turn of preparation or looting.
- **Recovery has limits:** every mode retains the one-recovery campaign rule,
  two-troop/two-relic retinue and rank caps. Accessible's larger second expedition
  can buy a frontline replacement; Challenge does not compound defeat with a
  smaller grant than today's 60 gold.

## Evidence and deliberate limits

The [v9 matched audit](eador-economy-v9.md) found Economy faster than Spells in
871/1,200 cases, while Spells lost fewer troops in 408. Sustain's early Acolyte
often cost replacements. Those are old-policy results, not current difficulty
evidence. The [v11 control/flight comparison](eador-control-model.md) found mean
6.89/5.15 troop losses and a 42-turn control outlier despite eventual victory.
Challenge should make decisions tighter, not turn that replacement loop into
its expected experience. Accessible should reduce its cost or duration.

Starting crystals alone will **not** fix the economy. V9 plans spent 0/0/2
crystals; v11 specialist plans spent about five on recruitment, plus two for the
control plan's Tower. Authored approaches now add paid alternatives, but their
effect on recurring surplus has not been measured on the combined candidate.
Do not claim G07 because Challenge begins with two crystals, or suppress crystal
production through a hidden cap. Measure actual specialist/approach purchases and
remaining stock first. A later explicit crystal-for-time purchase may be needed;
that would be a separate economy decision, not part of this difficulty tranche.

The 19-cell topology and fixed capitals also remain. Difficulty selection advances
G02 but does not by itself prove sufficiently different routes or replay value.

## Small public and persistence boundary

Use a game-owned `eador/difficulty.py` with frozen policy records and a three-entry
selection catalog. Add `difficulty='standard'` to `State.new` and
`State.new_campaign`; expose `State.difficulty` and the selected policy's title
and plain description. Existing `income`, `crystal_income` and
`upkeep_shortfall` remain authoritative. Add a small `recovery_preview()` query
for actual hero HP/mana gains, HP restored per surviving troop (up to its missing
health), and a blockade reason. Both end-turn recovery and its readout consume
that calculation. The forecast is recovery before the announced rival operation;
it does not promise the final health after a subsequent battle.

Reserve schema **v12**, subject to the current schema owner's agreement. Store
one immutable `rules_id` such as `standard-1`, `accessible-1` or `challenge-1`.
The catalog maps new-game selections to these IDs; a saved ID maps to its frozen
values. Later tuning introduces a new ID instead of changing the meaning of an
existing save. Old v11 and earlier saves migrate to `standard-1`. Unknown IDs or
future schemas fail through `SaveFormatError` before replacing a live state.
This is saved game compatibility data, not a framework rules engine.
Only these difficulty parameters are frozen by the ID. It does not promise that
every future content addition or combat correction will reproduce historical
behavior; that remains subject to the game's explicit save/version policy.

Loading never reapplies a starting grant, replans the rival, regenerates provinces
or revisits battle capabilities. Linked advance, recovery and same-run replay
must copy the existing ID rather than look up the latest selection alias.
Recovery restores its recorded entry provinces and rival, then follows its
existing explicit arrival scheduling with that same policy. The difficulty is
fixed for a run; changing the title selection affects only the next new game.
Display it in the title, map, departure/recovery brief and save metadata.

| Caller | Bounded change |
|---|---|
| `eador/model.py` | Creation selects the profile; income/end-turn and recovery preview use it; current command validation remains in force. |
| `eador/rival.py` | Initial scheduling and destruction delay read policy values. Saved live orders/treasury are untouched on load; ordinary planning remains the same. |
| `eador/campaign.py` | Advance uses profile starting grants plus existing carry caps; recovery uses its separate grant and original checkpoint. Both copy the rules ID into candidates. |
| Save validation | Migrate missing ID to `standard-1`; validate known IDs and profile-aware legal countdown bounds. Preserve all existing world, battle and finite-army checks. |
| Title, CLI and app creation | Choose a visible mode before a new run; Standard remains default. The selection cannot mutate an existing campaign. |
| Map/Hero/Rival/Campaign/Save readouts | Show saved mode, actual income, upkeep shortfall, live mana/HP recovery and explicit arrival/recovery funding. Never reproduce policy arithmetic in scene code. |
| Public input driver and verifiers | Route selection through actual title controls, and any newly introduced replay command through an explicit adapter; keep rejecting unadapted mutations. |

## Acceptance before calling the selection usable

1. Retain a genuine v11 active battle, pending reward, announced rival operation,
   linked departure and recovery save. After migration, the same public commands
   produce exactly the captured Standard results, including money, HP/mana,
   casualties, offers and rival timers. Only the new schema/ID metadata differs.
2. Generate 100 seeds per theme and difficulty; preserve connectivity, source
   guarantees, paid-opening reachability for all classes, and roundtrips. Lower
   resources must not remove access to a required linked contract or recovery.
3. Compare Economy, military/sustain and Spells across matched 100-seed sets,
   all themes/classes/difficulties. Include direct and useful flank policies;
   report purchases, crystal sinks, troop losses, desertions, recovery turns,
   intercepted operations, bankruptcy, median/tail duration and unfinished runs.
   Keep prices and combat AI fixed while isolating difficulty. Do not require
   every rigid policy to win Challenge or rename a safety-bound stop as victory.
4. Demonstrate at least one reasonable winning policy for every class/theme/mode
   and both middle/final contracts. Inspect failures and slow outliers; Accessible
   must improve a measured mistake/recovery case, and Challenge must change an
   actual purchase, route or intervention decision rather than only add waits.
5. Play visible shortfall, defense, paid refit, breakout and eventual neglect
   defeat on all modes. Save during warnings, then change the title selection and
   reload: treasury, operation timing and rule identity must remain exact.
6. Run the three selections and one linked recovery through real input with
   screenshots and restart. Reuse model scenario policies, but don't impose old
   hard-coded arrival turns or troop identities on the new difficulty cases.

Standard's existing tutorial/manual routes remain unchanged and required. Tune
only the new candidate profiles while evidence is being developed; settle their
immutable IDs before shipping saves that rely on them.
