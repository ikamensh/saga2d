# Control orders, flight and sight — v11 checkpoint

The game now has ten recruitable roles and eight distinct active combat orders:
Bolt, Heal, Brace, Pin, Swap, Rally, Smoke and Repulse. Ordinary attacks, movement,
Guard and evacuation are excluded from that count. This reaches those numerical
floors; it does not establish finished tactical or economy balance.

## Rules and the game/framework seam

- Militia Rally spends the Militia's action and movement to clear an adjacent
  ally's Pin. It preserves the ally's action, movement, retaliation, stance,
  cooldown and cargo flags. A spent ally never receives another order.
- Sapper Smoke costs one charge per battle. Place one visible cloud within three
  hexes; it blocks both teams' ranged shots and spells, including shots from or
  into its hex. Self-healing still works. It expires before its caster's team's
  next phase, even if the Sapper dies. Spending it consumes action and movement.
- Rune Adept Repulse spends one charge, action and movement to push one adjacent
  enemy directly away by one hex. Guard and Brace anchor targets; board edges
  and occupied landings prohibit the order. It changes position only, and never
  automatically awards seal progress or evacuation.
- Skyrider flight crosses bodies and rough terrain at one movement per hex.
  Landings must be empty. Pin still reduces range, and Brace still reacts to a
  flying melee attack.
- Ranged attacks, Pin, Bolt and Heal need clear sight. Forest intervening between
  source and target blocks sight; endpoint forest retains its existing cover.
  The symmetric game-owned `eador.sight` helper handles hex edge cases without
  adding a tactical policy engine to Saga2D.

Sapper costs 60 gold + 1 crystal and requires Marketplace; Rune Adept costs
65 gold + 2 crystals and requires Mage Tower; Skyrider costs 85 gold + 3 crystals
and requires Temple. Their upkeep is 2, 2 and 3. The one equipped relic slot and
eight existing relics are unchanged by this increment.

Public queries are `rally_targets/rally_preview`, `smoke_targets/smoke_preview`,
`repulse_targets/repulse_preview`, `has_sight`, and the existing `reachable`.
Orders are `rally`, `smoke`, `repulse`; flight is intrinsic movement behavior.
`State.recruit_crystal_cost(kind)` complements the existing gold cost query.
Previews do not mutate the state and command validation preserves it on rejection.

The automatic policy uses Rally to restore an actual approach or escape, Repulse
to clear a seal/exit or relieve a wounded ally, and Smoke when screened enemy
fire exceeds blocked friendly shots/magic and the Sapper's immediate attack.
These support decisions precede ordinary unit order so the hero can use the
resulting route. Flying movement breaks equally useful attack-position ties by
immediate incoming damage. This is bounded game policy, not an optimal planner.

## Persistence and meaningful manual evidence

Version 11 records sight mode, cloud positions and expiry teams, and spent
charges. Existing active version 10 and older battles keep their recorded
abilities, receive open sight, and gain no Rally, Smoke, Repulse or flight.
Worlds and pending adventure rewards are never regenerated. A genuine saved
version 10 Pinned Crossing continues to exactly the captured former result.

`tools/eador_control_campaign.py` purchases all three new roles from ordinary
seed-seven Commander resources, travels and recovers, then enters Border Watch.
Its explicit formation uses Smoke on the Archer's approach, Repulse to clear the
seal, and flight across the occupied formation to close the remaining flank.
It wins by holding on round 3, with all seven allies and the defending Archer
alive. Saving after every order preserves the outcome. Paired Guard instead of
Smoke also wins, with two fewer allied HP: this particular screen is a modest
benefit, not proof that Smoke dominates ordinary defense.

The real Pinned Crossing journey uses an earned enemy Pin, moves an adjacent
Militia reserve, previews and applies Rally, and preserves the carrier's existing
order while restoring its route. Separate public tactical regressions prove
immediate evacuation after Rally/Repulse, anchored displacement rejection,
finite charges after reload, cloud lifetime after caster death, and rejected
crystal-funded recruitment without partial spending.

