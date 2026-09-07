# Current Vault continuation after site placement changes

The ordinary candidate sweep stopped because the active Vault audit checked the
old coordinate `(-1, 1)` after completing the actual Vault. Preparation already
located the saved `sealed_vault`; the repair changes only the audit/test location
assertions and replaces the obsolete “Aerie” label for the production objective
with “adventure.” No purchase policy, manual route, recovery threshold, opponent,
rule, schema or production target changed.

The [current report](comparison.json.gz) records source commit
`4094c850b074f9612fe035738a111ba2ac3e19de` plus the uncommitted audit repair,
whose exact bytes are in its source manifest. Every measured source remained
unchanged during the comparison. It retains every preparation/branch command,
full before/after saves, costs, battle outcomes, recovery and rival operations.
The report was copied exactly from `/tmp/shardbound-vault-current-4094c85.json.gz`.

Both branches start from the same earned Ruins seed-7 Commander save on turn 6
at the Vault in `(-2, 2)`: 191 gold, 22 crystals, two actions, 14 mana, full
Militia/Militia/Archer/Warden/Ranger army, Quartermaster 2 and equipped Moonstone.
Broken Checkpoint `(0, 0)` is still neutral and produces 12 gold / 2 crystals;
its recorded Old Barrow adventure remains unexplored throughout the comparison.

| Actual result | Free crossfire | Pay two crystals to unseal |
|---|---:|---:|
| Vault escape round | 4 | 2 |
| Surviving army + hero wounds at escape | 62 | 13 |
| Mana spent in Vault | 4 | 0 |
| Production captured | T8 | T7 |
| End turn | T13 | T8 |
| Recovery/wait turns after Vault | 7 | 2 |
| Troop casualties / replacement gold | 0 / 0 | 0 / 0 |
| Final gold / crystals | 623 / 73 | 390 / 34 |

Both Vault escapes award the real 60 gold, one crystal and Mirror Badge. The
unchanged continuation stops after production capture and a subsequent rival
operation. That stopping rule now produces **different horizons and rival
states**. Paid play ends on T8 after the rival captures Briarwood; its surviving
expedition is targeting Westwatch. Free play intercepts the expedition on T9 and
ends on T13 after the rival recruits a new Guard at its capital. Its extra waiting
also generates income and recovery.

Therefore the final treasury difference is not a matched economic advantage.
This snapshot supports the paid route's lower wounds at escape and one-turn
earlier production capture; it does not reproduce the historical matched-T11
38-gold / 2-crystal advantage or prove better later defense. The unfavorable
remaining threat in the paid endpoint is retained. No extra normalization turns,
substituted target, rerouted policy or injected resources were added to recover
the old result. The [historical comparison](../../eador-vault-continuation.md)
remains evidence for its original source and entry only.

Validation was serial and narrow: both existing tests in
`tests/tools/test_vault_continuation.py` passed in **1.22 seconds**
([raw output](focused-tests.txt)), including the one-order bound that preserves
an unfinished campaign. One CLI comparison used its existing **25% cooperative
CPU allowance**, completed in 0.896079 seconds of measured comparison time and
reported unchanged source ([raw output](comparison.txt)). This short run is not
an instantaneous CPU-cap or battery-life measurement. No native window, other
campaign matrix or gameplay acceptance claim is included.

```sh
uv run python tools/audit_eador_vault_continuation.py --cpu-percent 25 --output /tmp/vault-current.json.gz
uv run python -m pytest tests/tools/test_vault_continuation.py -q
```
