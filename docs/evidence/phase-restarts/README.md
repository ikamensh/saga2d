# Saved phases resume through a fresh process

Nine saved phases loaded through the title controls in a new Python process,
then accepted their declared continuation with exactly the model oracle's full
state. The manual save files stayed byte-identical throughout loading and play.

The native run used working-tree source revision
`393359f62f6a13b3590b94a21287c2886e62e5b5`. Its receipt fingerprints 197
source, asset and fixture files, including the new verifier, and confirms they
did not change during the run. The verifier/test were not yet committed at that
revision; `source-sha256.txt` records their verified contents. No product source
changed for this unit.

## Results and process boundary

- Native pyglet: nine phases, 76 actual input activations, 81.772513375s wall,
  20.535762s combined writer/resume CPU, cooperative 25% allowance and native 30FPS.
- Writer PID 37001 created and closed nine Games. Only after all closed did it
  launch child PID 37256, which created nine fresh Games, each starting at Title
  and using F9 or F6/2 to load the isolated disk save. The child received file
  paths, not live State or Scene objects. All nine child Games also closed.
- Mock integration: **1 passed in 1.80s**, reported by the root agent that ran
  `tests/eador/test_phase_restarts.py`. No separate mock terminal transcript was
  retained; this timing is an execution report, not an archived raw log.

Reproduce the native journey with
`python tools/verify_eador_restarts.py --backend pyglet --output /tmp/shardbound-phase-restarts-native`
with the default CPU allowance. Exact input events, complete before/after states,
source hashes and fixture origins are in `native/verification.json.gz`.

## Earned states and continuations

| Phase | Preparation or fixed source | Public continuation after title load |
| --- | --- | --- |
| Campaign | Current Commander/Standard/Frontier seed7 title start | End turn |
| Battle | A second current title start, then Explore | Commander guards |
| Pending skill | Manual seed5 journal `commands[104].after` | Choose Tactician 2; relic choice remains |
| Pending relic | Same journal `commands[105].after` | Keep Veil Censer |
| Unresolved result | Same journal `commands[103].after` | Resolve the successful Courier evacuation |
| Departure | Packaged direct `phase-2.json.gz`, `loaded_checkpoint` | Choose Rootward; carry Swordsmen 4/5 and Moonstone/Iron Crown |
| Recovery | Packaged recovery `phase-3.json.gz`, `loaded_checkpoint` | Recover with those actual survivors/relics |
| Completed | Packaged direct `phase-4.json.gz`, `checkpoint` | Return to title, start another shard, reload completed chronicle |
| Capital loss | Retained complete-journey `capital-loss.json.gz`, `state.campaign` | Return to title, start another shard, reload actual defeat |

The manual journal is under
`docs/evidence/adventure-variety/route-seed5.json.gz`, earned by the declared paid
agent-directed route at `37a4e60` without autoplay. Packaged checkpoints are under
`docs/evidence/shardbound-package-7b5562d/campaign/`, earned by paid linked play
using the visible A autoplay control. The actual capital loss is under
`docs/evidence/shardbound-candidate-validation/complete-journey/`, from the earlier
paid campaign integration attempt, also using visible A. Fixed compressed-file
hashes and exact selectors authenticate these historical origins. Historical
battles and campaign preparation were not replayed here; no army, treasury or
outcome was manufactured.

## Visual review and limits

All 11 original native frames were inspected across the root and verifier agents:
nine restart frames and the departure retinue/arrival pair. No material clipping,
overlap or unit-health occlusion was found. Six representative restart PNGs are
retained here: skill, relic, departure, recovery, completed and capital loss.
`visual-review.md` preserves the separate review of the remaining frames.

This is fresh Python-process native input evidence, not a packaged-app launch,
human playtest, new successful campaign route, 125% reading matrix or tooltip
review. Most continuations have exact state/input receipts rather than separate
post-continuation screenshots.

The byte check includes `save_1.json`–`save_3.json` and their actual
`save_N.backup.json` paths. Each isolated case saves its manual slot once, so
there is no existing manual backup in this journey. The result proves primary
save preservation and no unexpected backup creation; it adds no backup-recovery
coverage. Autosaves 10–12 are outside this invariant because continuations can
legitimately update them.

## Retention and static review

`native/prepared.json.gz` and `native/resumed.json.gz` retain the exact writer and
child reports; `native/saves/` contains all nine original UI-written save
envelopes, losslessly compressed. `originals.tsv` maps retained originals to
their source paths and uncompressed SHA256. `SHA256SUMS` checks the archive bytes.

Final static review kept one existing PlayerInput adapter, fixed fixture
selectors, one fresh child and `Game.close()` in every owner path. No additional
persistence abstraction or source change was needed after the passing run.
