# Causeway with ordered battle playback

The isolated integration source `a211c397ba808b06cd0300867385945f05095303`
merges main `316bcb2` with frozen playback `a27c473`. No production source
changes or conflict resolutions were needed. This check covers the twelfth
pattern with the new modal before root's final integration.

All 17 focused Causeway tests passed in 51.63 seconds. Both actual paid native
journeys passed through the existing PlayerInput visible Finish/Space control:

| Plan | Inputs | Exact F5/F9 reloads | Visible Finish orders | Outcome |
|---|---:|---:|---:|---|
| Infused Guard | 259 | 13 | 22 | Escape round 4, 12 wounds, 12 mana |
| Failed attempt and finite retry | 351 | 21 | 26 | Deadline round 5, then manual rout round 3, 9 wounds, 12 mana |

The 48 additional input actions are exactly the 48 visible modal completions
relative to the pre-playback routes. Preparation remains actual purchased
campaign play. A read-only capture subclass records each Causeway modal, checks
that rendering does not alter authoritative State, then delegates to the normal
visible Finish action. It does not call battle rules or privately advance a
presentation clock. All ten Causeway phase-entry views were captured.

The complete final State from each route is byte-for-byte identical to its
native pre-playback run at `1a20e54`. The paid infusion still spends three
crystals and one action without advancing the rival. Failure still charges the
normal 20-gold retreat fee, gives no partial-kill reward, and preserves the three
wounded survivors; retry and settlement remain once-only.

[The compressed report](evidence/causeway-feedback-integration-2026-09-06.json.gz)
contains both full journeys, input sequences, final states, modal capture
metadata, test output and 88 source hashes matched against the integration Git
revision. Python 3.13.2, macOS 26.6.2 arm64, real hidden Pyglet at the shipped
1280×800 canvas; briefings/Codex were checked at both 100% and 125% text.

Inspected images: [guarded carrier and caster movement](evidence/causeway-feedback-2026-09-06/guarded-movement.png),
[incoming shot](evidence/causeway-feedback-2026-09-06/incoming-shot.png),
[actual Repulse](evidence/causeway-feedback-2026-09-06/repulse.png),
[finite retry briefing](evidence/causeway-feedback-2026-09-06/finite-retry.png), and
[manual retry result](evidence/causeway-feedback-2026-09-06/retry-result.png).
The captions, visible Finish control, disabled battle orders and retry guidance
are readable. No actionable integration finding was reproduced.

To replay the retained capture harness at the recorded revision:

```sh
caffeinate -u -t 1
PYTHONPATH=. uv run python docs/evidence/verify_causeway_feedback_integration.py
```

Its output is `/tmp/causeway-feedback-integration-native`. This bounded check
complements the playback owner's full/fuzz/timing evidence; it does not replace
those checks or independent human playtesting.
