# Shardbound sound preferences

`eador/preferences.py` owns `master`, `music`, `sfx` (finite numbers from zero
to one) and `muted` (an actual boolean). Defaults are 80% master, 50% music,
80% effects and unmuted. These preferences live in `settings.json` alongside
the save directory; campaign checkpoints contain no preferences.

The launcher should load/apply preferences before starting any audio:

```python
from eador.preferences import load_preferences

preferences = load_preferences(game)
# preferences.error is explicit if the file could not be loaded.
# Safe defaults are usable in memory; the damaged file remains intact.
```

Title and guide actions can open the ordinary overlay with a method-local
import, following the existing Codex/Rival scene pattern:

```python
from eador.settings_scene import SettingsScene
self.game.push(SettingsScene())
```

The screen previews edits through the one `game.audio` manager. Up/Down moves
the row cursor; Left/Right changes the value, including mute. Visible minus,
plus and mute buttons use the same commands. Enter/Apply writes before closing.
Escape/Cancel, or external scene removal, restores the exact runtime levels
and mute state present on entry. Scene exit performs no file writes.

Edits stay in a local draft. Apply constructs a separate Settings candidate,
so a failed write leaves shared preferences unchanged and the screen open.
A damaged file requires the explicitly labeled recovery action; it previews
defaults and explains that Apply will retain the damaged file before saving.
Cancel abandons that authorization. Recovery uses the framework's retained
file mechanism, preserving the exact displaced bytes. Write failures show an
actionable reason; the scene retains the full exception as `last_error` for
diagnostics without rendering potentially enormous filesystem paths.

This increment provides the screen and early-loading helper. Launcher/title/
guide wiring is a separate integration step. It adds no audio assets,
fullscreen, text scaling or reduced-motion control. Reduced motion should ship
with actual motion feedback, not as an inert toggle. This work alone does not
close the presentation/settings release gates.

Verification:

```bash
uv run python -m pytest tests/eador/test_preferences_scene.py -q
uv run python tools/verify_eador_settings.py --out /tmp/shardbound-settings
```

The integration journeys use real files and public keyboard/mouse input to
check preview, cancel, restart, wrong types/ranges, corrupt-file recovery,
failed Apply and campaign independence. The native checker pushes Settings
directly over the title, verifies real pyglet key routing, and captures normal
1280×800, compact 1280×720, damaged-file and write-error screens. Screenshot
inspection caught and removed raw-error footer overflow.
