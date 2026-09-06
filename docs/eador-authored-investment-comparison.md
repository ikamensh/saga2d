# Earned specialist investment at authored objectives

The small paid Sapper choice has demonstrable value at Runebound Causeway. The
whole Sapper/Adept/Skyrider conversion still has not earned a general economic
role. This is a bounded two-window Commander pilot, not a balance matrix or a
G07 completion claim. No game or Saga2D source changed.

The existing early-conversion harness now captures the first full, friendly army
on turns 5–7 that can afford a Sapper, while executing the unchanged Economy/direct
policy. The observed full campaign result equals the unobserved result. Each
alternative starts from that exact earned save and uses ordinary construction,
recruitment, retirement, actions, movement, automatic tactics and reward choices.
Funding waits intercept the actual nearby rival and recheck its position. They do
not simply neglect the capital to make expensive plans look bad.

The retirement policy preserves ranged troops where possible, releasing the
lowest-rank/XP Militia or Swordsman first. It pays normal current prices and gives
no refund, reserve or XP transfer. A real casualty during preparation can instead
leave an ordinary recruitment slot. Every branch records those differences.

## Ruins: one useful purchase, an expensive faster tactical round

Seed 0, Standard Commander reaches the captured turn-six camp with **104 gold and
23 crystals**. The rival at `(0,-1)` announces an attack on `(-1,0)` in two turns.
All preparations target the same unaltered Causeway and retain that finite rival.

| Preparation | Additional gold / crystals | Causeway completion | Troops killed through completion | Missing HP at tactical result |
|---|---:|---|---:|---:|
| Keep army, leave now | 0 / 0 | T7, R4 rout | 0 | 45 |
| Keep army, wait to T7 before leaving | 0 / 0 | T8, R4 rout | 0 | 22 |
| One Sapper | 42 / 1 | T8, R4 rout | 0 | 12 |
| Tower and one Adept | 121 / 4 | T8, R4 rout | 0 | 56 |
| One Skyrider | 60 / 3 | T8, R5 rout | 1 | 3 |
| Sapper + Tower + Adept | 163 / 5 | T8, R3 rout | 0 | 46 |
| Staged full conversion | 223 / 8 | T10, R4 rout | 1 | 27 |
| Fund whole conversion before purchasing | 223 / 8 | T11, R5 rout | 1 | 29 |
| Keep army, wait to T9 before leaving | 0 / 0 | T10, R4 rout | 0 | 2 |
| Keep army, wait to T10 before leaving | 0 / 0 | T11, R4 rout | 0 | 2 |

Wounds include the hero and living troops before post-victory advancement. Dead
bodies disappear from the wound total, so the Skyrider's three wounds are not an
improved army. Each single-role purchase retires one soldier; the pair retires two;
the full conversions retire three. The Sapper replaces a rank-one, zero-XP
Swordsman. It does not demonstrate that retiring an experienced Militia is equally
attractive.

The Sapper and T8 retained-party control both enter fully healed, spend four mana,
finish R4 and lose nobody. The Sapper purchases ten fewer wounds for 42 gold, one
crystal, one soldier retirement and one campaign action. Keeping the army can
instead complete a full campaign turn earlier with more wounds. These are different
maximum-health armies: the Sapper line has 246/258 living HP, compared with
244/266 for the retained Swordsman line. Ten fewer wounds means only two more
remaining HP, and the replacement also trades attack and defense for Smoke.
The direct Smoke/Guard comparison below holds composition fixed. The pair saves a
battle round at T8 but costs 121 additional gold/four crystals over Sapper and ends
with 34 more wounds. Neither faster battle completion nor lower treasury alone
makes it the better investment.

A direct tactical control establishes that Sapper's charge matters. From its
actual round-three save, **Smoke at `(3,-2)`** followed by the normal automatic
policy ends R4 with 12 missing HP. **Guard** instead ends R4 with 23. Both spend
the Sapper's order, finish with the same two mana and no deaths. The Smoke result
matches the original paid battle exactly when compared in serialized form.
These are two public choices; no ability, terrain, income or defender was edited.
Guard leaves the charge available, and a later automatic round still uses Smoke.
The comparison therefore demonstrates the value of screening at the earlier
decision, rather than removing the ability from the alternative army.
The two choices can cause the same subsequent automatic policy to select different
actions. They are not proof of optimal manual tactics or native input coverage.

