# macOS companion — final preview source

Built from clean detached commit `fd6e0c911fa68aa0355d4b56dd8e4f0885c739d8`,
matching Windows CI run 34202934123. This supersedes the earlier `mac-package`
candidate for delivery; those older receipts remain historical evidence.

The portable ZIP passed isolated-profile, real WebSocket authority checks and
native rendering. The final `.app` separately passed the same multiplayer
checks over public TLS at `wss://games.tachyon-ai.eu/play`, plus native title,
multiplayer input, font and match rendering on Apple M4 (OpenGL 4.1). All six
PNGs were opened and inspected. Native match frames retain the normal opening
banner. The generated sound catalogue loaded 87 entries; this is not an
audio-listening acceptance test.

The `.app` was archived with `ditto --sequesterRsrc --keepParent`; extraction
preserved its executable SHA-256 and passed deep, strict ad-hoc signature
verification. The archive is unsigned by a Developer ID and not notarized.
`mac-SHA256SUMS` identifies the published app archive; the original build
manifest also describes the separately tested portable directory archive.

The ready-to-run local copy is
`dist/warband-0.1.0-preview.1/Warband.app`.
