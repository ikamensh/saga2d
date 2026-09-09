# Online multiplayer

Open **Multiplayer** in Tribes or Warband, or **Co-op** in Shardbound. **Online**
is selected by default. Choose **Create room**, share the room code with your
friend, and have them enter it and choose **Join room**. Both players connect
outward over encrypted WebSockets; neither needs a public IP, port forwarding,
a VPN, or a computer acting as the server.

The default service is `wss://games.tachyon-ai.eu/play`, hosted on Scaleway.
Use the same game build on both computers. Rooms have two seats:

| Game | Play mode | Server responsibility |
| --- | --- | --- |
| Tribes | Competitive, two human tribes | Turn order and every model command |
| Warband | Competitive, simultaneous RTS | Orders and the 20 Hz simulation clock |
| Shardbound | Shared-realm campaign co-op | Campaign decisions, tactical orders and campaign progression |

Warband also supports a [headless AI client on a separate computer](warband-remote-ai.md)
that takes one ordinary player seat, for testing or playing against a remote bot.

The creator's selected map and campaign options configure the room. Both
players receive the server's world, including the creator. The room starts
when both connect and pauses whenever a seat disconnects. Menus do not pause
a connected match; in particular Warband continues while a menu is open.

The waiting screen offers **Copy room code** and **Copy invite link**. The link
(`https://games.tachyon-ai.eu/join/<game id>/<code>`) opens a page that shows
the code, explains how to join and offers the download for a friend who has not
installed the game yet. It contains only the game and room code.

A short connection interruption reconnects automatically. After leaving or
restarting the app, choose **Rejoin last room**. Each computer privately saves
its own seat credential alongside its game settings; the shared room code
only admits the second player initially. Keep the private credential private.
Match rooms expire after 15 minutes without both players; Shardbound campaign
rooms are kept for seven days, so a co-op campaign can continue on another
day. Starting another online room replaces that game's locally remembered room.

Installed games check the release catalog when Multiplayer opens and show
**Update available** with an **Open download page** button when a newer build
is published. A client the server no longer accepts sees **Update required**
with the same button; both players need the same version.

Commands interrupted by a lost connection are never replayed automatically.
Check the refreshed world before repeating an order. Simultaneous decisions in
Tribes and Shardbound may reject a stale order with a request to try again.

## Command line

```sh
uv run python -m tribes --online-host --seed 7 --size 14
uv run python -m warband --online-host --seed 3 --size Medium
uv run python -m eador --online-host --campaign --seed 7

# Use the code printed by the creator's lobby, in the same game.
uv run python -m tribes --online-join ROOMCODE
uv run python -m warband --online-join ROOMCODE
uv run python -m eador --online-join ROOMCODE

# Reclaim this computer's saved seat after restarting.
uv run python -m eador --online-resume
```

`--server wss://your-server.example/play` overrides the hosted endpoint.
`SAGA2D_SERVER_URL` sets it for both menus and command-line launches. Plain
`ws://` is accepted only for loopback development; public connections require
trusted TLS certificates.

## LAN mode

Choose **LAN** in the same menu for direct local-network or private-VPN play.
The original `--host`, `--join ADDRESS`, `--port` and `--room` flags retain their
LAN meaning. See [the LAN transport and game integration guide](multiplayer.md).

## Boundaries

This is private room play, without public matchmaking, ranked accounts or
spectators. The server validates orders and owns the authoritative simulation.
Competitive snapshots still contain the full world for the existing game
views, so a modified client can inspect information hidden by normal fog.
Offline save files remain separate from multiplayer rooms.

Server storage serializes complete authoritative state through the game
catalog's `checkpoint_match`/`restore_match` pair. Network `snapshot(player)`
is a separate interface, so future player-view filtering cannot erase private
state from a saved room. This separation does not add fog filtering to the
existing games or change their on-disk checkpoint formats.

## Development checks

```sh
uv run python -m saga2d.server --games tribes.multiplayer:ONLINE warband.multiplayer:ONLINE eador.multiplayer:ONLINE --host 127.0.0.1 --port 8765
SAGA2D_SERVER_URL=ws://127.0.0.1:8765 uv run python -m tribes
uv run python -m pytest tests/framework/test_server.py tests/framework/test_online_client.py tests/framework/test_online_menu.py -q
SAGA2D_SILENT=1 uv run python tools/verify_online.py /tmp/saga2d-online
```

The integration checks cross real sockets into a separate dedicated process;
they exercise all three games, turn ownership, room isolation, invalid input,
private seat recovery and connection interruption. The native verifier captures
the actual menu, lobby and gameplay after issuing native input.
