"""Tribes — a Polytopia-style turn-based strategy game built on saga2d.

``python -m tribes`` starts it.  Package layout:

* ``rules``   — data tables: terrain, resources, units, techs, tribes.
* ``model``   — the world state and every rule that mutates it.
* ``mapgen``  — procedural map generation.
* ``ai``      — computer opponents driving the model.
* ``render3d``— a tiny Pillow software renderer for low-poly props.
* ``textures``— pre-rendered isometric tiles, props and units.
* ``view``    — isometric layout and sprite reconciliation for the map.
* ``effects`` — transient animations (damage numbers, pulses, banners).
* ``sound``   — procedurally synthesised effects and ambient music.
* ``scene``   — saga2d scenes: map, tech tree, settings, pause, help.
* ``title``   — title screen and new-game setup.
"""