## Elderwild: timing costs without a useful complete bundle

The second window is turn six, **63 gold / 16 crystals**, with a wounded rival
already at Duskspire announcing paid recovery in one turn. Kept troops clear the
same Supply Cache on T7/R2 without deaths, with 14 missing HP. Sapper costs 42/1
and finishes at the same date with 25 wounds. Skyrider costs 60/3 and produces 13
wounds at that date. Both retire the same rank-one, zero-XP Swordsman.

The pair costs 163/5 and reaches T12/R2, with 13 wounds and two retirements. Staged
full conversion costs 223/8 and reaches T14/R2, with 15 wounds and three
retirements. Nobody dies before that staged objective, but a real battle during
its separately recorded two-turn aftermath kills one troop. Funding the whole
bundle first reaches T15/R3 after three combat deaths and two retirements; an
actual casualty opened the third normal recruitment slot. The corresponding
no-purchase T14 waiting control also loses three troops before its T15 objective.
Those losses therefore cannot be attributed solely to specialist recruitment.

## Evidence and remaining work

The complete pilot retains **21 alternative branches**, each repeated, with an
exact public-order replay from every tactical-phase save. It includes both
windows, same-clock waiting controls, prices, lost identities, fights, complete
endpoints and two separate aftermath turns. Seed-zero Frontier's captured window
already had its dynamically placed Relief site explored, so that case was
explicitly excluded instead of resetting the site.

The larger three-seed/four-class/three-theme/three-mode run was **interrupted with
exit 143** after the user reported CPU and battery pressure. Its aggregate was not
written, so its partial console lines are not counted as completed comparison
cases. The tool now defaults to one Commander/Ruins/Standard seed-zero window and
a cooperative 25% allowance of one CPU core. Larger selections must be explicit,
and heavy jobs run serially. The wider class/theme/difficulty comparison remains required before
any general economy recommendation.

The pilot was invoked before committing the tool; its recorded source hashes
match committed **`e5a13ce`**, including the complete game source used. The
[retained evidence](evidence/earned-specialist-investment-e5a13ce/provenance.json)
records this provenance, the interrupted handle and checksums. The
[complete pilot](evidence/earned-specialist-investment-e5a13ce/authored-commander-pilot.json.gz)
and [executed Smoke/Guard control](evidence/earned-specialist-investment-e5a13ce/paid-sapper-control.json.gz)
contain the actual saved inputs and outcomes. The existing capital comparison's
20 branches and paid retry were also rerun successfully before the tool commit.

The follow-up command is bounded by explicit seed/class/theme/mode selections;
run one small selection at a time when test load is permitted:

```sh
uv run python tools/prototype_eador_early_conversion.py --authored --seeds 0 --heroes Commander --themes ruins --modes standard --repeat --report /tmp/earned-investment.json.gz
uv run python tools/prototype_eador_early_conversion.py --tactical-control-from /tmp/earned-investment.json.gz --report /tmp/earned-smoke-control.json.gz
```

The original source/model control invocation hit a tuple/list comparison in its
final assertion. Comparing the serialized battle form fixes it. A fresh clean
`4c555b2` invocation now passes, following a repeated one-window Commander/Ruins
pilot with ten branches, both at the default 25% CPU allowance. The original
twenty-one-branch evidence remains historical; the larger matrix was not resumed.

The [current reproduction](evidence/earned-specialist-investment-4c555b2/README.md)
also resumes the earned round-three save through real native F9 input and issues
Smoke or Guard through the displayed controls. **51 native inputs and seven
exact reloads** reproduce both model continuations and final campaign states.
The preparation was performed by the model, so this is native decision/continuation
coverage, not a native whole paid journey or a human playtest.

Review found a separate harness bug: waiting for actions could intercept the rival,
move away from the intended site and then explore the wrong province. A regression
from the actual paid Ruins camp targets Sealed Vault; it failed before the fix and
now passes after returning to the intended site. Every recorded target fight now
asserts its actual battle province and site kind. The twenty-one historical branches
were checked and already targeted the right sites; this correction does not invalidate
their measured outcomes. Fourteen focused audit/budget integration tests pass.

Do not add a tax or relocate crystal income on this evidence. A purposeful small
purchase is already available and can trade an action/retirement for less damage;
the larger conversion performs worse in these examples. The next useful question
is how often players can identify and choose that local tradeoff across different
openings, rather than how to make them consume their remaining money.
