# Rival intelligence reading evidence — 2026-09-06

Source `3947ec2307a4066dc404816a9a6642961bc2bf0f` includes the completed
replacement interface and its input adapter. [Provenance](provenance.json)
records the platform, commands and source/artifact hashes. Six native frames
were inspected (final survivor/defeat/old-rule frames byte-match their earlier
inspected captures):

- The complete six-troop opening at [100%](opening-100.png) and [125%](opening-125.png).
- [Saved wounded survivors after paid interception and withdrawal](intercept-survivors-125.png).
- [The defeated expedition and its paid rebuilding delay](defeated-125.png).
- [Earned encirclement and all named breakout routes](encircled-125.png).
- [Preserved Challenge-1 rules](saved-challenge-1-125.png).

The [matrix](matrix.json) passed **90 layouts / 818 input activations / one
exact save-load**. Its 15 saved states cover all three mode openings and first
conquests; Standard's paid approach, interception survivors, recovery, healed
force, defeat and new recruit; and actual v11, Challenge-1 and fortified-capital
saves. Every case was read at 100%/125% in 1280×720, 1280×800 and 1920×1080
windows. All these cases fit on one force page. Values and health come from
public campaign/battle commands and saved rules, without inserted state.

The verifier checks complete orders/location, treasury, prices, individual
survivors, current rule delays and encirclement advice. Keyboard/mouse Locate
and unrelated command keys leave full state JSON unchanged. Settings
Cancel/Apply/restart preserve the reading preference. Reading itself creates
no campaign save files; the exact reload runs after closing the view.

The existing native rival journey also passed on this source: inspection,
paid interception, saved persistent wounds, defense, paid rebuilding and an
old-save supply breakout. The combined full suite passed **1,113 tests in
140.89 seconds**. Tribes passed 60 AI games plus 20 input-monkey runs at seed17.
The [linked Shardbound fuzz report](linked-fuzz.json) passed 60 model campaigns
and 20 scene runs, with 3,730 input activations. All random model campaigns
ended in defeat; these are invariant checks, not a measure of winning play.

This is source-specific macOS layout/input evidence for the current rival
view. Map/battle HUD scaling, global accessibility and AI strength are outside
its claims. See the [implementation note](../../eador-rival-reading.md) for
scope and reproducible commands.
