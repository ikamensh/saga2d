# Native realm mode selection and continuation

Measured source: `3638b69`, macOS ARM64, native Pyglet input. The
[combined report](native.json) records full source hashes, their equality before
and after all journeys, input events, saved rules IDs and completion records.
The eight retained images were inspected at this exact source. No source file
changed during these runs.

The opening driver selects each mode through title controls, buys a Temple,
earns enough gold to recruit an Acolyte, fights the home site, inspects the
recovery forecast and checks its actual next-turn gains. It saves, changes the
title's next-run mode and reloads unchanged, then tears down the Game and loads
the same real file in a fresh Game. Each mode keeps its saved rules ID. The first
driver attempt incorrectly assumed every starting grant could fund both
purchases immediately; a public-input regression now requires earning that gold.

Three complete Commander Rootward/Gate journeys exercise departures, contracts,
retinue selection, advertised funds, final battle briefing and completion.
Accessible additionally loses the middle realm, selects its recovery retinue and
launches the advertised 90-gold/four-crystal recovery. Together these journeys
use **1,108 input activations and 35 exact manual save/reloads**. Native runtime
is about seven seconds per automated campaign, not a measure of human pacing.

The combined source passes **958 tests**, Tribes' 60 AI games and 20 random-input
runs, and Shardbound's 12 linked model campaigns plus 12 linked scene runs
(2,227 inputs). These are development checks, not release-candidate stress or
human playtests. The catalog still selects `accessible-1`, `standard-1` and
`challenge-1`; the model audit's Challenge recovery tail remains open.

Reproduce from the named source:

```sh
uv run python tools/verify_eador_difficulty.py --output /tmp/shardbound-modes
uv run python tools/verify_eador_campaign.py --difficulty accessible --recovery --output /tmp/shardbound-accessible
uv run python tools/verify_eador_campaign.py --difficulty standard --output /tmp/shardbound-standard
uv run python tools/verify_eador_campaign.py --difficulty challenge --output /tmp/shardbound-challenge
```
