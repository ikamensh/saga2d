# Shared campaign army encounters — 2026-09-08

Backend source **9d6a8ea6ef2e1a5a14fec916ce191f4256a44872**, using the
alternating battle kernel from **96eb221**. This advances the
[concurrent campaign scope](../../simultaneous-campaign-pvp.md) through model
and real loopback TCP tests. It is not a selectable PvP mode.

The socket journey buys a Barracks and Swordsman for each realm (90 gold each),
then wins actual neighboring conquests through public PvE autoplay orders.
Seat 1 spends one action to wait while seat 0 fights for the central province;
that challenge changes neither the incumbent realm nor the challenger's gold.
The central conquest pays 25 gold and offers the incumbent's earned skill.
Only after that choice does the shared human battle begin.

Both client views show the same battle. Human Guard and End turn orders update
both realm revisions. Both sockets close, the complete authority is written to
JSON, a new authority is reconstructed during the defender's turn, and new
sockets reconnect. The defender then guards and retreats: the winner enters
the contested province, the loser returns to its capital and pays up to 20
gold, both action allowances remain spent, and the encounter claim clears.
This is an authority-object restart within one test process, not a dedicated
server process restart. Human combat here is manually commanded by the test;
the preparatory PvE conquests use the existing optional autoplay control.

Model regressions also cover two active PvE battles, waiting withdrawal without
refund, stale/unauthorized orders, Ready reopening, actual army consequences,
capital victory and settlement of finished versus unfinished PvE on capital
loss. The kernel checks exercise separate spell pools, both hero-death
directions, paid veteran/source-ID preservation, actual casualties, status
lifetimes and exact restore/trace behavior.

Two new corrupted-checkpoint cases first failed: restore accepted an unrelated
waiting destination and the unsupported shared outcome `victory`. Both now
reject those checkpoints. An earned continuation additionally verifies that a
valid choice-only wait at an incumbent's departed origin still restores and
enters its originally paid destination without another action charge.

## Retained checks

| Receipt | Result | Scope |
| --- | --- | --- |
| [Network](concurrent-armies-network.log) | 2 passed, 0.93 s | Earlier development loopback run |
| [Restore RED](concurrent-armies-restore-red.log) | 2 failed, 22 deselected, 0.38 s | Both malformed checkpoints were wrongly accepted |
| [Restore GREEN](concurrent-armies-restore-green.log) | 2 passed, 22 deselected, 0.24 s | Narrow validator fixes |
| [Departed-origin choice](concurrent-armies-choice-wait.log) | 1 passed, 24 deselected, 0.07 s | Valid continuation remains loadable |
| [Final selection](concurrent-armies-stable.log) | **146 passed, 3.76 s** | Both concurrent files, duel and seven solo compatibility files |

The final run measured 3.809033375 seconds wall and 0.960655 seconds CPU, about
25.22% of one core, using a cooperative 25% allowance. Pacing occurs between
test cases and within the paid preparation/socket helpers; it is not an
instantaneous CPU limit or a battery measurement. Jobs ran serially and exited.
The final 146 includes the targeted cases above; the rows are not additive.

[receipt.json](receipt.json) retains the exact selections, timing and source
scope. [source-files.git.txt](source-files.git.txt) lists committed Git blob IDs
for the backend, kernel and selected tests at 9d6a8ea. Earlier logs describe
intermediate revisions; the final run validates the committed backend unit.
[SHA256SUMS](SHA256SUMS) covers all retained files except itself. Logs are exact
copies of the named `/tmp/concurrent-armies*.log` originals.

This selection is not a full suite or human playtest. Campaign screens, the
new mode's server catalog, dedicated-server restart, native PvP and a refreshed
package remain unfinished. Existing selectable multiplayer is co-op; the
preserved Mac build predates this source. **G01–G19 remain incomplete.**
