# Shardbound deterministic stress evidence

Measured on 2026-09-05: **1,000 model campaigns and 100,039 random public
input activations passed without an unexpected exception or failed
invariant**. This is partial reliability evidence for G15/G16 in
[the Early Access criteria](early-access-criteria.md), not release readiness
or evidence that the game is balanced or enjoyable.

## Reproduce

Use source checkpoint `31a2c88` and run from the repository:

```sh
uv run python tools/fuzz_eador.py --campaigns 1000 --scenes 0 --report /tmp/eador-stress-model.json
uv run python tools/fuzz_eador.py --campaigns 0 --scenes 100 --events 100000 --report /tmp/eador-stress-scenes.json
```

The default command runs twelve model and scene seeds in about seven seconds
on the measured machine. `--seed N` selects the first seed, `--steps` controls
the random campaign prefix, and `--events` sets a minimum total number of
random scene activations. A failing scene prints its seed and last 25 inputs;
reproduce a scene from this run with
`--seed N --campaigns 0 --scenes 1 --events 1000`. Model failures print their
seed; use `--seed N --campaigns 1 --scenes 0`.

Full reports retain metrics, platform, source hashes and working-tree status:

- [Model report](evidence/shardbound-stress-2026-09-05-model.json)
- [Scene report](evidence/shardbound-stress-2026-09-05-scenes.json)

Both processes started at HEAD `5d2680e` with the final game changes already
on disk; those changes were committed as `31a2c88` during the run. None of the
43 measured Python files changed during either process, and every recorded
SHA-256 matched checkpoint `31a2c88` afterward. The driver is included in
those fingerprints.

## What was exercised

Model seeds 0–999 cycle evenly through the four hero classes. Each campaign
uses up to 120 random commands, resolving battles and saved skill/relic
decisions as they arise. Expected `RuleError` rejections must leave the entire
serialized state unchanged. A bounded cleanup then uses ordinary choice,
battle-resolution, retreat and end-turn commands until a real ending; this
cleanup is counted separately from random play.

Every state check verifies health, mana, resources, ownership, unit identities,
occupancy, equipment membership, battle/campaign outcomes and an exact schema
save roundtrip. Saved battles continue through the same AI round on two
copies; saved choices must produce the same subsequent state on both copies.

Scene seeds 0–99 enter through `TitleScene` and exercise the public `Game.tick`
input path using the mock backend. Each activation is a key press, mouse click
or mouse move; companion releases, setup and cleanup do **not** count toward
the 100,000 target. Random selection mixes arbitrary clicks/keys with targeted
legal destinations and visible button bounds to reach deeper states.

All nine scene types were reached: title, shard, battle, catalog, help, result,
choice, hero and save browser. The driver checks the state and scene stack
after each rendered tick. It covers building/recruiting, travel, tactics,
retreat, hero choices/equipment, manual/autosave slots, backup loading and
replay. Each seed saves an unfinished battle, returns through the save-slot
picker to the title, reloads the same state, and later starts a new shard after
an actual campaign ending. Saves use real temporary files and the normal game
persistence code; only the rendering/input backend is mocked.

## Observed results

| Measurement | Result |
|---|---:|
| Completed model campaigns | 1,000 |
| Model invariant/save checks | 127,384 |
| Rejected commands checked for no mutation | 33,433 |
| Paired saved-battle AI rounds | 23,828 |
| Paired saved skill/relic choices | 5,492 |
| Random public scene activations | 100,039 |
| Random keys / clicks / mouse moves | 61,740 / 37,042 / 1,257 |
| Total scene ticks, including setup/cleanup | 103,078 |
| Scene invariant/save checks | 102,114 |
| Pending-choice / result save-load checks | 219 / 671 |
| Backup / equip input attempts | 209 / 524 |
| Tactical move / attack / spell input attempts | 5,285 / 1,885 / 2,063 |
| Unfinished-battle title reloads / ending replays | 100 / 100 |
| Unexpected exceptions or failed invariants | 0 |

At the end of the model random prefixes, 53 campaigns had ended in defeat and
947 were still playing. After cleanup, 999 ended in defeat and one in victory.
These outcomes describe this deliberately weak random policy, not a win-rate
estimate for players. The random phase recorded 8,931 player battle victories
and 409 enemy victories; retreats and cleanup have separate counters in the
report.

Wall-clock elapsed time was 148.2 seconds for the model run and 251.9 seconds
for scenes on macOS 26.6.2 arm64 with Python 3.13.2. The processes overlapped;
these times are not frame-time benchmarks.

Independent cross-game checks also passed: `uv run python tools/fuzz.py`
completed 60 Tribes AI games (42 score endings, 18 domination) and 20 random
scene runs of 600 steps each, with zero failures. The framework suite passed
all 138 tests with `uv run python -m pytest tests/framework -q`.

## Limits and failures

During driver adaptation, its old assumption that “Save & title” immediately
opened the title failed after that flow gained a slot picker. The driver was
updated to select the visible manual slot. No product defect was found in the
recorded large runs.

This run does not supply the two-hour real-backend soak, p50/p95 frame times,
memory-growth measurements, display/platform matrix or human playtests required
by the release criteria. It does not exhaust every legal strategy or prove
future content behaves correctly. File corruption and OS write-failure cases
belong to the focused persistence tests, not this legal-gameplay stress report.
Later rule, content, input or persistence changes require another run against
their own source fingerprints.
