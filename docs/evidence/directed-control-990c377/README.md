# Directed Control continuation and development pacing — 2026-09-06

The earned Control opening at turn 6 now has **184 explicitly directed commands**
through first-shard victory at turn 9. The historical opening used autoplay;
every command in this continuation was selected by an agent with a recorded
reason. The root directed commands 1–97 and accepted the final result at 184;
the economic-depth agent directed the capital preparation and battle, 98–183.
No alternate simulations, rewinds, resource injections or autoplay were used
in the continuation. Rejected orders and tactical misunderstandings are disclosed
in the journal's observations.

The source is `commands[38]['before']` (zero-based index 38) in the retained
[Control journal](../shardbound-army-plans-cd351a9/control.json.gz), SHA-256
`6609eb4f334a956f6d6873e378b0b87bdd6901f3ad2f4688226265b8ede0b72a`.
The new [journal](journal.json.gz) authenticates that opening and all current
game/framework source files. Its original recorder is retained as
[director.py](director.py), including the original local paths. This recorder
applied only supplied public commands and reloaded each saved result.

## Actual decisions and cost

The continuation bought a Rune Adept and Skyrider for **150 gold, five crystals
and two actions**, permanently retiring a rank-3 Militia and Archer. Two Tower
infusions cost another **six crystals and two actions**. It used three ordinary
end turns; Oak Standard improved recovery and Moonstone supported combat.

| Battle | Campaign turn | Victory round | Fallen troops | Mana remaining |
|---|---:|---:|---|---:|
| Greenwater interception | 6 | 3 | None | 8 |
| Cinderwood conquest | 8 | 6 | None | 10 |
| Duskspire garrison | 9 | 10 | Militia #2, rank 3 | 1 |

Cinderwood combined Repulse with flight into the cleared space to protect a
wounded Adept. In the capital, coordinated attacks and lethal finishes avoided
several retaliations; four heals restored 88 HP. The capital's Militia death came
from an overlooked overlapping Guard attack. That mistake remains in the record.
Earlier mistaken assumptions about adjacent retaliation and marsh defense, and
one rejected movement, are also preserved.

After accepting the capital result, the campaign has **140 gold, nine crystals**,
a 28/44 HP Wizard and one mana. Survivors are Adept #6 (23/32 HP, rank 2),
Skyrider #7 (10/32, rank 2), Sapper #4 (9/34, rank 3), and Acolyte #5
(26/26, rank 2). The next offer and retinue remain unselected.

## Input verification and CPU evidence

Source **f78359d** adds one shared development input adapter and the authenticated
journal replay tool. It rejects stale models, fabricated openings, broken chains,
queries presented as commands, and autoplay in a directed journal. Each F5 check
reads the actual Manual 1 save; each F9 check requires a new live State object and
exact saved content. Review reproduced false passes for unhandled F5/F9 and a
query-only journal before these checks were strengthened.

Source **990c377** also paces the retained army-replacement prototype. Its battle
rounds and paired investment campaigns share the existing 25% CPU allowance;
`--cpu-percent 100` explicitly disables sleeping. This changes development tools
only. Game/framework bytes remain those of d643410.

**45 focused integration tests pass in 18.20 seconds** ([log](tests.log)). They
cover replay authenticity, actual input and saves, paid replacement, extraction,
support roles, linked-campaign transitions and CPU pacing. The added prototype
test compares one actual battle and the bounded investment pair with and without
yielding; reports and original input remain identical. Its RED was the missing
budget argument. No full prototype matrix or full-suite repeat was run.

One real native replay on **990c377** passes **794 inputs and 184 exact command /
save / reload joins** ([receipt](native/verification.json), [log](native.log)). It
took **66.37 seconds wall and 16.88 seconds CPU**, averaging **25.44% of one core**.
It used the default 25% cooperative allowance and existing 30 FPS native cap.
The allowance is not a strict operating-system quota or battery-life measurement.
All execution was serial; both test and native processes ended, and the native
backend closed. All 70 receipt source hashes match the recorded checkout.

The replacement review, Repulse result, and departure screenshots were inspected
at 125% reading size. Text and controls fit, the spent Repulse and nine-HP Adept
are visible, and the first-shard departure offers remain readable. All nine
captured frames are retained; the three inspected paths are listed in
[summary.json](summary.json).

```sh
uv run python tools/verify_eador_directed_journey.py \
  --input-report docs/evidence/directed-control-990c377/journal.json.gz \
  --output /tmp/shardbound-directed-check --backend pyglet
```

The two remaining linked shards, other directed builds, counter-scenarios and
independent human playtests remain open. This is source execution from an earned
save; the preserved Mac archive still predates the current autoplay change.
**All G01–G19 remain incomplete.**
