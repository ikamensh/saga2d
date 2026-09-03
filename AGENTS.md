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
- `tribes/` — the game: `model.py` (rules), `mapgen.py`, `ai.py`,
  `textures.py`, `scene.py`, `__main__.py`.
