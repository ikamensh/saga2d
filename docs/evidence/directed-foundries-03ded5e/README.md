# Directed Control — Foundries departure

The same paid Wizard formation that completed the
[first shard](../directed-control-990c377/README.md) now completes Foundries
at turn 4. This checkpoint retains all **428 commands** from the authenticated
historical turn-6 opening; command 185 carries the two purchased veterans into
Foundries, and commands 186–428 are the directed second-shard continuation.
Game and framework source hashes remain unchanged from the previous checkpoint.

Root selected the Foundries contract and carried the actual Adept, Skyrider,
Moonstone and Oak Standard. The economic-depth agent chose subsequent commands
from the current state, reachable cells and forecasts. Every command has a
rationale and resumes from its exact serialized result. The director rejects
autoplay and source changes; it preserves each successful command immediately.
There were no rewinds, search branches, injected resources or model-field edits.
The historical opening before the journal used autoplay.

| Second-shard result | Observed value |
|---|---|
| Battles | Seven victories; 24 total rounds, 17 enemy phases |
| Troop casualties | Zero |
| Recovery | Three ordinary campaign rests; no recovery expedition |
| Buildings | Market 60g, Temple 65g, Mage Tower 75g/2c |
| Support purchases | Acolyte 45g, Sapper 60g/1c |
| Infusion | One ordinary purchase, 3c and one campaign action |
| Battle mana | 41 spent: 11 Heals for 33 mana, four Bolts for eight |
| Healing | 200 actual HP restored |
| Departure treasury | 158 gold, 17 crystals |
| Advancement | Wizard level 4, earned Channeling II and Restoration I |

The route captured Silverford, both foundries, the central checkpoint and
Cinderwood before intercepting the rival's surviving army. Equipment changed
to Oak Standard for normal rests and Moonstone for combat. The final capital
battle took eight rounds and exhausted the shared mana pool. All five troops
survived: Adept 34/36 HP, Skyrider 27/36, Militia 25/32, Acolyte 26/26 and
Sapper 6/30; the Wizard finished at 38/48 HP. A rejected Sapper path at command
254 and the resulting correction are disclosed in the observations. It was
not used to restore or replace earlier successful commands.

The [raw journal](journal.json.gz) and [director](director.py) preserve the
choices and states. The unchanged first-shard prefix already passed native
input verification; these additional commands have **not yet** been replayed
through native controls at this checkpoint. The third shard is still being
played. This is one agent-directed itinerary, not a human walkthrough, a
completed three-shard result or general balance evidence. All G01–G19 remain
incomplete.

The director uses one shared 25% cooperative CPU allowance; its command
processes ran serially and ended at this checkpoint. No CPU or battery-life
measurement is claimed for this manually paced stage. The separate
[fresh UI-only attempt](independent-ui.json) stopped at the locked Mac before
any screenshot or game input; its own app process was closed and it adds no
G09 evidence.
