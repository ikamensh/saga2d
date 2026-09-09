# Shardbound settings and audio: reuse plan

Read-only audit, 2026-09-05. Main framework baseline: `00ca6cf`; Warband
offerings inspected from committed revision `f478e89` with `git show`, not
from its changing worktree. This is an implementation proposal for
[G10/G11](early-access-criteria.md), not evidence that those gates pass.

## Decision

Use the existing `Game.audio`, asset loader, scenes, buttons and measured
paragraphs. Adopt and harden Warband's small settings store instead of writing
another preferences-file implementation. Reuse its pure synthesis functions
for original Shardbound audio; keep playback on the one `game.audio` instance.
Settings screens, sound choices and reduced-motion policy remain game code.
There is no need for an audio graph, action registry, universal options schema
or a framework-wide animation switch.

## Existing capabilities

| Capability | Main | Committed Warband offering / consequence |
|---|---|---|
| Playback and mixing | `AudioManager` has master/music/sfx levels, mute, pitched effects, looping music and live music-volume changes. `Game` stops its own manager's music at teardown. | Same mechanism; reuse it. |
| Audio assets | `AssetManager` caches decoded effects and opens fresh music streams; WAV/OGG/MP3 paths are conventional. Mock backend records playback. | `sagaforge.synth` extracts reusable tone/noise/mix/envelope/WAV-generation functions from the existing procedural-audio approach. |
| Preferences | No dedicated settings store. Tribes embeds its options in campaign saves and passes dictionaries between scenes. | `Settings(path, defaults)` and `game.settings(defaults)` provide a shared mapping and `settings.json`; `game.data_dir` locates it. Harden before adopting. |
| Options UI | `Scene`, `Column`, `Row`, reactive `Label`, `Button.shortcut`, `draw_paragraph` suffice. Tribes already has keyboard-selectable volume rows. | Warband has a similar game-owned options screen. Copy the interaction pattern, not its game-specific rows. |
| Display | Startup logical resolution/fullscreen, aspect-preserving viewport, HiDPI rendering and inverse mouse-coordinate mapping exist. | `Game.set_fullscreen(bool)` delegates to the backend and recomputes the viewport. Useful to adopt with its verification. |
| Animation | Scene timers/actions, sprite movement, particles and camera shake exist. | Generic `Effects`, `FloatingText`, `Pulse`, `HitReaction`, etc. are reusable after review. Neither branch supplies a reduced-motion policy. |

The settings/audio module is a demonstrated shared need: Tribes' volume
options, Warband's persisted volume/display options, and Shardbound's G10/G11
requirements all cross the same file/playback seams. The games' option names,
sound compositions, event meanings and accessibility presentation differ.

## Smallest Shardbound implementation

`eador/preferences.py` owns the known keys, defaults and value validation.
Start with `master`, `music`, `sfx` (finite numbers in 0–1), `muted` and
`reduced_motion` (actual booleans). Keep preferences separate from `State`
and campaign saves: loading an old campaign must not restore old volume or
accessibility choices. Use one shared preferences object for the title and
in-game options screen.

Load and validate preferences before starting any playback. Configure
`game.audio.set_volume(...)` and `game.audio.muted` first, then start the
initial track. Warband's current `sound.install()` starts music before its
launcher applies stored volumes; do not copy that ordering.

An ordinary transparent `SettingsScene` is accessible from title and guide.
Use a row cursor with Up/Down and Left/Right, visible minus/plus buttons,
percent labels, and explicit Apply/Cancel controls. Volumes can preview live.
Apply validates and writes before announcing success. A failed write leaves
the screen open with the reason and the previous file intact; Cancel restores
the pre-edit runtime values. Do not perform fallible file writes in
`on_exit`, where a failure interrupts scene teardown. That is currently how
Warband's settings screen reaches `settings.save()` through `apply_settings()`.

Keep sound composition in `eador/sound.py`, with descriptive game cue names
and a small event-to-cue mapping. Use the pure `sagaforge.synth` functions once
merged; do not import `tribes.sound` or `warband.sound`. Generate original WAVs
at build time and ship them under the game's asset root with the generator,
version and provenance. This avoids first-launch synthesis and cache writes
in a packaged release. The runtime then needs only ordinary calls such as:

```python
game.audio.play_sound("attack_hit")
game.audio.play_music("shard_ambience", loop=True)
```

Begin with distinguishable UI confirmation/refusal, movement, weapon impact,
bolt, healing, reward/advancement, and victory/defeat cues, plus restrained
campaign ambience and a battle track. The exact compositions remain a sound
design task requiring listening. Trigger cues on confirmed commands or new
outcomes, never from `draw()` or every refresh. Music selection should check
`game.audio.music_name` before restarting the same track. Use this existing
manager directly rather than adding another bank and module-global hooks.

