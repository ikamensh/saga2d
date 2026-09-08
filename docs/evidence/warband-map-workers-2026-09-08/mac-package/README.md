# Preview.3 installed Mac acceptance

Version **0.1.0-preview.3**, immutable source
`85becd0fda8493fffc14ad33baee32f4fccdee64`. Built from a clean detached checkout
with pinned CPython 3.13.2 and packaging dependencies.

The extracted portable executable passed real loopback socket and native
acceptance. The installed `/Applications/Warband.app` separately passed
against `wss://games.tachyon-ai.eu/play`, using isolated diagnostic profiles:

- Create/join, authoritative movement, rejected foreign orders and private
  seat reconnection.
- Global unit/upgrade orders, assembly point, automatic worker assignment to
  a building plan and plan cancellation.
- Actual mouse/key input through create/copy/paste/join, the global Train
  catalogue, a waiting Footman plan, cancellation, and the live Match menu.

Nine `installed-native*.png` frames identify the exact installed binary.
The second player's base remains in position beneath Plans and Match menu;
the shared camera regression has both scene-stack and native-pixel coverage.
The opening banner is still naturally present in the early match captures.
Apple M4 / OpenGL 4.1 Metal supplied native rendering; the 87-sound catalogue
was generated and loaded with audio muted.

`local-install.json` records installation time, both executable hashes and
the preserved preview.2 app backup. Existing settings and saved games were
not changed. The final app ZIP was extracted; its executable hash matches
the installed app and deep, strict ad-hoc signature verification passed.
The Mac archive hash is in `mac-SHA256SUMS` and `mac-build-manifest.json`.
Ad-hoc signing is not Developer ID notarization.

`mac-verification.json` keeps portable acceptance separate from
`installed_public_server` and `installed_native`. These automated flows
do not represent a full match between two human players.
