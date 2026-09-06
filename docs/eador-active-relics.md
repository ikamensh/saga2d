# Twelve relics: earned model evidence

The four active relics reuse existing tactical commands. One equipped slot remains
the constraint: equipping one gives up the other relic's income, movement, armor,
spell access or active order. Powers are assigned when a new battle is created;
equipment cannot change during combat. The numerical twelve-item floor is met,
but these journeys do not establish finished equipment balance or complete G04.

| New relic | Discoverable source | Existing order and cost |
|---|---|---|
| Veil Censer | Frontier Courier's Crossing, (0, 2) | One Smoke charge; spends hero movement/action and blocks friendly fire and spells too. |
| Porter's Rune | Elderwild Supply Cache, (-1, -1) | One Repulse charge; adjacent target, empty landing, no Guard/Brace anchoring. Spends hero movement/action. |
| Mirror Badge | Ruins Sealed Vault, (-1, 1) | Swap an adjacent ally. Hero spends its action; both spend movement. The ally keeps only its existing unspent action. |
| Vanguard Drum | Frontier Muster Yard, (-1, 1) | Rally an adjacent Pinned ally. Hero spends movement/action; only Pin is cleared, with no extra order or healing. |

The existing eight remain Moonstone, Ember Lens, Oak Standard, Iron Crown,
Merchant Seal, Wayfarer Boots, Storm Quiver and Watch Bell. Muster Yard is a
procedural rout relic source; it is **not** another authored pattern for G05.
Every new relic sells for 45 gold; its value is still a balance hypothesis.

## Public earned journeys

`tools/eador_relic_campaign.py` uses ordinary purchases, travel, combat, rewards,
equipment and linked departures. No inventory, treasury, XP or troop injection
prepares these journeys. `tests/eador/test_active_relics.py` reloads after every
manual order and validates final campaign resolution.

- **Censer:** a purchased Warden/Acolyte army completes the actual guided Crossing
  escape, keeps the reward and later buys a Ranger for Border Watch. Smoke over
  the Archer's approach wins the hold on round 3 with all allies and a defender
  alive. Guard from the same starting save also wins on round 3. The screen saves
  **one HP after the first enemy phase**; subsequent healing equalizes final HP.
  A different screen chosen from that earned save blocks the Acolyte's legal Heal.
  This proves a small positional benefit and a friendly-fire cost, not dominance.
- **Rune:** complete stage one, choose Rootward, earn Cache's reward, and carry it
  with Moonstone into the Ruins Gate. A Warden delivers the hero to a rear seal
  contester; Repulse changes only the living defender's position, and a reserve
  closes the gap. The recovered formation wins by hold on round 5 with every
  ally alive. A complete opening ring is faster, winning on round 2 without the
  Rune. This is a deliberately delayed formation's recovery, not an optimal route
  or a speed advantage. The displaced Guard can die to later ordinary retaliation.
- **Badge:** choose Foundries, earn Vault's reward, and carry it with Moonstone
  into the Elderwild Gate. The hero swaps a wounded Archer off the seal; its
  unspent shot remains usable. The formation holds on round 2 with all allies
  and all seven defenders alive. The exchanged hex remains flankable: the Archer
  is 26/28 HP before the swap and 16 HP after the next enemy phase. Moving a holder
  is not automatically a health-saving rescue. A separate earned Cache journey
  delivers the hero to an uncontested exit with its own Swap: evacuation refuses
  unchanged because the action was spent, then succeeds after the next phase.
- **Drum:** a purchased Warden/Ranger army earns Muster Yard's reward, enters
  Watch, and takes a real Archer Pin. Rally restores a forest approach that was
  unreachable while Pinned; the Ranger moves and uses its already-unspent shot.
  The helper intentionally stops there. Explicit automatic continuation wins by
  **rout on round 3**, not by holding. Guarding that Ranger before Rally proves
  the spent movement/action are not refreshed.

The Rune and Badge source battles use the explicit automatic combat command;
their later Gate orders are manual. Each linked departure carries at most two
troops and exactly two owned relics. Separate anchored/occupied Repulse counter
fixtures derive from an earned battle but deliberately alter the enemy stance or
position; they are legality tests, not additional naturally played encounters.
The old troop-level tests continue to cover board edges and Brace anchoring.

## Source and save protection

`RelicSpec.battle_ability` supplies the existing command ID. Battle creation uses
that metadata; save validation permits only an equipped relic's recorded hero
capability. Extra powers, mismatched equipment and spent charges without a power
are refused. No new battle fields, framework abstraction or schema bump is needed.
Schema remains v11. Recorded active ability tuples, province rewards, pending
adventure rewards and linked recovery worlds are never regenerated on load.

A genuine pre-extension v11 Crossing fixture retains its Merchant Seal reward
and finishes to the exact captured former campaign state. A saved old hero does
not gain a newly available power during its active battle.

Across 100 seeds in each theme, all four new sources and the protected home
Shrine, Watch, Den and Explorer's Camp are present. Replacing duplicate rewards
otherwise removed the last Seal from 16/100 Frontier worlds and the last Oak
from 6/100 Elderwild worlds. When the old reward is absent, the generator places
its Caravan or Grove at the available procedural (-2, 1). This bounded fallback
uses no extra random draws and never overwrites the fixed sources. Ruins retains
the Iron Crown in its Barrow. Saved worlds retain their original arrays exactly.

## Reproducible validation

- **882 full tests passed** at `f1c9f67`, including all eight active-relic tests,
  older saves, linked transitions, authored routes and framework/Tribes checks.
- **400 varied continuations** at `6a0b672`: 100 seeded policies from each of four
  publicly earned seed-7 checkpoints. The Drum starts just before responding to
  its real Pin. Every order and automatic phase validates the full campaign save;
  every terminal battle resolves identically after reload. This varies policies
  from four worlds, not 400 independently generated campaigns.
  The run checked 16,038 full campaign saves, 1,944 paired automatic phases and
  1,995 nonmutating forecasts. Explicit hero orders included 85 Smoke, 22 Repulse,
  100 Swap and 36 Rally. Outcomes included 32 deadlines and seven hero deaths;
  failed attempts were validated alongside victories.
- **300 random campaigns**, 100 per theme: 36,655 state checks, 6,711 paired
  battle rounds, 3,033 equipment commands and 8,673 rejected commands unchanged.
  Before forced cleanup, random play produced 80 defeats, one victory and 219
  ongoing games. Cleanup outcomes are separately recorded, not balance evidence.

The stress runner reuses the existing tactical command/forecast checker with an
optional earned battle and full-save checkpoint. It does not duplicate combat
rules. Both retained reports record source hashes; no measured source changed
during either run. No new native run is claimed here: root's separate input
verifier owns native equipment, departure, preview and command presentation.

```sh
uv run pytest -q
uv run python tools/stress_eador_relics.py --policies 100 --report /tmp/relic-orders.json
uv run python tools/fuzz_eador.py --campaigns 300 --scenes 0 --steps 120 --report /tmp/relic-campaigns.json
```

Raw evidence: [earned orders](evidence/relics-earned-stress.json),
[random campaigns](evidence/relics-campaign-stress.json).

These examples demonstrate reachable abilities, costs, counterplay and saved
continuation. They do not compare all twelve choices across all heroes, establish
sell-price balance or replace first-time human discovery and enjoyment checks.
