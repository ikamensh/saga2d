# Independent counter room verification

The [example and interface guide](../../framework-match-menu.md) reuse existing
`MatchMenu`, `MatchLobby` and `OnlineClient`; no framework API or reference-game
import was added. The initial integration tracer failed on the missing demo
module (1 failure, 0.06s). The final focused check passed: **1 passed in 0.29s**
([tests.log](tests.log)), using
`.venv/bin/python -m pytest tests/framework/test_match_room_demo.py -q`.

The final native check ran serially before pytest with
`caffeinate -du .venv/bin/python /tmp/saga2d-counter-native-final-check.py`.
[verify-native.py](verify-native.py) is its exact historical script, with original
absolute paths. [verification.json.gz](verification.json.gz) records HEAD
`42aacebc45cc420dbcb459cef6d9c444c65a217a` plus the uncommitted example's exact
hash. All **46 source hashes** remained unchanged and matched before commit.
The uncompressed receipt SHA256 is
`f13ebffc7b78c9fab0ed0af87a36f7bb97336ff8a9ebbcccd5adfcdc3ae9e9ba`.

One hidden macOS pyglet window received five real input activations: Create,
Add one, Help, Escape, Space. A second loopback client added while Help covered
its counter; both seats finished at `[2, 1]`. The receipt observes transferred
lobby ownership, continued covered polling, window/session closure, peer
disconnect and stopped client workers. The authority was intentionally stopped
in cleanup (SIGTERM/-15, no traceback). No owned process/window remained.

The run used **29 frames**, **30 FPS** and **CpuBudget(25)**. Its body measured
**2.403448s wall**, **0.486124s main CPU**, **0.069117s child CPU**, approximately
**23.10% of one CPU** combined. This excludes imports, includes local authority
startup/cleanup and the Git identity child, and is not a battery benchmark.

All five captured images were individually opened. Four representative frames
are retained: [menu](final/menu.png), [counter](final/counter.png),
[Help](final/help-peer-updated.png), [returned counter](final/counter-returned.png).
The menu and lobby were readable; counter titles, counts, status and controls
were complete and in bounds. Final Help cleanly covers the background.

The [original Help image](original-help-overlap.png) exposed a status-text sliver.
Removing `transparent=True` fixed it with default opaque Scene behavior. The
[original receipt](original-verification.json.gz) preserves the first input/state
run. An initial disappearing-controls report was an image-reading error and is
retracted: the original and final returned images are byte-identical. No
framework workaround was added; all non-Help frames were unchanged.

This programmatic local check supports the independent-consumer part of G17.
It is not a human playtest and does not verify hosted rooms, Windows rendering,
LAN, reference-game adapters, failure/reconnect scenarios or audio listening.
