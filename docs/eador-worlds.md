# Three themed shards: model checkpoint

This increment adds three materially different province policies while retaining
Shardbound's compact 19-province topology, fixed capitals and one default
challenge level. **G02 remains partial:** these are not three map sizes, three
difficulty settings or evidence of long-term strategic balance.

## Public boundary and ownership

```python
state = State.new(seed=7, hero_class='Commander', theme='elderwild')
state.theme  # 'frontier', 'elderwild' or 'ruins'
```

`eador.worldgen.THEMES` supplies frozen `ThemeSpec(name, description)` records.
`worldgen.generate(seed, theme)` owns the game-specific map policy;
`State.new` creates the hero and finite rival as before. Saga2D gains no opponent,
content registry or strategic world-generation abstraction. Its existing
`HexGrid` supplies coordinates, adjacency and routes.

The generator was extracted first with 100 entire default campaign snapshots
unchanged. A fixed pool of the six original random site IDs prevents adding an
authored encounter from consuming a different sequence of random draws. Border
Watch is then placed deliberately away from the starting Shrine. Frontier retains
the familiar seed-7 opening and original generated data except that authored site.

## Practical differences

| Theme | Direct approach | Flank opportunity |
| --- | --- | --- |
| Frontier | Mixed terrain and outlaws, then armoured eastern guards | Seeded sites and resources; familiar tutorial |
| Elderwild | Lower-income forest/marsh interior with wolf packs and goblins | A seeded northern or southern dry road: plains, fewer central guards, richer gold income and merchant relics |
| Ruins | Short, lucrative checkpoints guarded by Pikemen and archers, with recurring crystal production | A seeded weaker flank offers cheaper fights, an early merchant charter and a Tower's Ember Lens before the final garrison |

Each themed shard has one Border Watch on a neutral edge opposite its favoured
flank. Its hold encounter uses the authored tactical layout; ordinary province
conquests continue to use the theme's terrain. Forest/marsh movement, ranged fire,
Brace and relic effects use existing game rules. There are no invisible terrain
bonuses or generated combat formulas.

## Saved campaigns

Schema **v6** records `theme`. Versions 1–5 migrate explicitly to the Frontier
label, keeping their serialized province arrays, progress, choices, rival and
active battles. Loading never regenerates a map. The retained v5 Watch fixture
verifies the province data and active objective remain exactly equal, then
continues combat through reward resolution. Unknown theme IDs and unsupported
versions fail through `SaveFormatError`.

## Measured route choices

Source checkpoint: `4b0e3e2`, after merging main's hold and sound/settings work.
The [route report](evidence/shardbound-worlds-routes-2026-09-06.json) retains
per-campaign observations and source SHA-256 fingerprints. Reproduce with:

```sh
uv run python tools/audit_eador_worlds.py --seeds 20 --output /tmp/world-routes.json
```

The shared public-command policy explores itinerary sites, builds a Barracks and
Swordsman, invests in recovery, intercepts an approaching rival and refills before
Duskspire. It chooses the first skill option, keeps the first relic in combat and
uses a recovered Merchant Seal when recruiting. Tactical battles use the explicit
automatic command. All **720 campaigns won**: 20 seeds × 4 classes × 3 themes ×
3 itineraries. Winning is checked independently of the route's speed or cost.

Means across 80 campaigns per row:

| Theme / route | Final turn | Soldiers lost | Recruitment gold | Final gold | Net battle HP lost | Mana spent | Extra recovery turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frontier / direct | 12.09 | 3.65 | 141.74 | 462.32 | 285.32 | 44.85 | 1.71 |
| Frontier / north | 14.84 | 3.26 | 144.66 | 624.20 | 324.05 | 58.10 | 3.67 |
| Frontier / south | 15.31 | 2.62 | 115.81 | 801.21 | 298.74 | 54.11 | 2.66 |
| Elderwild / direct | 12.06 | 2.39 | 151.51 | 375.59 | 249.11 | 46.84 | 1.81 |
| Elderwild / north | 15.41 | 1.77 | 138.10 | 699.56 | 285.71 | 64.45 | 4.21 |
| Elderwild / south | 15.29 | 1.05 | 114.16 | 867.42 | 246.90 | 57.89 | 2.71 |
| Ruins / direct | 11.43 | 2.08 | 138.75 | 563.12 | 232.28 | 43.88 | 1.18 |
| Ruins / north | 13.89 | 1.46 | 116.30 | 598.70 | 258.60 | 55.26 | 2.79 |
| Ruins / south | 14.55 | 0.99 | 105.49 | 825.05 | 225.69 | 45.84 | 1.93 |

The direct road is faster. The flanks preserve more veterans and generally
reduce replacement spending, but add encounters and can require more total mana
and healing. Final gold includes the extra turns' income; it is not profit per
turn. Net battle HP lost is measured after tactical healing and before campaign
advancement; it includes dead soldiers and is not total incoming damage. Extra
recovery turns count final-approach rests for wounds/mana, not every end turn.
North/south aggregates mix the seeded favourable flanks and retain the fixed
rival's geographic asymmetry. This policy is not an optimal strategy, and these
results do not prove that every route is equally attractive to a human player.

## Validation

- `uv run pytest -q`: **608 passed** at the source checkpoint.
- 100 seeds per theme: connected/reachable capitals, valid content and rosters,
  deterministic save roundtrips, more than 90 distinct generated maps, and both
  northern/southern favourable flanks present.
- **4,800 actual opening battles:** all four classes across 100 seeds and three
  themes can win the home adventure and each adjacent conquest after the starting
  Barracks/Swordsman purchase.
- Public seeded campaign tests retain the older tutorial, retreat, defense,
  neglect/defeat and save behavior, and add all class/theme/route combinations.

The [random stress report](evidence/shardbound-worlds-stress-2026-09-06.json)
retains **300 model campaigns (100 per theme), 35,608 state checks, 6,608 paired
battle rounds, 1,528 saved choice continuations and 9,172 unchanged rejected
commands**, with no failures. Twenty current UI runs produced **10,007 random
input activations** and passed their save/backup, replay and battle-continuation
checks. Those UI runs use the existing Frontier title flow; the model runs cover
all themes. Random play naturally loses: 97 defeats and three victories occurred
before cleanup; forced cleanup finished the remaining 200 runs. These are
invariant checks, separate from the deliberately competent 720 winning journeys.
All recorded source fingerprints still matched after the runs.

The title/CLI theme picker and its native visual verification belong to the UI
integration checkpoint. This model report makes no claim that those controls
already exist, nor that G02 or the Early Access criteria are complete.

## Playable selection — 2026-09-06

The title offers all three worlds with their route tradeoffs and a terrain
illustration. Left/Right cycles worlds, Tab cycles heroes, and mouse buttons
provide the same choices. `--theme`/`--hero` preselect the title or start directly
with `--seed`. The active map and results name the saved theme, and Save & title
retains it for the next selection. Loading restores the recorded world even
after choosing a different title theme.

Three public-input integration journeys cover that selection/save/load path.
The native verifier `tools/verify_eador_themes.py` exercises the same paths and
captures all theme titles/maps at the shipping 1280×800 logical canvas, displayed
in 1280×720 and 1280×800 windows. This verifies letterboxing, not arbitrary
logical layouts or text scaling. A 720-pixel *logical* campaign layout was also
inspected and exposed overlapping lower sidebar controls; that layout remains
unsupported and must be addressed before claiming arbitrary UI scaling.
