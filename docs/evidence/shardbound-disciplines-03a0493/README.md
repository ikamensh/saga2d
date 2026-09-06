# Earned discipline continuation evidence

Game/framework source: `1b54ad5`. Verification tool/tests: `03a0493`.
The report fingerprints match that committed source and remained unchanged
during each measured run. No gameplay, UI, framework or save-schema code changed.

Sixteen model campaigns pass: eight preferred disciplines, each both directly
and after an actual lost capital/recovery in shard two. Eight native campaigns
repeat the recovered routes through shipped keyboard/mouse controls. All reach
three completed shards with the preferred discipline at rank 3 and the other
at rank 1. All earn rank 2 on shard one and retain it through loss/recovery;
rank 3 survives the second departure.

Native environment: macOS 26.6.2 arm64, CPython 3.13.2, pyglet 2.1.13.
Default 1280×800 logical window, 2560×1600 captured framebuffer, 100% reading.
The native matrix is complete: **3,874 input activations, 102 exact F5/F9
reloads**, 136 earned choice records and 56 full phase checkpoints.

| Preferred discipline | Native inputs | Exact reloads |
|---|---:|---:|
| Quartermaster | 477 | 13 |
| Tactician | 456 | 12 |
| Duelist | 490 | 13 |
| Vigor | 492 | 13 |
| Pathfinder | 489 | 14 |
| Skirmisher | 464 | 11 |
| Channeling | 509 | 13 |
| Restoration | 497 | 13 |

Reports retain every decision's full before/after state, every phase checkpoint,
final states and source hashes. Native records additionally retain all inputs.
Every within-route reload compares full serialized state exactly.

- `model-direct.json.gz`: eight direct paid public-command runs.
- `model-recovery.json.gz`: eight model runs including deliberate capital loss.
- `native-recovery.json.gz`: eight native recovered campaigns, all input events.
- `summary.json`: compact results and exact ending hashes for all 24 runs.
- `tests.txt`: 40 passing targeted progression/journey integrations, 3.33 seconds.

Ten retained native images were opened and inspected: the eight
`*-rank-two.png` choices, `quartermaster-recovered.png`, and
`restoration-completed.png`. Descriptions/options/shortcuts are legible and
complete. The ending identifies Restoration 3 / Channeling 1 and recovery used.
These frames are actual native captures, without re-rendering or image edits.

The full-state **model-to-native results are not equal**. The public model
selection passes two troop IDs in veteran-priority order, while visible retinue
checkboxes submit the selected set in the roster's order. That can change which
troop identity occupies a physical battle slot and later retains particular HP.
The native and model routes remain separate results; no ID normalization hides
the difference. They both establish earned rank continuation, and their own save
restores remain exact. There is no claim that the UI promises a formation order.

This tool uses the existing paid Swordsman/recovery policy and **tactical
autoplay**, followed by the visible Finish playback control. It does not prove
manual counterplay, naturally watched feedback, skill balance, three different
army plans, human comprehension, other seeds/difficulties or Windows behavior.
The native run overlapped other stress work and supplies no normal-play CPU,
frame-time, duration or battery conclusion. It had already exited successfully
when the request to stop CPU-heavy verification arrived; no further native or
CPU-heavy tests were launched.

The initial development tracer's missing recovery adapter was fixed by using
real recovery controls before `03a0493`. A subsequent pre-commit mock matrix was
interrupted during tool development and is not counted. Only the three complete
frozen reports above contribute evidence.

For later reproduction, run one selected path at a time. The native command
opens a hidden window and requires an awake display:

```sh
uv run python tools/audit_eador_disciplines.py --skills tactician --recovery --output /tmp/disciplines-model
uv run python tools/audit_eador_disciplines.py --skills tactician --recovery --backend pyglet --output /tmp/disciplines-native
```

[Content audit and next manual comparisons](../../eador-content-acceptance.md)
explain what this evidence resolves and what remains for G03/G04.