Clear sight required two earlier manual-route adjustments: the full-cargo Cache
Acolyte moves to a legal lane before healing; the earned Warden/Ranger Watch
arrival is turn 8 instead of 7. The original no-casualty, explicit objective,
one-time reward and saved-continuation assertions remain.

## Reproducible checkpoint evidence

Measured source: `89ad3f3`, after merging root's control UI `68803c5`. No source
hash changed during these runs. Raw reports retain commands/purchases, seeds,
revision and source hashes.

- **855 full tests passed.** Existing standalone, linked campaign, legacy-save,
  Guard/Brace, Pin, role, extraction and Vault journeys remain green.
- **1,200 mixed battle fixtures:** 7,879 paired automatic rounds, 8,918
  nonmutating forecast checks, 7,975 invariant checks, 3,554 flight moves;
  manually issued 48 Rally, 173 Repulse and 911 Smoke orders. Fixtures include
  both teams, wounded armies, hero-free clashes, hold and extraction layouts.
  Random-policy losses and deadlines are expected; no win-rate claim follows.
- **480 paid campaigns:** seeds 0–19 × three themes × four heroes × two disclosed
  purchase plans. All finished in victory, all purchased their intended roles,
  and each saved campaign validated without rewriting its world.
- **300 random campaigns and 20 scene runs:** 36,723 model-state checks, 6,646
  paired battle rounds, 8,755 rejected commands unchanged, and 10,003 random
  public inputs. Forced defeat/replay cleanup is separately counted in the
  fuzzer report. The dedicated control tool above supplies new-order coverage.
- Root's current input adapters also pass with this automatic policy on the mock
  backend: paid Watch 159 inputs / 8 exact reloads; actual Pinned carrier Rally
  106 / 4; Smoke 24 / 1; Repulse 26 / 1. A new native attempt here could not create
  a Cocoa screen. The earlier inspected native checkpoint is retained separately
  in [the control UI evidence](eador-control-ui.md), not relabeled as a native
  run of this later policy.

Reproduce with:

```sh
uv run pytest -q
uv run python tools/stress_eador_control.py --battles 1200 --campaign-seeds 20 --report /tmp/control-model.json
uv run python tools/fuzz_eador.py --campaigns 300 --scenes 20 --events 10000 --report /tmp/control-fuzz.json
```

Raw data: [control model](evidence/eador-control-model-2026-09-06.json),
[random campaign/input checks](evidence/eador-control-fuzz-2026-09-06.json).

## Balance interpretation and remaining work

These are fixed competent development policies, not optimal play or a player
study. The control plan buys Marketplace → Sapper → Mage Tower → Adept → Temple
→ Barracks. Flight buys Temple → Skyrider → Barracks → Warden. Both replace their
specialists when lost and fill spare slots with Swordsmen.

| Per campaign | Control | Flight |
|---|---:|---:|
| Victory | 240 / 240 | 240 / 240 |
| Mean turns (range) | 15.55 (9–42) | 12.03 (8–23) |
| Mean permanent troop losses | 6.89 | 5.15 |
| Mean recruitment gold | 332.12 | 272.08 |
| Building gold | 245 | 110 |
| Mean recruitment crystals | 4.94 | 5.14 |
| Building crystals | 2 | 0 |
| Mean combat mana spent | 67.28 | 41.30 |
| Runs with no battle defeat | 201 / 240 | 219 / 240 |

Crystal recruitment now imposes a real recurring cost. However, the slower,
more expensive control opening exposes weak early armies, and automatic fighting
still loses many specialists. One control run recovered from nine battle defeats
before winning on turn 42. That is real attrition and pacing debt, not evidence
of a satisfying campaign. The two plans have different building costs and do not
isolate any single unit's strength. Manual objective play, an economy matched
comparison, and first-time player observation remain necessary before declaring
G04/G07/G08 complete. Four additional relics remain a separate approved proposal.
