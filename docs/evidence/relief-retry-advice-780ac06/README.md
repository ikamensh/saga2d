# Relief retry advice after its support dies

An actual paid Commander killed the enemy Militia, left the Skyrider alive,
then retreated. The saved retry retains Skyrider, Archer and Dread Guard at
74/90 total HP. It must explain landing denial without recommending removal
of already-defeated support.

The narrow regression failed before the conditional copy fix and passed after.
All 13 targeted Relief model/input tests pass. This changes briefing prose only.

The native run used base commit `780ac06` plus the conditional advice fix and
its regression; `verification.json` records exact source SHA-256 values and
confirms those files did not change during the run. Both free approaches were
inspected at 125%, in a 1280×720 window, after seven actual native input
activations including file load and Settings Apply. The complete loaded State
stayed exact throughout. Preparation and the opening used public model orders;
no roster or wounds were injected.

- [Forward retry, 125%](forward-retry-125.png)
- [Western retry, 125%](western-retry-125.png)
- [Source, inputs, labels and exact saved state](verification.json)
- [Native reproduction script](verify.py)
- [Artifact hashes](artifact-sha256.json)

Run the script from the repository root:

```sh
PYTHONPATH=. uv run python docs/evidence/relief-retry-advice-780ac06/verify.py
```

It writes its native
captures to `/tmp/relief-retry-advice-native`; inspect the resulting images.
The forward approach retains its established title, “Intercept the support”; the
live tactical advice now reflects the actual surviving defenders.
