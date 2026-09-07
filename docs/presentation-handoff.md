# Presentation handoff — 2026-09-07

This records checkpoint `c507745`, when work stopped at the user's request to
conserve credits. The user subsequently authorized continued useful work.
See [current progress](early-access-progress.md) for later increments; this
checkpoint is not an Early Access release.

## Completed

- Final manual blows finish their visible contacts before the result screen
  (`3488d50`, native frames `5ae95d1`).
- Modal statistics, prices and utility controls use the existing icon system,
  retaining tooltips, shortcuts and explanatory text (`c1a3df2`).
- Attacks lunge toward their target and return; hits recoil. Direct orders and
  turn playback share game-specific pose code, including lethal retaliation.
  Reduced motion keeps figures still. Rules, save format, framework API and
  game frame caps are unchanged.

Run the source game with `.venv/bin/python -m eador`.
Review the [latest native movie and receipts](evidence/attack-motion/README.md),
[modal icon evidence](evidence/modal-icons/README.md), and
[final-blow evidence](evidence/final-blow/README.md).

## Verification boundary

Focused integration tests and mock/native input journeys passed. The motion
suite had seven passing tests on the final source; related playback/audio/final
blow checks had passed before the final casualty regression. The 16.83-second
native movie covers four cases and four exact UI reloads. Retained screenshots
were inspected. Capture and encoding were sequential, paced to a 25% CPU
allowance, and the Game closed. No owned test/capture jobs remain.

No broad suite, release package rebuild, human listening or independent human
playtest was added during this wrap. The frozen packaged candidate remains
`7b5562d1b76b` under `dist/shardbound-checkpoints/7b5562d1b76b/Shardbound.app`;
it predates the latest presentation changes. Windows runtime verification and
all overall G01–G19 Early Access gates remain incomplete.

## Next session, if requested

Keep the user's visuals and sound priority. Review the new motion and audio
first. Existing floating damage numbers can briefly obscure faces, and direct
orders still expose resolved health immediately. Online co-op retains snapshot
presentation. Decide on any further polish from actual review before resuming
strategic content or spending resources on a refreshed package.

Keep game-specific presentation in `eador`; only extract a framework primitive
when another consumer demonstrates a useful, simple shared interface. Preserve
earlier evidence and checkpoints. Run only one expensive local job at a time,
including agent jobs, and close verification Games explicitly.
