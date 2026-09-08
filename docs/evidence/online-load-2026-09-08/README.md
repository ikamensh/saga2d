# Bounded online load checks, 2026-09-08

`tools/load_online.py` against `wss://games.tachyon-ai.eu/play` from a laptop in
Western Europe, after the site launch and before raising the room limit from 16
to 32. Each room has two real clients issuing one valid order per second.

| Report | Rooms | Seats | Load | Orders | Rule rejections | State gap p50 / p95 | Health |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `warband-4-rooms.json` | 4 Warband | 8 | 90 s | 716 | 0 | 98 / 124 ms | 91–170 ms |
| `tribes-2-rooms.json` | 2 Tribes | 4 | 45 s | 178 | 0 | 1007 / 1226 ms (turn-paced) | 95–139 ms |
| `shardbound-2-rooms.json` | 2 Shardbound co-op | 4 | 45 s | 178 | 22 | 1008 / 1047 ms (turn-paced) | 81–103 ms |

Warband's server simulation held 19.35–19.62 ticks per second against its 20 Hz
target with no disconnects. The Shardbound rejections are the game refusing
orders after the automatically played campaign ended, not transport failures.
Earlier attempts hit the server's four-rooms-per-minute creation limit and, once,
the 16-room capacity filled by expiring test rooms; those attempts are not kept.
This describes a small friendly load, not a capacity guarantee.
