# Army results — 2026-09-07

Completed ordinary PvE battles now apply wounds, casualties, earned advancement
and defeated-hero recovery through `eador.battle_results.apply_army_result`.
The function mutates only its supplied hero/army and returns casualty names and
earned hero levels. The battle stays unchanged. The caller retains province
claims, rewards, choices, economy and encounter cleanup.

Four focused tests pass: a paid two-victory advancement journey; standalone
Hero-only mutation; a real Observatory retaliation casualty followed by hero
death, without injected outcomes; and rejection of an unfinished battle.
The ordinary result path retains exact message order and save continuation.

94 tests pass in 1.76 seconds across army results, model, progression, rival,
Screen, and an earned linked-shard victory with advancement caps. The separate
bounded linked fuzz run passes four model campaigns and two scene runs in
20.0 seconds at 25% CPU. Its campaign and scene metrics exactly match the same
run before the army extraction: 517 model checks and 366 scene checks. All four
fuzz campaigns finish in defeat, so this is invariant coverage; the focused
linked-shard test supplies the separate victory/cap check.

```sh
.venv/bin/python -m pytest tests/eador/test_army_results.py tests/eador/test_model.py tests/eador/test_progression.py tests/eador/test_rival.py tests/eador/test_screen.py tests/eador/test_campaign.py::test_a_real_shard_victory_caps_advancement_and_opens_persistent_choices -q
.venv/bin/python tools/fuzz_eador.py --campaigns 4 --scenes 2 --steps 120 --linked --cpu-percent 25 --report /tmp/shardbound-army-results-fuzz.json
```

This is a game-local prerequisite for concurrent campaign PvE, not a playable
PvP mode or a framework interface. Ordinary tactical turns are unchanged.
