# Guard and Pikeman Brace

Stage-one rules and evidence at source
`d2c51d11e9031d48e9ae3df81d6fd5b5bd01925b`. These are Shardbound rules;
Saga2D received no combat abstraction or other changes in this increment.
The larger target remains [the tactics design](eador-tactics-design.md).

## Public orders and consequences

`Battle.guard(unit_id)` spends a living player's remaining movement and
action. It rejects an already-used action, enemy selection, a fallen unit
or an ended battle without changing state. Moving before the order is legal.

- Ordinary combatants enter `stance='guard'`: +2 defense until their next
  team turn begins. `BattleUnit.effective_defense` exposes that armor before
  terrain cover; the base `defense` field never changes.
- A Pikeman enters `stance='brace'` instead, with no armor bonus. The first
  adjacent attacker whose attack range is one receives a normal spear hit
  **before** its attack. A lethal spear stops the attack entirely. The hit
  consumes both Brace and the ordinary retaliation allowance.
- While Brace is waiting, it replaces ordinary retaliation. Ranged attacks,
  including point-blank shots, take no defensive hit and leave the spear
  ready for the first melee attack. Thus ranged contact cannot draw one
  retaliation and leave another spear reaction available afterward.
- Brace expires at the Pikeman's next team turn. It is a pre-attack reaction;
  effects preventing ordinary retaliation do not prevent the spear hit.

`Battle.preview(attacker_id, target_id)` remains an exact, nonmutating pair:
target HP loss and attacker HP loss. The latter can be a spear pre-hit or
ordinary retaliation. Preview and execution share the ordered calculation,
including either participant dying. Both teams use the same damage rules.

The fifth recruit is appended after the existing four: Pikeman, 40 gold,
2 upkeep, Barracks required, 28 HP, 9 attack, 3 defense, movement 2, range 1.
It trades speed and sustained durability for melee defense. Automatic
Pikemen advance and Brace when no attack is available; existing combatants'
automatic decisions retain their prior behavior.

## Saves and verification

Schema 4 saves each combatant's stance. Versions 1–3 migrate existing units
with no stance; unknown stances, Brace on another unit kind, and player
stances that did not spend an order are rejected at load. Captured v2 and
v3 active-battle fixtures retain their exact subsequent results.

At the named source:

- Full suite: **466 passed**. Twenty-nine new cases include Guard's armor
  and action cost, both-team expiry, saved orders, lethal spear hits,
  multiple attackers, ranged counters and mixed hero-free clashes.
- **1,000 mixed Guard/Brace clashes**, seeds 0–999, passed distinct living
  positions, health bounds, bounded outcomes and exact saved continuations
  on three terrains. See the [recorded clash report](evidence/shardbound-guard-clashes-2026-09-06.json).
- **100 random campaigns and 20 scene runs** passed, including 10,008 random
  input activations, 2,588 paired battle rounds and 24,220 state checks.
  Source fingerprints stayed unchanged during the run. See the
  [recorded campaign/input report](evidence/shardbound-guard-stress-2026-09-06.json).
- Independent review compared 100 actual prior-v3 battle snapshots across
  25 seeds and four heroes with their full v4 continuations, including
  campaign rewards/choices: every field matched except the schema tag.
  Additional played approaches covered retaliation immunity and lethal
  spears. The ranged-contact double reaction found by review was fixed
  before the final checks above.
- The default Tribes stress driver also passed 60 AI games and 20 random
  scene runs before the final game-only reaction correction.

Reproduce the suite with `uv run python -m pytest tests -q`, the campaign
stress with `uv run python tools/fuzz_eador.py --campaigns 100 --scenes 20
--events 10000 --steps 160 --report /tmp/guard-stress.json`, and the clash
matrix by calling the public scenario
`test_mixed_defensive_orders_preserve_hero_free_clash_rules_and_saved_continuation`
from `tests/eador/test_guard.py` for seeds 0–999.

These reports establish bounded rule/save/input reliability at the named
source. UI integration and native visual verification are separate later
work; these results do not prove release readiness or broad army balance.
The older real-backend soak remains tied to its archived `31a2c88` source.
