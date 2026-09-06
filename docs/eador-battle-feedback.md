# Ordered battle feedback

Ending a battle round (E) or asking for one automatic round (A) now shows the
resolved moves, abilities, hits and reactions in order. The player can finish
playback with Space, Enter, Esc or its visible button. Ordinary manually aimed
orders retain their immediate controls. This is a bounded G11 improvement, not a
claim that all feedback, accessibility or player comprehension gates are passed.

The concrete problem was the earned Relief sequence: leaving its support alive
lets Militia clear Skyrider's Pin, the flyer cross the screen, Pikeman Brace
strike first, then the flyer attack and other enemies retaliate. Previously the
first rendered frame after E showed every final position and four aggregate HP
changes. The individual cause-and-effect chain was available only in history.

## Rules and viewing

`Battle.trace(command)` observes one ordinary command without changing its
result. It returns frozen before/after frames and explicitly typed events. The
recorder lives only for that call; a `finally` clears observation even if the
command raises, and the original exception propagates. Nested observations are
rejected. Nothing is inferred by parsing battle-log prose, and neither traces nor
viewing clocks are serialized.

Rules finish atomically, and the ordinary campaign checkpoint records that
resolved state before playback begins. `BattlePlaybackScene` is a game-owned
modal that reuses BattleScene's board, objective, reading size and history UI.
Its isolated visual battle follows immutable frames; it is never assigned to the
campaign. Saving during playback therefore saves the completed turn. Loading
replaces the old scene stack and resumes the authoritative battle or its pending
result; it does not replay damage or award a reward twice.

An event takes up to 0.8 seconds, with the whole batch capped at eight seconds.
Long automatic rounds use shorter intervals. Settings and read-only history
pause the modal through the ordinary Saga2D scene stack. Reduced motion retains
ordered captions, highlights, status changes and HP values while units and
numbers remain stationary. The full history is available when a caption needs
more reading time. There is no persistent cinematic queue, new save version or
framework combat/event abstraction.

## Integration seams

The game owns `battle_trace.py` and `battle_playback_scene.py`. BattleScene offers
small drawing/button hooks so the modal can reuse its existing layout. Saga2D
continues to own queued-input scene transitions, layers, drawing, input, file I/O
and timing. No new framework primitive was needed.

The shared development `PlayerInput` uses the visible Finish button's Space
order by default before continuing a policy. It adds no saves, rule calls or
private animation advancement. Captures that need to watch the action use
`finish_actions=False` and ordinary `game.tick` calls instead. The random-input
tool treats playback as a real modal and tests ignored tactical keys separately
from ordinary recruitment, battle orders, saves and linked transitions.

## Reproduction and scope

```sh
uv run pytest -q tests/eador/test_battle_trace.py tests/eador/test_battle_playback_scene.py
uv run python tools/verify_eador_battle_feedback.py --scenario rally --scale 125 --output /tmp/feedback-rally
uv run python tools/verify_eador_battle_feedback.py --scenario rally --still --scale 125 --output /tmp/feedback-still
uv run python tools/verify_eador_battle_feedback.py --scenario hold --output /tmp/feedback-hold
```

The native verifier starts at Title, purchases the actual Relief party and issues
its orders through native mouse/key dispatch. It compares the complete resolved
State after every viewing tick. The retained sequence is sampled every three
60 Hz game ticks, with actual frame files and a timing manifest; it is a scripted
input capture, not footage of an independent human play session.

Independent review of the trace checked 138 paid Watch/Explorer/Relief commands,
full-state equality, event continuity, nested reactions, status expiry, saving
inside observation, and exceptional lifetime cleanup. Five genuine historical
active-battle fixtures also continue through the same complete outcomes with or
without observation. Terminal hold, queued input, save/reload, settings/history
pause, real file errors and ordinary controls after Finish have public scene
regressions. Final same-source validation and native evidence are recorded below.
