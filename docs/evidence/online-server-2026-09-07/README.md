# Deployed online server — 2026-09-07

The dedicated Scaleway instance is running the recorded source release at
`wss://games.tachyon-ai.eu/play`. HTTPS health returned `ok`; the unprivileged
systemd service is active. The release candidate passed room creation/joining
for all three games on the actual Ubuntu VM before activation.

A public TLS test created two Tribes OnlineClients, committed an end-turn order,
restarted the real systemd service over SSH, and required both original clients
to auto-resume with the same private seats and exact acknowledged world. The
returning guest then successfully ended its turn. See `public-restart.txt`.
No room credentials or cloud secrets are retained in this evidence.

The full suite before main integration passed 1,578 tests; two source-hash
checks failed because final edits landed while they were running. The frozen
integration run then passed all 74 selected tests, including those two checks,
all online/LAN game tests, UI images, and packaging inputs. See
`integrated-tests.txt`. Four deployment tests additionally verified the extracted
artifact and all three game constructors through real WebSockets.

The real pyglet LAN verifier then passed Tribes, Warband and Shardbound against
separate local host processes after selecting the explicit LAN mode. Its
three join/gameplay captures were inspected. See `lan-native.txt`.

Server restarts preserve acknowledged turn-based commands; sudden failure may
roll Warband back to its last checkpoint (at most five seconds). Rooms expire
15 minutes after losing a player. Competitive snapshots still contain the full
world, so this is private friend play rather than ranked anti-cheat.
