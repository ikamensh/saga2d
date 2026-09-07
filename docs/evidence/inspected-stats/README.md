# Inspected battle statistics — 2026-09-07

The generic enemy inspection row pairs attack, defense and range icons with
their values and explanatory hover text. Previously Range could wrap away from
its value at 125% reading size. Action-specific combat forecasts retain their
existing explanations. No rules or framework interfaces change.

The three icon-control integration tests pass. Native verification uses a paid
Observatory journey, real settings controls, one attack at each reading size,
layout/tooltip checks and two exact UI reloads. Both screenshots were opened
and inspected; the three statistics remain on one row at 100% and 125%.
The receipt records source hashes, inputs and complete resolved states.
Games close after the paced 30 FPS runs with a 25% CPU allowance.

```sh
.venv/bin/python docs/evidence/inspected-stats/verify-native.py /tmp/new-inspected-stats
```

Pass a new output directory and keep the display awake for native capture.
This is source-level visual verification, with no package or release claim.
