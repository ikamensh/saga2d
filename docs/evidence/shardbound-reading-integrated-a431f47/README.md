# Combined forecast and diagnostic verification

Source **a431f47**, including tactical forecast reading and complete Save/Replacement
diagnostics. The economy attribution merge contains tools and evidence only.

- Full suite: **1,148 passed in 117.79 seconds**.
- [Native diagnostics](diagnostics.json): **25 pages / 93 inputs**, complete real
  long-path errors, exact backup/replacement recovery, both reading sizes and
  three window sizes. All recorded source hashes match this commit.
- Tribes: **60 AI games / 20 scene runs**, no failures.
- [Linked Shardbound fuzz](linked.json): **12 model campaigns / 12 scene runs**,
  **2,195 input events**, invariant/persistence checks passed. The random policies
  finish in defeat; this is reliability evidence, not a balance claim.

[Forecast screenshots and native journey](../shardbound-forecast-086ce14/README.md)
and [diagnostic screenshots and independent review source](../shardbound-diagnostics-fca7596/README.md)
retain their original attribution. [Provenance](provenance.json) hashes these
combined reports. No new packaged build or release-gate completion is claimed.
