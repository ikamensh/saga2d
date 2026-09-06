# Native Observatory journeys

All three reports were recorded at `46a5aa8` on macOS ARM64 with real Pyglet
keyboard/mouse dispatch. Their full game/framework/tool source hashes agree and
remained unchanged through all runs. Each army was bought using campaign input;
each approach was selected in the visible briefing. Battle commands include
exact control forecasts, saves/reloads, finite reward resolution and refusal of
a second reward. These are executable scenario plans, not human playtests.

| Plan | Inputs | Exact reloads | Hold round | Missing player HP |
|---|---:|---:|---:|---:|
| Sapper / cleared lane | 176 | 8 | 4 | 22 |
| Rune Adept / covered lane | 217 | 9 | 5 | 8 |
| Rune Adept / cleared lane | 217 | 9 | 5 | 2 |

All seven allies and one enemy survive each battle. The matched Rune orders
spend 12 mana in either lane; two crystals save six wounds without saving a
phase. The differently funded Sapper army does not isolate the fee's effect.
All seven retained briefing/forecast/result screenshots were inspected.

Replay any of these plans with:

```bash
uv run python tools/verify_eador_observatory.py --plan adept-covered --output /tmp/observatory
```

The combined integration suite passed 924 tests. Tribes passed 60 AI games and
20 random-input runs; Shardbound passed its bounded linked run of 12 campaigns
and 12 scenes with 2,227 input events. Broader model and randomized Observatory
evidence remains separately attributed to `3579eeb` in the parent directory.
This is the seventh authored family; G05 still requires more distinct content
and varied campaign sequences.
