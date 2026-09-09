# Saga2D — Agent Notes

See `CLAUDE.md` for commands, testing conventions and the mandatory
visual-verification loop, and `DESIGN.md` for the architecture.

Quick orientation:

- `saga2d/game.py` — game loop (`tick`), subsystems, scene stack glue.
- `saga2d/scene.py` — `Scene` hooks, `controls`, draw helpers, ownership.
- `saga2d/backends/pyglet_backend.py` — GPU backend: view matrices per
  space, triangle soup for shapes, cached labels, texture atlas.
- `saga2d/backends/mock_backend.py` — recording backend for tests.
- `saga2d/ui/` — components, layout math, theme.
- `sagaforge/render3d.py`, `effects.py`, `synth.py`, `fonts.py`, `ui/minimap.py`
  — pieces both games share: low-poly renderer, transient effects,
  procedural sound, the bundled font, the minimap component.
- `tribes/` — the turn-based game: `model.py` (rules), `mapgen.py`, `ai.py`,
  `textures.py`, `scene.py`, `__main__.py`.
- `warband/` — the RTS: `model.py` (fixed-step simulation and orders),
  `path.py`, `mapgen.py`, `ai.py`, `textures.py`, `view.py`, `scene.py`,
  `sound.py`, `__main__.py`.
