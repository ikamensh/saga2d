# Shardbound local development build

Game and Saga2D framework: Ilya Kamenshchikov and contributors, under the
repository's MIT license. Terrain, miniatures, relics and effects use original
game-owned drawing code. The atmospheric environment painting was generated
with Codex's built-in image-generation tool; its prompt and provenance ship
in `eador/assets/VISUAL-PROVENANCE.md`. The music and sound effects are original
procedural compositions; see `eador/assets/AUDIO-PROVENANCE.md`.
Eador is the gameplay research reference; this is an independent game.

The application bundles CPython, pyglet, Pillow and NumPy. Original license
texts found in the installed distributions are included under `licenses/`.
The PyInstaller bootloader is distributed under its application-bundling
exception; its license is included there too.

This is a packaging foundation, not an Early Access release candidate.
It still uses system Verdana/Georgia fonts and the default development app
icon. No Windows validation, distribution signing/notarization, complete
platform support matrix or player-support service is claimed.

To report a problem during local testing, give the project maintainer the
build manifest, platform, seed, reproduction steps and save file. No public
support address has been configured for this development artifact.
