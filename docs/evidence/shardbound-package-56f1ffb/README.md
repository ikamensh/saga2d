# Standalone Mac development checkpoint

Source **56f1ffb1036b0a1e1a74bbc20d6ee0812e38c7e6** is preserved at
`dist/shardbound-checkpoints/56f1ffb1036b/Shardbound-macos-arm64.zip`.
The archive is **32,734,895 bytes**, SHA-256
`c8a8a2a5bb3c9fe7f026dd7dccfddd3e03a2d237496502dc5357678f8165d3e1`.

The [build manifest](build-manifest.json) records the frozen source, package
contents, pinned tool/runtime versions and all shipping audio hashes. Package
and build source hashes were compared with the committed files. Its dirty flag
is retained: the unrelated `.gitignore` edit was present. No application source
was uncommitted when the snapshot was taken.

The archive was extracted to a fresh directory outside the repository and ran
with Python environment variables removed and a minimal system PATH. Its
[executable smoke](packaged-smoke.json) and separate macOS
[LaunchServices smoke](launchservices.json) pass native input, manual/battle/Guard
save and reload, settings Apply/Cancel/restart and playback/mix/cleanup of all
14 shipping WAVs. Saves and preferences are isolated temporary files.
The extracted bundle passes `codesign --verify --deep --strict` with its local
ad-hoc signature. No Developer ID or notarization claim is made.

All seven retained captures were opened and inspected: title, shard, battle,
Codex, rival, Sound settings and the separately launched title. The source
[combined regressions](../shardbound-integrated-56f1ffb/README.md) pass 1,142 tests;
those source journeys are separate from this bounded packaged smoke.

This build contains ten authored families, the three linked shards/modes,
ten recruits, twelve relics, paid replacement, Tower infusion and reading size
for title/reference/purchase/choice/result/save/rival/campaign screens.
Shard and battle HUD scaling, more authored families, economy/pacing, complete
packaged-campaign play, sustained candidate stress, human/listening feedback,
Windows and clean-account checks remain open. **release_ready is false.**
All earlier checkpoint archives remain unchanged.
