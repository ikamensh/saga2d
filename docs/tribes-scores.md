# Tribes: final scores, surrender and local records

The final score rewards a developed empire and a decisive victory. The results
screen shows every contribution, the actual winner, and each tribe's fate.

| Contribution | Points |
|---|---:|
| Cities still held | 100 per city level |
| Parks still held | 250 per park |
| Technology | 20 per learned technology |
| Surviving army | 5 × each unit's recruitment cost |
| Territory still held | 5 per tile |
| Victory | 1,000 |
| Early victory | 50 × rounds remaining out of 30 |

For example, an empire worth 800 points winning in round 12 finishes with
**2,700**: 800 + 1,000 + (30 − 12) × 50. A defeat keeps its empire points and
receives no victory or early-finish bonus. Treasury and kill counts do not add
points, so hoarding currency and repeatedly killing cheap units cannot inflate
the score directly.

The live empire score still determines the winner at the round limit; bonuses
are added afterward. The internal transition to round 31 is displayed and
recorded as 30 completed rounds, with zero early-finish points.

## AI surrender

An AI with surviving troops continues to fight. An armyless AI first attempts
recruitment, harvesting and city rewards. It protects an immediately affordable
recovery unit from research or harvest spending. Then it concedes if:

- Every remaining city is occupied by enemies, preventing recruitment; or
- Its treasury plus all remaining turn income cannot pay for the cheapest
  unlocked unit before the round limit, or it has no cities to recruit from.

An empty treasury alone is insufficient: an open city that can fund a future
unit keeps the AI alive. Pending rewards are resolved before the decision.
Humans never surrender automatically. Existing elimination on losing the last
city remains unchanged.

Occupied cities pass to their occupying tribes. Unoccupied surrendered cities
become villages and their territory becomes unowned. Surrendered tribes leave
the turn order and are explicitly marked in the log and final standings. These
changes and the surrender marker survive save/load.

## High scores

Open **High scores (L)** from the title or results screen. **M** cycles map sizes,
**P** cycles tribe counts, and **Esc** returns. Each map size / tribe count has
its own top ten, avoiding an advantage from the larger empires possible on
larger maps. The table records tribe, score, victory/defeat, rounds, seed and
completion date. The current run is highlighted when it qualifies.

Scores sort descending, with fewer rounds and then earlier completion breaking
ties. Every new game gets a distinct run ID, retained by saves. Only the best
finish for that run is kept, so replaying from a save or reopening results does
not produce duplicate records. Loading the same pre-ID save gets a stable ID
derived from that saved world. A new game on the same seed is a separate run.

Records live in `~/.tribes/high_scores/save_1.json` for the normal launcher,
separate from quick saves and preferences. An explicitly configured save
directory places them under its parent's `high_scores/` directory. The game
reuses Saga2D's atomic save-file replacement and previous-file backup; there is
no new framework persistence abstraction. The score schema/formula is version 1.

Damaged or unsupported data is reported explicitly and never silently reset.
If recording fails, the result remains visible and High scores shows the error.
No score table is sent to a server.

## Verification

- `uv run python -m pytest tests/tribes -q`
- `uv run python tools/fuzz.py`
- `uv run python tools/verify_tribes_scores.py --output /tmp/tribes-scores`

The native verifier uses temporary records, real pyglet keyboard and mouse
events, a surrender triggered by ending the human turn, a full ten-row table,
empty and damaged storage, a restarted game, and 1280×800 / 960×600 canvases.
It checks content stays on screen and saves PNGs for visual inspection.
