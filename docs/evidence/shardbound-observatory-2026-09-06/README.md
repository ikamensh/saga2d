# Observatory model evidence

Source checkpoint: `3579eeb` on `codex/shardbound-observatory`. This is the
bounded Broken Observatory model/content increment, before its new native
verifier and before difficulty schema v12. Source hashes in both reports match
at the beginning and end of each run. The tests passed on Python 3.13.2/macOS;
exact platform metadata is in the reports.

`manual-routes.json` retains three seed-seven Commander plans. Preparation uses
ordinary State commands, purchases, conquests, rests and rewards through
`prepare_observatory`; each tactical order passes through the public saved
`Journey` adapter. Attack, Pin and Heal forecasts match their immediate effects.
Every order reloads exactly, and each completed hold awards its reward once
with an enemy still alive. The actual commands, costs, starting levels and
ending HP are retained, not reconstructed from a desired outcome.

| Plan | Paid buildings / recruits | Campaign turn | Battle rounds | Missing player HP | Mana spent |
|---|---|---|---|---|---|
| Sapper, clear approach | 170 / 145 gold | 5 | 4 | 22 | 12 |
| Rune Adept, covered approach | 185 / 143 gold | 8 | 5 | 8 | 12 |
| Same Rune Adept army/orders, clear approach | 185 / 143 gold | 8 | 5 | 2 | 12 |

All seven player units survive each plan; one enemy Archer survives each hold.
Clear costs two crystals; covered is free. The Rune army earns a higher hero
and support level during its later preparation, so it is not a controlled
comparison with the Sapper army. Its paired terrain comparison is controlled:
the same 62 orders save six wounds for two crystals, with no phase advantage.
These specific plans do not establish optimal play or all-class balance.

The six tests in `tests/eador/test_observatory.py` also establish a saved paid
retreat followed by a free retry with the same finite defender wounds, rewards
once, 100-seed Ruins placement and required equipment sources, and an actual
prior-source Barrow continuation. The fixture and expected complete result
were generated with pre-Observatory source `f9b3a70`; they are not current saves
with a changed schema number. At this checkpoint the complete v11 result is
identical. The full suite passed **908 tests**, including all eight earned
active-relic tests unchanged.

`fuzz.json` records 300 randomized campaigns, 100 per theme, and 20 mock scene
runs with 10,003 random inputs. The campaign policy selected covered 25 times
and clear 16 times. Random play plus cleanup produced one victory and 299
defeats; this is evidence against state/input failures, not winning strategy.
All source hashes remained unchanged.

Reproduction from the source checkpoint:

```sh
PYTHONPATH=. python -m pytest -q tests/eador/test_observatory.py
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python tools/fuzz_eador.py --campaigns 300 --scenes 20 --events 10000 --steps 120 --report /tmp/observatory-fuzz.json
```

For interactive/input-adapter replay, prepare the default Sapper army and call
`observatory_route(state, 'clear', orders_type=...)`; for both Rune plans use
`prepare_observatory(state, support='adept')` and
`observatory_rune_route(state, 'covered'|'clear', orders_type=...)`. The helpers
are in `tools/eador_observatory_campaign.py` and do not import tests.

Native pixels, briefing cancellation, real controls and result presentation
are owned by the separate root verifier. This directory initially retains only
model/mock evidence; it does not claim native acceptance, G05 completion or
release readiness.
