# Independent packaged-candidate review

No issue found in the archive/provenance/campaign-restart evidence for clean source `219bcf94136db9cd0fe2ac81f7e8a636be657e60`.

- Recomputed archive size **32,788,690 bytes** and SHA-256 **2781921fcd858577159c7222e915e479b7af88345b6cf3bfe0144641cd4b7bd8**.
- Verified all **128 archive bundle entries** against the manifest and local `.app`, including exact symbolic-link targets. The embedded build-info matches the pre-archive manifest fields.
- Verified all **121 snapshotted inputs** by SHA-256. **95 inputs** map byte-for-byte to the recorded clean Git commit (including renamed recipe/release copies). The other **26** are generated package-data/helper metadata or bundled upstream license files. The recorded commit contains both Causeway `316bcb2` and playback `a27c473`.
- PyInstaller Analysis uses the snapshotted entry; all **68 project imports** in the PYZ table originate within the frozen source snapshot. Only the three intended public-input helpers and generated tools package enter the executable; no test or Tribes modules were included. All **17 package-data inputs**, including **14 WAVs**, match the installed manifest/receipt.
- Verified nine distinct frozen native process IDs at the same outside-repository extracted executable and asset root. Every reported input count matches its event list; every checkpoint SHA matches its complete saved text; all **seven inter-process joins are byte-exact**.
- Direct campaign: **471 inputs**, **8 UI reloads**, **3 process joins**. Recovery campaign: **513 inputs**, **9 UI reloads**, **4 process joins**. Total **984 inputs**, including **182 visible playback Finish commands**. Inputs are ordinary key/click events; tactical play is explicitly reported as visible automatic rounds, not manual or human play.
- Both final manual saves equal their reported ending checkpoints, and each final process reloads that exact ending then returns to Title. Both have three completed shard records. The recovery process reloads the exact capital-loss state before consuming recovery, and subsequent states keep recovery_used true. Reading preferences remain 125 throughout and in saved settings.

Records: `/tmp/review-package-219bcf9.json` and audit script `/tmp/review_candidate_package.py`.

Scope: read-only verification of retained artifact/build/native receipts. No new launch, full suite, fuzz, code-signing, visual, clean-account, Windows or human-playtest approval is implied. Root owns LaunchServices, screenshots, retention and final running checks. No candidate source or build artifacts were changed.