Reduced motion controls presentation only. When action feedback is added,
disable shake, camera pans, sprite travel/knockback and moving particles under
that preference. Keep immediate position updates, readable damage/result
text and static selection/target markers. Do not skip model commands or
globally stop timers; timers may also own useful messages and cleanup.
Shardbound currently has essentially static presentation, so an inert toggle
alone would not constitute reduced-motion evidence. Ship and test the policy
alongside actual feedback.

## Shared issues to address before reuse

1. **Settings validation and writes.** The committed store accepts
   `{"music": NaN, "sfx": true, "fullscreen": 999, "scroll_speed": -1}`
   without setting `error`; this was reproduced by loading the committed
   module against a real temporary JSON file. Its numeric type exception
   treats booleans as numbers. A 10,000-level nested JSON file raises
   `RecursionError`. A malformed file is replaced by defaults on the next
   `save()`; also reproduced. Its fixed `.tmp` path and rename lack the
   durable staging/backup guarantees already implemented for campaign saves.
   Preserve a useful small settings interface, reject non-standard JSON and
   invalid shape/type explicitly, and leave game-specific ranges/enums to the
   game validator. Reuse the existing durable-write mechanics through a
   private shared helper if needed; do not introduce a second public storage
   abstraction. A visible game-level recovery policy may offer defaults in
   memory, but must preserve the damaged file until explicit reset/recovery.

2. **Playback ownership.** `SynthBank(game, ...)` constructs a second
   `AudioManager`. Main Tribes' `SoundBank` uses the same pattern. In a public
   mock playback check, music started by the committed `SynthBank` remained
   active after `Game._teardown()`, which only stops `game.audio`. Prefer
   pure synthesis plus `game.audio` for Shardbound. Before adopting the bank
   itself as a general primitive, give its playback an explicit game-owned
   lifetime instead of relying on process exit or retained global hooks.

3. **Mute while effects are playing.** Source inspection shows that mute
   updates the music player and suppresses future effects. It cannot change
   already-playing effects: backend `play_sound` is fire-and-forget and
   `set_volume("sfx", ...)` does not update active players. This affects both
   existing games as well as Shardbound. Add a focused regression using a
   sustained effect, then extend internal player control so master/mute/SFX
   changes affect active playback and teardown releases it. Keep the public
   `AudioManager` interface; no game-specific mixer is needed.

One smaller committed synthesis bug also surfaced: a bank with only music
and `sounds={}` fails writing `sounds/VERSION`, because no effect created
that directory. Fix it in the shared synthesis module if that module is
adopted; it does not justify a Shardbound workaround.

## Display and text scaling are separate work

The backend's resize handler letterboxes the original logical canvas;
`Game.width`/`height` do not change with that physical resize. Fullscreen
switching therefore does not solve text scaling or responsive menu layout.
The current Shardbound launcher fixes 1280×800, and `Screen.text` and
`paragraph` use explicit font sizes. Changing only the theme cannot scale
those labels.

Reuse Warband's fullscreen operation rather than call native window methods
from game code. Add display choices only with the required restart/runtime
behavior stated accurately. Implement text scale in Shardbound's theme and
text wrappers together, and let measured heights and layout determine panel
spacing/pages. Do not add a global UI-scale primitive solely to stretch fixed
coordinates. Verify actual screens at 1280×720, 1280×800, 1920×1080 and HiDPI,
with each advertised text scale, before declaring a setting supported. Neither
inspected branch supplies that full matrix or a general text-scale solution.

## Verification and implementation order

First coordinate adoption/hardening of the committed Settings/fullscreen/synth
offerings; no Warband worktree or shared source was edited for this audit.
Then implement the game preferences UI and audio through the existing owner.
Add reduced-motion behavior with action feedback, followed by the display
and text-scale layout pass. These can be separate reviewable increments.

Public tests should cover settings restart across a new `Game`, campaign
load independence, malformed/wrong-type/nonfinite options, explicit recovery,
failed writes and retained data; keyboard/mouse parity, live volume preview,
Apply/Cancel; and audible-event selection through the mock playback records.
Native verification must exercise running music and effects during volume,
mute and teardown changes, inspect all options screens and listen to the
actual cues/loops at player volume. Reduced-motion and normal runs must yield
the same model state while presenting their intended visual differences.
Silent backend tests prove routing, not sound quality or audible mixing.

## Implemented display preferences

The game-owned Sound/Display settings transaction now uses the reviewed fixed-
canvas Game display API, including an actual `windowed_size` snapshot for Cancel.
Saved display applies once in `create_game`; audio/motion may apply on scene entry.
See [the implemented behavior and verification](eador-display-settings.md).
Text scaling and the full G10 screen matrix remain separate work.
