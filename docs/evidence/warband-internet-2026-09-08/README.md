# Warband public internet verification — 2026-09-08

The native human client on this Mac joined a room hosted by the Paris game
server while the AI player ran on a separate Scaleway VM in Amsterdam.
`ai-live-process.txt` records the actual running client process and its
established TCP connection from `51.158.175.125` to `51.159.207.49:443`.
`infrastructure.json` records the separate VM identity and installed artifact.
The deployed AI module was compared byte-for-byte with committed source.

```sh
uv run python tools/remote_warband_ai.py install
uv run python tools/remote_warband_ai.py create --duration 600
SAGA2D_SILENT=1 uv run python tools/verify_warband_remote_ai.py docs/evidence/warband-internet-2026-09-08 --room tmnv1gx59wt6
```

**Passed in 21.6 seconds**, advancing from tick 6 to tick 386. The room code
here is historical, not a permanently available match.

- Actual native input joined through Online, moved a worker, ordered lumber
  harvesting, trained a peasant and sent a scout toward the opponent.
- Received server state confirmed each order, harvested lumber and completed
  training. The human client had no local match authority or AI brains.
- The remote player moved three workers, added a unit and started a farm.
  Its JSON journal records submitted orders separately from server snapshots.
- Scouting revealed a rendered blue opponent through normal fog rules; its
  subsequent chopping progress was verified from received state.

`report.json` retains order/state evidence. Inspected native captures:
`03-authoritative-chopping.png`, `05-remote-ai-visible.png`,
`06-remote-ai-progression.png` and `07-local-economy.png`. The first chopping
capture still includes the normal opening banner; later frames show the
unobstructed game and current procedural artwork.

The headless-client integration suite additionally passed four tests in
5.34 seconds: create/join as either seat, actual AI orders through real
sockets, invalid-room failure and bounded lobby timeout. These short checks
establish connection and early play, not a complete human-versus-AI match.

The hosted server was then updated from immutable commit `2205d6d`, including
the current Warband battle-event metadata. The candidate passed room creation
and joining for all three games on the VM before activation; the public TLS
smoke passed all three again afterwards. The frozen source passed **37 online
server, checkpoint, client, menu and headless-AI tests in 11.93 seconds**.
See `server-deployment.json`, `server-regressions.txt` and
`public-server-smoke.txt`. This update does not change Warband order rules or
simulation timing relative to the native run above.
