# Tribes scoring and local high scores

Native verification of the results / high-score interface introduced in
`6b53680`, including the recovery refinements that follow that commit.

Inspected real pyglet captures:

- `victory-960.png`: score breakdown, surrender, highlighted local rank; 960×600.
- `leaderboard-960.png`: all ten rows and controls fit at 960×600.
- `defeat.png`: four-tribe standings and correct 30-round limit.
- `unsaved-result.png`: a storage failure keeps the score and navigation visible.
- `title.png`: the title and subtitle clear the expanded menu; 1280×800.

The PNGs contain the full physical Retina framebuffer. Screenshots use temporary
records. The scripted match reaches victory through a native end-turn key event
and AI surrender. Native keyboard and mouse open the leaderboard; Escape returns
to results, and a second Game instance loads the finished save without duplicating
its record. Empty boards, setup switching, and corrupt-file error details were
also captured and inspected during verification.

Reproduce with:

```sh
uv run python tools/verify_tribes_scores.py --output /tmp/tribes-scores
```

The final focused Tribes suite passed **174 tests**. The default 25%-CPU fuzz
run passed **60 AI matches and 20 random-input sessions**, with no failures.
The unrelated full repository suite was interrupted after **164 passing tests**
when another worktree was found running its own full suite; it is not claimed as
a complete pass. Focused and fuzz logs are recorded alongside this file.
