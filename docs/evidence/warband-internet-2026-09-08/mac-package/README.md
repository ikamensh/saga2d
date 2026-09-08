# Matching Mac package

Built from immutable commit `90f30676de97d8bda327ef4fbd50b1149b7715ce`,
version `0.1.0-preview.1`, with pinned CPython 3.13.2 and PyInstaller 6.22.2.

The extracted executable passed font checks and real authoritative socket
tests from an isolated temporary profile outside the checkout. Native title,
multiplayer key input and match rendering passed; all three `native*.png`
frames were visually inspected. The procedural sound catalog contains 87
sounds. This verifies generation/loading, with audio muted for the run.

Both the standalone executable and the `.app` bundle passed public TLS room
creation/joining, rejected foreign orders, authoritative movement and private
seat reconnection against `wss://games.tachyon-ai.eu/play`.
The retained `.app` also passed its own native title/menu/match check;
`mac-app-native.png` was opened and inspected.

The local `.app` is retained at
`dist/warband-0.1.0-preview.1/Warband.app`. Its version matches the Windows
candidate; it includes the procedural scenery, distinct units/buildings,
continuous forest ground and workers' body motion during woodcutting.
