# Campaign map reading at 0bd713b

Source: `0bd713b45588f227ba07fa248c9e4a149b65998c`. The retained native run verified source hashes before/after. This is a development snapshot, not a packaged release or a claim of complete game-wide text scaling.

- [Native matrix](matrix.json): **2,394** selected-province layouts = 21 actual earned/historical cases × 19 provinces × 3 window sizes × 2 reading sizes. **4,685** public input activations and **127** exact save reloads; a real long-path error remains complete across **2** diagnostic pages. Actual window sizes were 1280×720, 1280×800 and 1920×1080; the logical canvas remains 1280×800.
- [Full tests](tests.txt): **1,152 passed in 115.43 seconds**.
- [Tribes stress](tribes-fuzz.txt): 60 AI games and 20 deterministic monkey runs, no failures.
- [Linked Shardbound stress](linked-fuzz.json): 60 model campaigns and 20 public-input scene runs, no invariant failures. All 60 random model policies ended in defeat; this is reliability evidence, not a balance or play-quality result.

The native journey applies/cancels Settings, reads all selected provinces, visits existing overlays, restarts, and executes an actual invasion/retreat/end-turn with the exact public-model result. Historical v11 and Challenge-1 saves preserve their own rules. Real purchases supply the full control army, zero gold and zero crystals; two actual retreats exhaust the campaign actions. A saved encirclement supplies zero income and unpaid-upkeep pressure.

These seven representative screenshots were opened and inspected. Full guards and every other province description were also checked in the matrix. The unchanged tactical art was inspected after the native invasion; the default province-art label behavior is preserved for other callers.

| Frame | Evidence |
|---|---|
| [Opening 100%](standard-opening-100.png) | Baseline complete map and commands |
| [Encircled 125%](saved-encircled-125.png) | Zero income, shortfall, complete six-troop army and wrapped orientation names |
| [Paid control army 125%](paid-full-army-125.png) | Current role names, level/health, exact resources and current Watch |
| [Linked campaign 125%](linked-opening-125.png) | Campaign control/stage and numbered map target retained |
| [Saved Challenge-1 125%](saved-challenge-1-125.png) | Old production/recovery rules, wounded army and selected province |
| [Message link](complete-message-link.png) | Failed save leaves the selected invasion intact and exposes full message |
| [Complete message 125%](complete-message-1.png) | Actual filesystem diagnostic, measured pages, explicit Return |

Reproduce with `python tools/verify_eador_shard_reading.py --output /tmp/shard-reading` from the recorded revision. [Provenance](provenance.json) records artifact hashes. The source change is described in [Campaign map reading](../../eador-shard-reading.md).
