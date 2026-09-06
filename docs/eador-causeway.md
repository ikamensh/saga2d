# Runebound Causeway

The Causeway is an optional Ruins extraction site with one free assembly.
Its cargo slows the hero by one move; reach the northeastern exit with an
unspent hero action and no adjacent enemy, then Evacuate by the end of round
five. Routing the defenders also wins. Hero death loses immediately.

This authored pattern combines caster priority with a timed carrier advance.
It deliberately reuses existing Repulse, Guard/Brace, occupancy, ranged combat,
Heal and Swap rules. The Rune Adept can push an exposed hero away from the exit
once. Finishing it early commits three attack orders and accepts retaliation;
Guard spends the carrier's order; filling its push landing delays a useful
Militia. The Scout instead takes an oblique ranged approach with a smaller
party. These are measured alternatives, not mandatory counters or a claim that
this pattern invents a new tactical mechanic.

No new Battle command, AI behavior, save schema or framework API was needed.
The game-owned duplicate-source helper now serves two concrete callers:
Frontier Relief and Ruins Causeway. `SiteSpec.inherited_reward` lets Codex quote
the actual saved source for either encounter, including an honest absence on
worlds without it. Saga2D continues to own measured text/layout and input.

## Earned choices

All figures below use actual Standard seed-seven Ruins travel, purchases and
public manual orders. Preparation battles use the ordinary automatic policy;
the site itself is played manually. No unit, experience, currency or mana is
injected. All allies survive these examples. This is a reproducible comparison,
not an optimal-play or all-difficulty success claim.

Commander buys Barracks, Warden, Temple, discounted Acolyte and Mage Tower for
279 gold and two crystals. At the first healthy arrival it is turn nine, hero
level three, with the original two Militia/Archer, paid Warden/Acolyte and ten
mana. Scout buys Barracks, Warden and Tower for 175 gold and two crystals,
arriving at turn six, level three, with five total bodies and six mana.
Their earned Moonstone is equipped. Their actual travel/rival history remains
in the complete recorded campaign checkpoints.

| Commander plan | Entry turn | Additional funding | Result | Missing HP | Mana spent |
|---|---:|---|---|---:|---:|
| Focus caster | 9 | None | Escape R4 | 37 | 4 |
| Focus caster + Heal | 9 | None | Escape R4 | 15 | 8 |
| Guard | 9 | None | Escape R4 | 34 | 8 |
| Guard + Heal | 10 | One recovery turn | Escape R4 | 12 | 12 |
| Occupied landing | 10 | One recovery turn | Escape R4 | 28 | 12 |
| Occupied landing + Heal | 11 | Two recovery turns | Escape R4 | 14 | 16 |
| Guard + Heal | 9 | Tower infusion: 3 crystals, 1 hero action | Escape R4 | 12 | 12 |
| Occupied landing + Heal | 9 | Same infusion | Escape R4 | 14 | 16 |

The actual turn-nine arrival has two actions. Infusion raises ten mana to
eighteen and leaves one action for entry, without changing turn, gold or rival
state. This is an existing currency choice at an earned breakpoint, not a new
economy rule or evidence that G07 is globally solved. Recovery instead advances
income/upkeep and the finite rival. Guard+Heal buys three fewer wounds than
focus+Heal for four more mana. The occupied-landing line has different early
orders but is relatively expensive for this particular army.

The Guard healing line uses the forward Militia to finish the Ranger in round
four, freeing the Acolyte to heal. All Commander escapes use Warden Swap to
put an unspent carrier on the exit. Guard, attacks and spells would prevent
that carrier from evacuating if used in the same turn.

| Scout plan | Earned entry | Result | Missing HP | Mana spent |
|---|---|---|---:|---:|
| Ranged flank, immediate escape | T6, level 3, 6 mana | Escape R4 | 41 | 4 |
| Recover, then heal at the exit | T8, level 4, 8 mana | Rout R4 | 19 | 8 |

Scout has no Acolyte and does not need Swap. Its later recovery includes a real
rival interception and level gain; this is not the same level-three party with
mana edited upward. Casting its own Heal spends its evacuation action and
accepts another enemy phase. The remaining Guard dies to retaliation, producing
rout instead of escape. The [earlier earned audit](eador-causeway-placement.md)
also compares both lines from the same fully recovered level-four snapshot.

## Finite failure and persistence

The failed example exposes the carrier to an actual Repulse, kills the Adept,
then deliberately Guards until the round-five deadline. It is a retained
failure/retry test, not a claim the push makes defeat unavoidable. No allied
unit dies. The normal retreat fee is 20 gold; no partial-kill XP, choice or
reward is granted. The source keeps exactly Pikeman 28 HP, Ranger 22 HP and
Dread Guard 28 HP. The dead Adept does not reappear.

The same party recovers through ordinary commands and retries at turn eleven.
It manually routs those three survivors in round three, spending twelve mana
and ending with nine missing HP. The recorded reward is paid once. Repeated
explore/resolve attempts cannot repeat it, and every manual order round-trips
the complete State. The native journey additionally checkpoints with actual
F5/F9 input before entry, through the active battle/result, after retreat and
after settlement.

A real pre-Causeway Shrine battle and result were captured at source
`c1797d11bd85ca055c74bdc9b40fb0af2d7f3edc`. Loading and continuing that older
world remains byte-exact, including its original Shrine identity, guard battle,
level progression and reward. New-world generation changes only future sites;
it does not regenerate a loaded world or a saved recovery entry.

## Safe source placement

A new Ruins world replaces one ordinary duplicate, inheriting its exact saved
gold/crystal/relic reward. The unchanged witness must have the same ordinary
kind and reward, no larger defender multiset, and a location no farther east.
Only the selected site's name/kind and finite guard kind/HP arrays change.
Conquest guards, economy, terrain, ownership and every other province remain
exact. The ordinary witness preserves the cheaper reward encounter, not merely
the ability to obtain the same relic behind this harder battle.

