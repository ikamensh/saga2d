# Reading earned decisions

ChoiceScene uses the existing shared **Reading size: 100% / 125%** preference.
Its introduction, option names, complete consequences and status/error prose
reflow together. The existing large title, button text and numbered keycaps keep
their normal sizes. This extends the [reading policy](eador-reading-size.md);
it adds no preference key, campaign-save field or framework API.

Both available options stay visible, in their saved order. Measured wrapped
Labels and Columns determine each complete card's height; the larger card
sets their common action position. Late advancement with one remaining
discipline shows one complete card. No description is clipped, shortened,
paged away or reduced in font size. The existing original relic icon appears
beside the heading.

T opens the existing reading-size row. Apply, Cancel, Codex, Hero and Saves
return to the same pending decision without choosing. Number keys and mouse
buttons use the currently displayed options. F5/F9 preserve the decision and
its consequences through the ordinary campaign save API.

A failed checkpoint after a choice leaves its full warning visible. When a
further earned choice is queued, that next decision is displayed. When the
final decision has already applied, an acknowledgement shows its result,
chosen consequence and error, with **Saves** and **Return**. Choice buttons are
removed, so old number keys cannot grant the reward twice. Saving or loading
from this acknowledgement uses ordinary campaign state; no acknowledgement
flag survives a restart. A successful final checkpoint retains the normal
immediate return to the campaign.

`tools/verify_eador_choices.py` earns its cases through public campaign commands,
recording JSON just before the policy chooses. Seed-zero journeys across all
four hero classes and three themes currently cover 42 distinct decisions:
every one of the 12 relics, real duplicate-to-crystal offers, all discipline
ranks and single-option late choices. These are earned states, not inserted
inventory, XP or fabricated reward text. The tool checks 252 layouts at both
reading sizes and 1280×720, 1280×800 and 1920×1080 window sizes, then exercises
every offered option through both keyboard and mouse and compares the full
result against the public model command. It also exercises preview/cancel,
restart, exact save/load, overlay return and damaged-autosave acknowledgement.

Run the native verifier with:

```sh
uv run python tools/verify_eador_choices.py --output /tmp/shardbound-choice-reading
```

`tests/eador/test_choice_reading.py` covers those same real input routes on the
recording backend, plus immediate quicksave/quickload error visibility,
oversized malformed version diagnostics and preserved damaged-file bytes.
The matrix is layout and command evidence, not a campaign balance or play-quality claim.

The [retained native evidence](evidence/shardbound-choice-reading-2026-09-06/README.md)
includes the source-attributed matrix and six inspected representative frames.
