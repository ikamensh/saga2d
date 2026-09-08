# Shardbound 0.1.0-preview.1 distribution acceptance

Source `184584007ac3071dcb901e323a16bcd727877c14`, tagged `shardbound-v0.1.0-preview.1`; the first published Shardbound package.

- `windows-package/`: `build-manifest.json` and `verification.json` from
  [Windows CI run 34232824100](https://github.com/ikamensh/saga2d/actions/runs/34232824100):
  the frozen smoke journey (title, About, settings, shard, codex, rival, battle,
  saves, audio catalogue) in the extracted and installed applications under a
  test-only Mesa driver, the online co-op diagnostic against a loopback authority
  and, from the installed executable, against `wss://games.tachyon-ai.eu/play`;
  Start menu shortcut creation and uninstall.
- `mac-package/`: the Apple M4 build manifest (whose `smoke` records the same
  journey run by the build), the verifier's report with the smoke frames kept
  here, the loopback co-op receipt and `installed-public-server.json` from
  `/Applications/Shardbound.app` against the live service.
- `published-release.json`: sizes and SHA-256 of the three public downloads,
  fetched without authentication, and the installed executable hash.

The website at https://games.tachyon-ai.eu/shardbound/ lists these packages
from `releases/catalog.json`. The Early Access gates in
docs/early-access-criteria.md are separate from this distribution acceptance;
the build manifest keeps `release_ready: false`.
