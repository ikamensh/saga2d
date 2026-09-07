# Seed 12 — declared Boots route outcome

The fresh Commander / Standard Frontier route reached its declared Stranded
Explorer reward endpoint on T3, with no actions remaining, 121 gold and 14
crystals. All six troops survived. The carrier escaped in round 2 with Boots
equipped; this is an opening-route result, not a completed linked campaign.

`route-seed12.json.gz` retains 112 accepted, explicitly agent-directed public
model commands, 19 attack forecasts, each command's rationale and exact saved
before/after join. No autoplay, injected resources, alternative seed, branch,
rewind, retirement, retreat or elective recovery was used. The two campaign
end-turns occurred with zero actions remaining, at commands 41 and 70.

| Turn | Declared encounter | Result | Party HP deficit before reward/advancement |
| --- | --- | --- | ---: |
| T1 | Westwatch Shrine | Rout, R2 | 5 |
| T1 | Amber Fields conquest | Rout, R2 | 3 |
| T2 | Amber Fields Explorer's Camp | Rout, R2 | 8 |
| T2 | Silverford conquest | Rout, R2 | 4 |
| T3 | Greenwater conquest | Rout, R2 | 2 |
| T3 | Greenwater Stranded Explorer, north | Escape, R2 | 15 |

The original financial forecast held: the Camp reward left 128 gold. The
Swordsman (45) and Archery Range (55) left 28, so the second Archer (35) waited
for Silverford's 25-gold conquest reward. Together with the opening Barracks
(45) and Warden (55), actual construction/recruitment spending was 235 gold.
The two mandatory rests contributed 18 and 23 net gold and one crystal each.
Explorer north charged no entry fee. Its 55-gold/one-crystal reward was claimed
once; the duplicate Boots offered and paid four crystals through `distill`.

Moonstone was kept and equipped through Greenwater. Three actual Heals cost
four mana each: eight HP to the Warden at Amber Fields, eight to the veteran
Archer at Silverford, and three to the Warden at Greenwater. Tactician was
chosen at both earned skill choices. Boots replaced Moonstone before Explorer,
so the extraction had terrain-free hero movement and no Heal available.

In Explorer R1, the carrier moved from (3,-1) to (0,1), across the plain at
(2,0), forest at (1,1) and marsh at (0,1). The Warden used the corridor vacated
by the new Archer to reach (-1,1), then Swapped the carrier west. The veteran
Archer and Swordsman killed the enemy Archer before it could Pin. Militia 2
vacated the marked exit and guarded its southern approach. After the actual
enemy phase, the carrier's reachable set included (-3,1); it moved there and
used the separate Evacuate order in R2. The surviving defenders were Pikeman
23/28, Guard 36/42 and Warden 28/38.

Final saved HP was hero 42/44; Militia 1 32/32; Militia 2 26/32; veteran Archer
28/28; Warden 41/46; Swordsman 36/38; second Archer 24/24. The hero retained
10/14 mana, Tactician 2 and equipped Boots; Moonstone remained in inventory.
The rival still had its original six full troops at Blackfen, 98 gold and one
turn until its planned Frostmere attack. No interception occurred before this
stopping point.

One rejected order is retained after accepted command 32: the attempted
Commander move to (-1,1) at Amber Fields was out of reach because the chosen
intermediate Militia square still blocked the route. It changed no state.
The valid preceding orders were kept, and the second Militia made the legal
southern continuation. An endpoint observation's wording about the three-step
Boots crossing was clarified by an appended observation; no orders or saved
states were rewritten.

The director authenticated the fresh linked-campaign initial state against the
retained zero-order predecessor, SHA256
`6927b65bcb5fb21338af2344c2273db32613c062329bba7cb0e55186bd2da66a`.
Execution began at `51d4e117aec9e2bc14591d500484b4f2737b8e2e`; every request checked
the frozen Eador/framework/adapter source manifest. All requests used the
shared OS-lock wrapper around the director and its `CpuBudget(25)`. This is a
cooperative allowance, not a measured CPU percentage. Native input coverage
must come from the separately retained UI replay, not this model journal.

Journal bytes SHA256:
`867d46b3f50c286ff1d4f0b6d344301a78908ec28ef90bed5009471ff99bfea4`.
