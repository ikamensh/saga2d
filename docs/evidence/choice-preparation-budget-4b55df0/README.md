# Choice preparation CPU allowance — 2026-09-06

Source `4b55df0f4ba1200c7fcd66fd24f65ea2e3730161` fixes development work
that bypassed the existing allowance: `prepared_choices()` ran all twelve
hero/theme campaigns before native input pacing began. The default now passes
one shared `CpuBudget(25)` through preparation and verification. The CLI exposes
`--cpu-percent`; 100 explicitly disables CPU pacing. Two standalone native
frames use the existing 30 FPS helper, and both owned sessions call `Game.close()`.
No game rules, scene layout or framework API changed.

The retained pre-fix regression called the original no-argument preparation
through real campaign rules and failed because it never yielded. The final
focused checks pass **3 tests in 9.61 seconds**: all earned snapshots stay equal,
each chosen reward reloads exactly, and the real mock input journey honors the
default/explicit allowance and closes both backends. Only environmental CPU,
wall-clock and backend observation are controlled. This is no native CPU or
battery measurement.

Command: `uv run python -m pytest tests/tools/test_verifier_preparation_budget.py -k choice -q`.
The separate existing frame/input/CPU checks also passed 25 tests in 2.32 seconds
before this helper change. No full suite, native window or large matrix was
launched for this fix. Other tasks' ordinary pytest runs remain unpaced.

[RED symptom](red-no-yield.txt) and [focused test output](focused-tests.txt) are
retained verbatim. SHA256SUMS covers these files and this explanation.
