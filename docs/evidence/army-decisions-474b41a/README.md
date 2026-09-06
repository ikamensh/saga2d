# Two earned tactical decisions — 6 September 2026

`tools/audit_eador_army_decisions.py` resumes exact saves from the paid army-plan
journals, compares disclosed orders with autoplay, resolves real rewards and
attempts immediate affordable purchases using the same roster policy. Every
command continues from its exact serialized state. No resources, troops or ranks
are injected. These cases have no native input, rest or whole-campaign credit.

| Earned input / branch | Result | Fallen | Living HP | Immediate purchases |
|---|---|---:|---:|---|
| Control / autoplay | Player, round 5 | Rune Adept | 138 | 65 gold, 2 crystals |
| Control / other ready attackers first | Player, round 5 | None | 140 | None |
| Mobile / autoplay | Player, round 5 | Warden | 126 | 55 gold |
| Mobile / withdraw Warden, Guard, autoplay | Player, round 5 | Militia | 122 | 20 gold |

All branches finish with two mana and restore their target roles through actual
purchases. Control preserves the existing 2-HP Adept by moving the Wizard and
using the Wizard, Acolyte and Skyrider to finish the last Guard before exposing
the Adept to retaliation. Mobile preserves its 2-HP Warden but transfers the
casualty to a cheaper troop; it saves 35 gold while leaving four less living HP
and more wounds. It is a tradeoff, not an unqualified better result.

The inputs are commands 80 and 42 respectively in the retained Control and
Mobile journals; report provenance includes file/save hashes and stage/battle
indices. Each first autoplay result exactly matches its original journal.
The Control paid-replacement tracer passed; both CLI cases completed at 25% CPU:

```sh
uv run --extra dev python tools/audit_eador_army_decisions.py --plan control --output /tmp/shardbound-control-decision.json.gz
uv run --extra dev python tools/audit_eador_army_decisions.py --plan mobile --output /tmp/shardbound-mobile-decision.json.gz
```

Reports retain their pre-commit base `1aab5b7`. All 71 recorded source hashes
in each match committed `474b41a`; see `source-verification.json`. G04 remains
incomplete: two local orders do not establish three robust manual army plans.
