# Shardbound display preferences

Settings opens on **Sound** so the existing arrow-key sound journey is unchanged.
**S** / **D** choose Sound / Display; **Tab** switches between them. Up/Down selects
a row, Left/Right edits it, and the visible buttons perform the same actions.
Enter applies both tabs; Esc cancels both. The active tab is labelled in the title.

Display offers window sizes 960×600, 1280×720, 1280×800, 1600×900 and 1920×1080,
desktop fullscreen, reduced motion, and [Codex reading size](eador-reading-size.md). A window-size choice leaves fullscreen.
The OS can constrain a requested size: the row reports the actual windowed size,
and the status line reports the current fullscreen/window size. Native window
resizes also update the controls and become the saved size when Apply is used.
The logical game canvas remains 1280×800; differing aspect ratios are letterboxed.
The reading setting enlarges Codex content only. These controls do not establish
that all game screens meet G10's readability/accessibility matrix.

Sound, display, motion and Codex reading size are game-owned preferences in
`~/.shardbound/settings.json`, separate from campaign slots and autosaves.
Dimensions must be two actual integers from 1 through 16384; this accepts native
custom sizes while rejecting malformed or unbounded requests. Fullscreen and
reduced motion must be actual booleans. Existing audio-only files receive the
new defaults without a migration or rewrite.

Changes preview in the existing Game. Cancel, or another scene removing Settings,
restores entry audio, motion, reading size, fullscreen and the actual window size remembered
behind fullscreen. Nothing is written by `on_exit`. Apply writes successfully
before closing. Failed writes leave the draft open. Damaged files require the
visible **Preserve damaged file & use defaults** action; its default preview can
still be cancelled. A successful recovered Apply retains the original bytes in a
unique recovery file using the framework Settings store.

`eador.app.create_game` loads sound/motion/reading and restores saved display once at
startup. Explicit `resolution` or `fullscreen` launch options, `visible=False`,
and `SAGA2D_HEADLESS` retain their controlled launch display instead. They still
load audio, reduced motion and Codex reading size. This prevents a hidden verifier or packaging smoke
from inheriting a user's fullscreen setting. The usual 1280×800 default is fixed;
test tools may explicitly construct a different logical canvas, as before.
`load_preferences(game)` applies sound/motion/reading only, so title entry, campaign load
and shard travel never reset a later native resize.

The action-feedback hook is `eador.preferences.reduced_motion(game)`. It reflects
saved settings, live preview and Cancel restoration. Battle feedback should keep
damage-number positions fixed when it returns true; the preference has no effect
on combat rules or campaign serialization. Future motion effects must consult the
same game-owned preference. The draw hook is integrated separately by the battle
scene owner; the settings implementation alone is not evidence of reduced-motion
presentation throughout the game.

## Verification

`tests/eador/test_preferences_scene.py` exercises real settings files, restarted
Games, keyboard/mouse parity, native-resize simulation, fullscreen cancellation,
failed writes, corrupted data, explicit recovery and launch overrides. The shared
`Game.windowed_size` public regression independently proves that a preview can
restore an OS-resized window after entering fullscreen.

Run `python tools/verify_eador_settings.py --out /tmp/shardbound-display-settings`
with an awake desktop. It uses native Pyglet keyboard and mouse events, silent
audio and temporary files. It captures Sound at 1280×800 and 1280×720 window sizes
on the same logical canvas, plus damaged/write-error states. Its Display journey
covers OS resize, letterboxed fullscreen clicking, Cancel from fullscreen,
Apply/restart, reduced-motion runtime values and hidden startup override.
`display-report.json` records actual native/windowed sizes and logical dimensions.
Screenshots must be inspected; these checks do not prove human sound quality,
global text scaling, cross-platform display support or Steam release readiness.
