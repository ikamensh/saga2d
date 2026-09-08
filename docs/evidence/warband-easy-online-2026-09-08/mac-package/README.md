# Updated local Mac app and multiplayer flow

Version **0.1.0-preview.2**, immutable source `02377270d59fcf2ee6e9b0eef897303c1a5c0903`.
The existing `/Applications/Warband.app` was replaced after the new build passed
portable/native acceptance. `local-install.json` records the exact previous
and installed executable hashes, backup path and installation time. User
settings and saves were preserved. LaunchServices also opened this installed
app successfully; its own native diagnostics provide the inspected frames.

The installed app separately passed public TLS create/join, foreign-order
rejection, authoritative movement and private-seat reconnection. Native checks
used the same public server and actual mouse/key events: create room, copy
code through the macOS clipboard, cancel, paste by button and Cmd+V, join,
observe a match advancing and open its live Match menu. Seven screenshots
were captured; room-code, pasted-code, online-match and match-menu frames were
opened and inspected. Fonts, distinct artwork and controls render correctly.
The match image still includes the normal opening banner.

The `.app` ZIP was extracted and matched the installed executable hash; its
deep, strict ad-hoc signature check passed. It is not notarized or signed
with a Developer ID. Apple M4/OpenGL 4.1 were the graphics test context.
`mac-SHA256SUMS` identifies the exact published Mac archive.

The portable native result in `mac-verification.json` used loopback authority;
`installed_public_server` and `installed_native` identify the final installed
application and public server. Diagnostic profiles were isolated from user
settings and saved rooms. Clipboard text was restored after the native test.

The two `online-result-*` images are native victory/defeat display fixtures
from the same source revision. The underlying scene's result was marked as
already handled before the network result overlay was pushed; the verifier
asserted it remained the top scene and had no New game action. Both frames
were inspected. These are visual fixtures, not a claim of playing two full
matches; the real-socket result tests cover the live scene transition.
