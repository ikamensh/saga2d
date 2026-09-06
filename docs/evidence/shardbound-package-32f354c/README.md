# Packaged battle readability — 2026-09-06

Clean development source: **32f354ce6233d8f159acf6692548e854acc322cc**.
This refresh includes the CPU caps, casualty forecasts and the battle-piece
health/selection fixes. All Early Access release gates remain incomplete.

Archive: `dist/shardbound-checkpoints/32f354ce6233/Shardbound-macos-arm64.zip`

- Size: **32,798,697 bytes**.
- SHA-256: `cfd75163fec5d38496e45c81a526523087dca582acc18fab58c9828012069d16`.
- Host: macOS 26.6.2, Apple M4 / arm64, CPython 3.13.2.
- Recipe: locked runtime, PyInstaller 6.22.2 / hooks 2026.7.
- [Full manifest](build-manifest.json), [build output](build.txt),
  [native smoke receipt](packaged-smoke.json), [signature check](signature-check.json).

## Verification

The full headless integration suite passes on the clean checkout:
**1,264 tests in 188.44 seconds** ([output](full-tests.txt)). It finished before
the build began. Expensive work ran serially; cancelled stress matrices and the
two-hour soak were not restarted.

The builder extracted the ZIP outside the repository and ran that frozen
executable with Python environment overrides removed. It verified build identity,
About/Guide navigation, campaign and battle saves, Guard, Codex/rival, settings
Apply/Cancel/restart, and all fourteen installed audio files with native
playback/mix/cleanup. This is an automated audio check, not a listening review.

An additional external save from the earned Control army's turn-14 battle
verified the lethal Rune Adept forecast at 100% and 125% text size, then a safe
Acolyte alternative. Ten native inputs leave the campaign byte-for-byte
unchanged, including an exact quicksave/reload. The external fixture has SHA-256
`4eb6076224527ed7a1240f030e8cc0c4f4902af7814eb58813b86277375b72e1`;
it is verification input and is not bundled in the archive.

The root agent and an independent reviewer opened the actual packaged
[125% casualty forecast](packaged-smoke-forecast-125.png) and
[opening Guard battle](packaged-smoke-battle.png). The forecast fits, HP labels
stay with their pieces, and selected-unit corner ticks differ from the targeted
enemy's outline. No visual blocker was found in these two frames.

A second extraction into `/tmp/shardbound-playtest-32f354c` passes local
`codesign --verify --deep --strict`. No LaunchServices recheck, clean-account or
Windows run, Gatekeeper/notarization acceptance, human playthrough, full frozen
campaign replay or sustained test is claimed for this refresh. The packaged
check exited successfully and its temporary windows/profiles were cleaned up.

## Reproduce

From a clean checkout of the source above, supply the plain State JSON stored
as `commands[80].before` in
`docs/evidence/shardbound-army-plans-cd351a9/control.json.gz`:

```sh
uv run --locked --extra dev python -m pytest tests -q
caffeinate -diu uv run --locked --isolated --python 3.13.2 \
  --with-requirements packaging/requirements.txt python tools/build_eador.py \
  --forecast-save /tmp/control-forecast.json
```

The standard package check runs without `--forecast-save`; the optional argument
adds the earned casualty diagnostic. `caffeinate` keeps the Mac display awake
only for this bounded native check.
