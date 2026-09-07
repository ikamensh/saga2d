# Mac presentation refresh — 2026-09-07

Clean source **2d9520a1a871abda593075fd78bf0c7c36f20bc0** is preserved under
`dist/shardbound-checkpoints/2d9520a1a871/` with its app, ZIP and manifest.
It includes the recent attack/hit motion, contact-timed damage notices, impact
sounds that resume after Help/Saves, and compact inspection icons. The economy
and army-result extractions preserve existing solo behavior. This remains a
development checkpoint with shared-realm co-op; campaign PvP is not playable.

The ZIP is **49,269,888 bytes**, SHA-256
`1928990ac282aa33e3c27ccfaddd22fdeb420e758d5adf10a93023747808ed14`.
The retained application matches all 240 installed inventory entries, and local
ad-hoc signature verification passes. The manifest identifies 237 source
snapshot hashes and 116 package-data files. The previous 7b5562d checkpoint
remains untouched.

## Checks performed

Five packaging tests pass in 0.88 seconds. The pinned CPython 3.13.2 /
PyInstaller 6.22.2 / hooks 2026.7 builder extracts the archive outside the repo
and checks native input, campaign/battle/Guard save roundtrips, settings, About,
guide, Codex and rival screens. All 18 installed WAVs decode/play and audio
mix/cleanup passes using the silent driver; this is not human listening. The
external earned casualty forecast remains unchanged at both reading sizes and
reloads exactly. All ten packaged screenshots were opened and inspected.

A separate LaunchServices launch of the retained app (`open -W -n`) passes the
ordinary smoke with working directory `/` and its own bundled assets. Eight
frames exactly match the already inspected packaged frames; its changed About
data-path frame was separately inspected. The visual receipt maps each frame
to its retained representative. All application/build processes closed.

Source validation before this build includes 38 economy/recovery checks,
94 army/progression/campaign checks, bounded linked model/scene fuzzing, and
27 dedicated-server/checkpoint checks. See the adjacent progress record for
precise scopes; this was not a full-suite invocation.

## Reproduction and limits

From the clean detached worktree:

```sh
uv run --locked --isolated --python 3.13.2 --extra dev python -m pytest tests/packaging/test_eador_build.py tests/packaging/test_eador_smoke.py -q
/usr/bin/caffeinate -du -t 1200 uv run --locked --isolated --python 3.13.2 --with-requirements packaging/requirements.txt python tools/build_eador.py --forecast-save /tmp/shardbound-candidate-control-forecast.json
```

The forecast input is the unchanged earned checkpoint described in the
[previous package record](../shardbound-package-7b5562d/README.md). Build plus
smoke took 23.89 seconds wall and 15.96 seconds CPU. PyInstaller is uncapped;
ordinary smoke uses native pacing, and the forecast retains its 25% CPU
allowance. This is not a battery benchmark or a whole-build 25% cap.

This refresh does not repeat the previous package's full linked campaigns or
verify artifact multiplayer, Windows, clean-account launch or human playtests.
Source attack movies demonstrate motion; the frozen smoke does not replay that
full movie. No public deployment, signing identity or notarization occurred.
All overall Early Access gates remain incomplete.

`originals.json` maps retained originals, JSON is losslessly compressed, and
`sha256.json` authenticates the retained evidence files.
