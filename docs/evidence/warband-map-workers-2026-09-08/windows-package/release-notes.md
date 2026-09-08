Warband 0.1.0-preview.3

Source: 85becd0fda8493fffc14ad33baee32f4fccdee64

Download the setup EXE, run it, and launch Warband from the Start menu. No Python or administrator account is required.
For internet play choose Multiplayer, create a room, and share its code.

CI verified the extracted and installed applications against an authoritative WebSocket server, including accepted movement, rejected foreign orders and seat reconnection; shortcut creation and uninstall also passed.
The installed Windows executable also passed those multiplayer checks over TLS against wss://games.tachyon-ai.eu/play.
Native title, multiplayer input and match rendering passed with the test-only software driver: llvmpipe (LLVM 22.1.8, 256 bits), 4.6 (Compatibility Profile) Mesa 26.2.0 (git-aacd123e02).
The installer is unsigned. CI host checks are recorded in verification.json; they do not establish GPU or audio quality on every Windows PC.
