# Modal icons

Build/recruit catalogs now use icon/value prices and troop stats with compact
purchase controls. Hero infusion, rival finances/troop health, and expedition
entry/resources/rewards use the same existing icon vocabulary. Utility controls
reuse their toolbar symbols. Names, roles, blockers and consequences remain text.
No framework API, new assets, model rules or save schema changes.

Final native journey: 549 pointer/key/capture events, twelve captures at 100%
and 125% reading size, all catalog pages, one paid Barracks purchase and exact
reload. Six representative frames are retained. Screenshots exposed a wrapped
“Entry” heading and unnecessarily centered statistic rows; final captures verify
both fixes. Every numeric value and icon has a hover explanation. Final mock
journey: 529 events, exact rendered tooltips and model-value comparisons.

Focused integration: 8 catalog/hero checks, 17 rival/guidance/final-hit checks,
and 3 catalog-page/earned-hero/previous-icon-journey checks passed. Bounded fuzz:
two scenes, 205 input events, 198 state checks. Tests and native runs were serial;
cooperative 25% CPU and native 30 FPS remain in use.

The Observatory is separately prepared by public model commands with automated
preparation battles. It is presentation evidence, not an independent first run.
Receipts contain source hashes and exact origins. Early Access gates stay open.