The guarantee is structural: before placement, Ruins has nine ordinary sites
at nonnegative q among only Tower, Barrow and Shrine. Reserving the direct
Crown Barrow `(1,0)` still leaves eight cells and three kinds. Ordered duplicate
selection supplies a same-or-smaller ordinary roster; it fails clearly if later
content breaks this condition. Authored sites and negative q are excluded,
protecting home Shrine, Den, Explorer's Camp, Vault, Observatory, western
fallback, Watch and Aerie. Frontier/Relief and Elderwild generation stay exact.

The retained prechange 1,000-seed audit supplies full selected/witness records
and whole-world hashes. Production restores only the four intended fields and
matches each original whole-world hash, while checking the witness unchanged.
Seed seven chooses Shrine `(0,1)`, inheriting 45 gold, two crystals and Moonstone;
home Shrine remains the ordinary witness. Conquering or crossing this province
does not force site entry. The source's reward is shown from its saved data in
briefing and Codex.

## Reproduction and verification

```sh
uv run python tools/audit_eador_causeway.py --output /tmp/causeway-production.json.gz
uv run pytest -q tests/eador/test_causeway.py tests/eador/test_causeway_scene.py
caffeinate -u -t 1
uv run python tools/verify_eador_causeway.py --plan infused-guard --output /tmp/causeway-native
uv run python tools/verify_eador_guidance.py --matrix --output /tmp/causeway-guidance
```

The native verifier supports `focus`, `guard`, `backstop`, `infused-guard`,
`scout`, `scout-heal` and `failed-retry`. Its preparation uses actual campaign
input; its manual orders compare forecasts and full state against the public
model. It inspects both 100% and 125% text, actual source reward and conditional
caster guidance. The complete briefing matrix includes fresh and wounded
Causeway preparations at all supported window sizes.

Native verification found a real retry-only overflow: three surviving defender
kinds use three rows, whereas the fresh four-kind list uses two paired rows.
Removing redundant retry prose alone did not help because the map preview
already determined that row's height. Shortening the approach sentence kept all
cargo/exit information while freeing a measured line above the preview. The
public native failed/retry verifier is the reproducer; mock font metrics alone
did not catch it. Fresh and reduced-roster large-text screenshots were inspected.

The prototype and copied-placement tools were absorbed into production helpers
and deleted. Their compressed historical evidence and exact source revisions
remain linked from the proposal documents. Passing this tranche supplies an
additional authored pattern toward G05; neither the pattern count nor these
scripted journeys establish fun, first-time comprehensibility, or release
readiness. Independent human playtesting and the other release gates remain.

## Retained final evidence

All final local checks below use frozen source
`1a20e5451a9940f59993d6575db6a84b98c7033b`, Python 3.13.2 on
macOS 26.6.2 arm64. Documentation/evidence were the only files edited during
these final runs. The check record matches 329 source/config/fixture files
against that Git revision; native dependencies separately match all 86
recorded source hashes. This is revision-specific evidence.

- [Model audit](evidence/causeway-production-2026-09-06.json.gz): twelve manual
  plans with 482 exact tactical order/reloads, 185 campaign preparation
  checkpoints plus three retry recovery checkpoints, and 1,000 original-world
  witness/hash comparisons. It includes actual infusion and finite reward
  settlement. Its 82 source hashes match the recorded revision.
- [Native input and guidance](evidence/causeway-native-2026-09-06.json.gz):
  seven paid plans, 1,645 input actions and 93 exact F5/F9 reloads. The full
  guidance run covers 228 approach views across all 20 current layout entries
  at 1280×720, 1280×800 and 1920×1080, plus six Guide/Observatory views and
  persisted text-size restart. Layout entries are not authored-family counts.
- [Random stability](evidence/causeway-fuzz-2026-09-06.json.gz): 300 campaigns
  (100 per theme), 20 scene runs and 10,009 random inputs, with unchanged
  source hashes. These random policies eventually lose; this is stability
  evidence, not a victory-rate or balance claim.
- [Full/cross-game checks](evidence/causeway-checks-2026-09-06.json.gz):
  1,188 tests passed in 405.21 seconds; 40 Tribes AI games and 40 monkey runs
  passed with no failures.
- [Independent acceptance](evidence/causeway-independent-2026-09-06.md) and
  [public-command replay](evidence/causeway-independent-2026-09-06.json.gz):
  3,000 complete worlds compared with pre-Causeway generation, 806 exact
  save/reloads, paid routes and live/dead-Adept retries; no actionable issue.
  A surviving Adept's per-battle charge refreshes on a later attempt, while
  its wounds persist. The dead-Adept retry does not recreate it.

Inspected examples: [fresh large-text briefing](evidence/causeway-2026-09-06/causeway-briefing-125.png),
[three-survivor retry](evidence/causeway-2026-09-06/causeway-retry-125.png),
[recorded reward](evidence/causeway-2026-09-06/causeway-codex-125.png),
[paid infusion](evidence/causeway-2026-09-06/causeway-infusion.png),
[Guard](evidence/causeway-2026-09-06/causeway-guard.png),
[occupied landing](evidence/causeway-2026-09-06/causeway-occupied-landing.png),
[Scout flank](evidence/causeway-2026-09-06/causeway-scout-flank.png),
[Heal](evidence/causeway-2026-09-06/causeway-heal-forecast.png),
[Swap](evidence/causeway-2026-09-06/causeway-swap-forecast.png),
[deadline](evidence/causeway-2026-09-06/causeway-deadline.png), and
[Scout's rout](evidence/causeway-2026-09-06/causeway-scout-rout.png).
