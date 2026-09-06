# Reading size

The Field Codex and expedition briefings offer **Text size** (`T`), opening Settings directly on
**Display → Reading size**. Choose **100%** or **125%** with Left/Right
or the visible minus/plus buttons. The sample previews the selected size.
Apply saves it and returns to the same first visible entry; Cancel restores the
entry size. Sound remains the default tab when Settings is opened normally.

This setting enlarges the Codex category introduction and each entry's title,
facts and description across Troops, Abilities, Buildings, Skills, Sites and
Relics. The Field Guide uses the same value for all four numbered headings, their prose
and the quick-reference line. Its two measured columns preserve all sections at
both sizes. Expedition briefings enlarge objective headings/instructions,
resource and approach facts, rewards, map legends, defender counts/health and
entry messages. Navigation buttons, large screen titles and page count keep their
normal size. Other screens—including tactical forecasts, HUD, recruitment, rewards, equipment,
saves and campaign plans—keep their existing text sizes.
The Settings notice states this scope. This is a bounded reference-reading slice;
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

The single strict integer `codex_text_scale` preference retains its historical
disk name and lives in the existing game
settings file. Missing values default to 100 without rewriting older files.
Malformed values, including booleans, floats and unsupported percentages, expose
the existing recovery flow. Ordinary Apply cannot overwrite damaged bytes;
explicit recovered Apply retains them. Failed writes leave the draft open.
Cancel and external scene removal restore the runtime entry value without writing.
Campaign checkpoints never contain this preference.

`eador.preferences.reading_scale(game)` reports the runtime percentage.
`SettingsScene(focus="codex_text_scale")` opens this row, while the no-argument
constructor retains the ordinary Sound-first flow. These are game-owned seams;
there is no global framework theme mutation or settings-screen subsystem.
There is one runtime getter, and no per-screen scale settings. Existing valid 125
files retain their value without a migration write; existing invalid files retain
the same explicit recovery semantics.

## Verification

```bash
uv run python -m pytest tests/eador/test_codex_scale.py tests/eador/test_codex.py tests/eador/test_preferences_scene.py -q
uv run python tools/verify_eador_reading.py --matrix --output /tmp/shardbound-reading
uv run python tools/verify_eador_guidance.py --matrix --output /tmp/shardbound-guidance
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

A compact [retained evidence set](evidence/shardbound-reading-2026-09-06/README.md)
contains the final matrix JSON, exact source/artifact provenance and six inspected
frames. The [100%](evidence/shardbound-reading-2026-09-06/troops-100.png) and
[restarted 125%](evidence/shardbound-reading-2026-09-06/troops-125-restarted.png)
frames show the reading change; the paid Observatory and earned Smoke frames
preserve the long saved-value cases.


## One reading policy and the remaining layouts

Expedition briefings now compose their objective and deployment side by side,
then rewards and defenders, followed by the entry message and controls. The
window height follows measured content, up to 780 on the 800-pixel logical canvas.
The map uses its original 21-pixel hexes in a reserved layout component; no
terrain, deployment, objective or fee rule is reconstructed by layout code.
Each defender type has its own line so its count cannot wrap away from its name.
Approach selection survives Settings and Codex overlays. Canceling the briefing
spends nothing; only its original entry command spends the selected fee/action.

This replaces an actual fixed-position limit: the old 450-wide instruction
column had about 227 logical pixels before its reward block. The shipped hold
prose measured 348 pixels at 125% through attached wrapped Labels at 1280×720.
Simply increasing the font would have collided with the reward. The scene now
measures whole groups and leaves text at the selected size.

Later conversions should reuse this same preference. Recruitment, reward and
Hero screens need measured complete rows/cards and visible-entry shortcuts;
currently recruitment uses 77-pixel rows and equipment 95-pixel rows. Campaign,
Rival and Saves need their own content flow. Tactical forecasts, HUD values,
unit badges and setting/control labels require a separate coordinated layout
pass. Changing the global theme or every `Screen.text` call cannot provide that:
most calls pass explicit sizes and positions, and buttons have fixed 40-pixel
heights. G10 remains open until those views are usable at the advertised size.

Saga2D already supplies measured wrapped Labels, Columns, Rows and button-owned
shortcuts. Each game screen should own its content budget and paging policy.
Extract game-owned pagination only when another real variable-entry catalog
needs it; the fixed four-section Guide needs no paging subsystem.

The Guide tracer built on `dc63810` uses native input from title through Settings,
Cancel, Apply, Codex return, three native window sizes and settings restart.
`tools/verify_eador_guidance.py` retains frames and checks reading bounds and
text/control separation. Its 100/125 Guide and Settings frames were inspected on
macOS Retina; the historical Codex matrix above remains separately attributed.


The subsequent briefing matrix on the same base passed 96 approach views: every
then-current authored encounter at 100/125 in all three native windows, including
actual paid preparations, a wounded Observatory retry, an unaffordable Crossing
fee and the linked final Gate. Another six records cover the Guide/Observatory
tracer. Native extraction, rout, hold, blocked-fee and final-Gate frames were
inspected. These are content-snapshot counts; new authored sites need their own
public preparation in the matrix.
