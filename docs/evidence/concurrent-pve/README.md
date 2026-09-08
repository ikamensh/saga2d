# Independent campaign PvE encounters — 2026-09-08

Source **2d53ca3**, following shared-rule extraction **724f14f**.
The development-only `ConcurrentCampaign` can now run two ordinary PvE battles
at the same time on one shared province map. Each realm spends its own actions
and currencies, receives its own wounds/rewards/choices, and has its own command
revision. This advances the [simultaneous campaign plan](../../simultaneous-campaign-pvp.md);
it is not yet a selectable human PvP mode.

## Observed behavior

The first new integration test failed because exploration was an unknown order,
then passed with both site battles active. Manual Guard and End turn orders
change only the acting realm's battle. A packet prepared before an unrelated
peer order still applies. Trusted checkpoint restoration preserves both battles
and their next commands exactly.

A second earned journey buys both armies, captures adjacent provinces and
contests the central province. The second arrival is refused without any State
change. The first army inflicts real wounds then retreats; the next army meets
the actual survivors. The province pays its conquest reward once. The waiting
player receives no income while the winner's earned skill choice is unresolved;
after that choice and both Ready orders, exactly one new day begins.

Four malformed-checkpoint regressions initially failed to reject missing,
orphaned or wrong-owner claims and a realm marked Ready with an active battle.
Restoration now requires each claim to match one valid battle context. Valid
two-battle and pending-choice checkpoints retain exact continuation.

The real TCP journey connects `MatchHost` and `MatchClient` on loopback,
submits independent exploration and manual battle orders, closes both sockets,
writes a trusted checkpoint, reconstructs the authority and reconnects new
sockets. Both players then finish their sites through the existing optional
autoplay control, accept separate relic rewards and cross the Ready barrier.
The peer snapshot contains its own private realm and only the documented public
opponent fields. Duplicate result acceptance and premature Ready orders fail
without changing the authority.

## Shared code and verification

`Realm.apply_battle_progression`, `Realm.reward_site` and
`persist_province_defenders` are used by both solo and concurrent campaigns.
Solo rival/capital/linked-campaign transitions remain in `State`. The game-local
`invoke_order` shares argument and content validation with the existing co-op
adapter. Saga2D's interface and all rendering are unchanged.

**119 compatibility checks pass** in 7.86 seconds (7.92 seconds measured wall /
1.94 seconds CPU at the 25% per-test allowance). These include real paid hold,
escape and failed-retry cases, saved survivor wounds, economy, progression and
a linked victory. The exact selection is retained in `compatibility.log`.

**14 integration checks pass** in 2.09 seconds: the concurrent model/socket
tests, existing co-op commands/scenes, dedicated co-op server behavior and its
process-restart journey. After the final readability cleanup, all **eight
concurrent cases pass again**. Initial RED outputs and final results are retained.
Jobs ran serially and exited. Socket tests close both connections in `finally`;
no native windows were started for this model-only change.

Reproduce the concurrent checks with:

```sh
uv run --locked --isolated --python 3.13.2 --extra dev python -m pytest tests/eador/test_concurrent_campaign.py tests/eador/test_concurrent_network.py -q
```

The loopback test reconstructs the concurrent authority within its test
process; it does not establish dedicated-server process restart for this new
mode. The dedicated process test covers existing co-op. Native simultaneous
presentation, pending human conflicts, human tactical PvP, the new mode's
server catalog integration and victory/loss handling remain unimplemented.
Opponent encounters are explicitly rejected before spending an action until
that work is ready. The preserved Mac package predates this increment.
All overall Early Access gates remain incomplete.
