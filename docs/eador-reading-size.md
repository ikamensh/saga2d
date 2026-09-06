# Codex reading size

The Field Codex offers **Text size** (`T`), opening Settings directly on
**Display → Codex reading size**. Choose **100%** or **125%** with Left/Right
or the visible minus/plus buttons. The sample previews the selected size.
Apply saves it and returns to the same first visible entry; Cancel restores the
entry size. Sound remains the default tab when Settings is opened normally.

This setting enlarges the Codex category introduction and each entry's title,
facts and description across Troops, Abilities, Buildings, Skills, Sites and
Relics. Navigation buttons, header and page count keep their normal size.
Other screens—including tactical forecasts, HUD, recruitment, rewards, equipment,
saves, campaign plans and encounter briefings—keep their existing text sizes.
The Settings notice states this scope. This is a complete reference-reading slice;
it does not close G10's requirement for broader text scaling and readability.

## Layout and persistence

The game creates wrapped Saga2D Labels in Columns. It attaches them before
querying their public `get_preferred_size()` so page breaks use the real backend's
font measurements. Columns own line/row placement; the Codex owns whole-entry
pagination and its navigation. Text is never shrunk or clipped to fit a page.
A new entry that cannot fit alone raises a clear error and must be edited or
supported deliberately. Current and older saved values use the same layout.

Reflow keeps the previous first entry at the top and repacks the entries before
and after it. Every entry remains reachable once, in the same order. Changing
category starts at its first entry. Native window resizing also remeasures the
pages; the logical canvas stays 1280×800 with the existing letterboxing.
`visible_entries` exposes the current complete entries for public verification;
there is no fixed entries-per-page contract.

The strict integer `codex_text_scale` preference lives in the existing game
settings file. Missing values default to 100 without rewriting older files.
Malformed values, including booleans, floats and unsupported percentages, expose
the existing recovery flow. Ordinary Apply cannot overwrite damaged bytes;
explicit recovered Apply retains them. Failed writes leave the draft open.
Cancel and external scene removal restore the runtime entry value without writing.
Campaign checkpoints never contain this preference.

`eador.preferences.codex_text_scale(game)` reports the runtime percentage.
`SettingsScene(focus="codex_text_scale")` opens this row, while the no-argument
constructor retains the ordinary Sound-first flow. These are game-owned seams;
there is no global framework theme mutation or settings-screen subsystem.

## Verification

```bash
uv run python -m pytest tests/eador/test_codex_scale.py tests/eador/test_codex.py tests/eador/test_preferences_scene.py -q
uv run python tools/verify_eador_reading.py --matrix --output /tmp/shardbound-reading
```

The public integration journeys cover visible controls and keyboard parity,
preview/Cancel, Apply/restart, preserved reading position, invalid-file recovery,
failed Apply, old preference files, all catalog entries in current/v10 saves,
and native-resize simulation. The native checker dispatches real Pyglet input,
checks every visible reading Label against the content bounds and records page
counts and actual window/framebuffer dimensions in `matrix.json`. It exercises
100/125 at 1280×720, 1280×800 and 1920×1080 native window sizes on the fixed
logical canvas, using an earned Censer battle, the paid Observatory approach,
and a v10 active save. Screenshots
still require visual inspection; pixel measurements do not establish universal
font availability or cross-platform accessibility.

The 2026-09-06 macOS Retina run passed 72 category traversals, 420 measured
pages and 912 entry presentations. Actual backing sizes were 2560×1440,
2560×1600 and 3840×2160 for the three requested native windows. The run
exposed and then verified the separate framework measurement-cache correction
`170d32e`; final screenshots were inspected after that fix. The full isolated
suite passed 908 tests, and both games' bounded 60-game/20-scene fuzz runs
passed. The existing native Settings journey also passed title/guide entry,
fullscreen restoration, damaged-file recovery and write-error presentation.

After integrating main `86bef00` (including the authored Observatory), the suite
passed 919 tests. The extended native matrix passed 108 category traversals,
650 pages and 1,422 entry presentations. The paid Observatory's actual crystal
fee/reward and hold rules were inspected at 100/125; its 25-entry Sites catalog
remains complete. These counts describe that content snapshot, not a fixed
pagination contract.
