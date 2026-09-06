# Earned Scout paths: two directed continuations

These are two agent-directed examples from the same historical Scout save:
[`mobile.json.gz`](../shardbound-army-plans-cd351a9/mobile.json.gz)
`commands[14].before` (zero-based), pending the first skill choice. That opening
used autoplay. The anchor is T2, Silverford, 25g/7c, two actions, level 2,
40/40 hero HP, 12 mana and six missing army HP. No autoplay was used in either
continuation. Root directed Pathfinder; a delegated agent directed Skirmisher.

Both chose their declared skill twice and followed Silverford Shrine → Briarwood
→ Raven Hill → Border Watch → Greenwater → Stranded Explorer (north). Each bought
Ranger #5 for 50g, then replaced Militia #1 with Ranger #6 for 50g and one action.
Each took the two prescribed end-turns after exhausting campaign actions, with
actual recovery, income and rival response. No additional recovery turn or final
rest was taken. Moonstone stayed equipped; Watch Bell and Wayfarer Boots were
kept unequipped. Militia #1 was retired through replacement, not killed.

| Observed result | Pathfinder 2 | Skirmisher 2 |
|---|---:|---:|
| Persisted commands | 111 | 114 |
| Battles won / attempted | 6 / 6 | 6 / 6 |
| Battle casualties | 0 | 0 |
| Sum of final saved battle rounds | 11 | 12 |
| Explicit enemy phases | 6 | 7 |
| Pin commands | 3 | 0 |
| Heal casts / mana spent | 1 / 4 | 0 / 0 |
| Final missing hero / army HP | 0 / 13 | 4 / 17 |
| Final turn / remaining actions | 4 / 1 | 4 / 1 |
| Final gold / crystals / mana | 192 / 18 / 14 | 192 / 18 / 14 |

Each received 225g/5c from battles, 42g/2c from end-turns and 4c from distilling
the duplicate Moonstone; spending was 100g/0c. Pathfinder's Heal restored 11
Archer HP at Raven Hill. Its final army wounds are Militia 10 and Archer 3;
Skirmisher's are Militia 12, Archer 2 and Ranger #5 three. These are snapshot
wounds, not cumulative damage: healing and promotions remain in the records.

Pathfinder's Briarwood rout finished during the round-1 enemy phase. Both Watch
wins were round-2 **routs**, with hold progress zero; Skirmisher required a second
enemy phase there. Both Explorer outcomes were round-2 **escapes** using a screened
exit and Warden Swap: one enemy Archer died and three defenders withdrew.
Skirmisher used the hero's attack-then-move at Watch and Explorer; Rangers already
have that ability in both branches. Different positioning, Pin and Heal choices
prevent attributing the outcome differences solely to the chosen skills.

Pathfinder's observations retain one rejected, unsupported `choose('keep')`
request after command 71. It did not mutate the save; the actual offered `take`
was then used. Successful command counts exclude that rejection. Neither branch
retried a battle or rewound a successful command.

| Provenance | Recorded source |
|---|---|
| Historical journal | `2d775de99dd1699d8f71e34e9cf63e4c4e57cda2` |
| Pathfinder execution | `78cb545e3f961e49018ab8eff2460f5f15673d10` |
| Skirmisher execution | `36aaaa277f55b86a1081d7cded1f1e1207b2dd74` |
| Both native replays | `49d5b656e9f41e58bab06dcf7eb5ce67db8f6231` |

The original execution manifests are identical despite the different recorded
HEADs. Their game/framework hashes also match the native receipts. Directory and
temporary filename suffixes are not substitutes for these source fields.

| Native receipt | Commands / reloads / inputs | Wall / process CPU seconds | CPU ÷ wall |
|---|---:|---:|---:|
| [Pathfinder](pathfinder-native/verification.json) | 111 / 111 / 457 | 46.2894 / 11.7471 | 25.38% |
| [Skirmisher](skirmisher-native/verification.json) | 114 / 114 / 461 | 39.5789 / 10.0149 | 25.30% |

Both `pyglet` receipts report `source_unchanged: true`, exact final-state equality
and a requested 25% cooperative CPU budget. The ratios are process averages,
not instantaneous caps or battery measurements. PNGs, logs and receipts are
retained verbatim; the reports list nine/eight milestone captures respectively,
with additional briefing/replacement images also retained.

[`summary.py`](summary.py) reads only JSON and prints deterministic
[`summary.json`](summary.json). It verifies the historical anchor hash, every
saved command join, treasury deltas and native input/final joins; it does not
re-execute rules. From this directory, regenerate with
`python3 summary.py > summary.json`. The copied [`director.py`](director.py)
retains its original temporary paths as an execution record. [`SHA256SUMS`](SHA256SUMS)
covers every other retained file.

This is not a human playtest, a native opening, a complete campaign, an optimal
policy or an isolated causal balance experiment. Both saves remain stage 1,
`playing`, with the rival targeting Greenwater two turns later. No G01–G19 gate
is closed by this archive.
