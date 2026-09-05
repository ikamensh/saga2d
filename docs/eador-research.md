# Eador reference and scope

Research date: 2026-09-05. This is an independently implemented, compact
Eador-inspired game and a second demanding client of Saga2D. The target is
a complete, replayable single-shard campaign with original presentation;
content parity with the commercial series is outside this increment.

## What the reference establishes

Eador combines territory strategy, individual tactical combat and hero
progression. Genesis advertises more than 170 buildings, 80 spells and 70
units: its catalogue is much larger than the minimum needed to exercise
that combination. [Official Genesis store page](https://store.steampowered.com/app/235660/Eador_Genesis/)

The publisher's 21-page *Masters of the Broken World* manual supplies the
concrete mechanical reference. Printed page numbers are used below:

| System | Verified reference |
|---|---|
| Heroes, pp. 4–5 | Warrior, Scout, Commander and Mage lead armies and explore provinces. |
| Stronghold, pp. 6–8 | Construction prerequisites unlock troops, equipment, spells and economic improvements. |
| Armies, p. 9 | Soldiers are individuals, gain experience and require upkeep; travel requires a hero. |
| Economy, p. 10 | Gold funds construction and recruitment; gems pay for spellcasting. Provinces provide tax income. |
| Provinces, pp. 11–13 | Conquest or negotiation gains territory. Provincial upgrades and guards differ from stronghold construction. |
| Tactics, pp. 15–16 | Armies alternate turns. Heroes fight on the field; health, morale, stamina and terrain matter. |
| Exploration, p. 18 | Searching owned provinces reveals guarded sites and improves development; capturing enemy capitals wins the shard. |
| Magic, p. 19 | Combat spells consume gems and prepared uses; strategic rituals are separate. |

Source: [official manual distributed through Steam](https://store.steampowered.com/manual/232050),
also [hosted by Snowbird Games](https://snowbirdgames.com/files/eador/eador_mbw_manual_en.pdf).
The manual establishes mechanics; its exact balance formulas are not specified.

The official sequel description presents floating shards and competing
Masters, and explicitly identifies strategy, tactics and RPG systems as
its combination. [Official Masters of the Broken World store page](https://store.steampowered.com/app/232050/Eador_Masters_of_the_Broken_World/)

## Selected playable slice

The following are implementation choices for this project, not claims
about the original game's exact rules or quantities.

The player should start a generated shard, build and recruit, choose
between expansion and local exploration, fight a tactical battle, return
with surviving veterans and rewards, improve the realm, and defeat a rival
stronghold. An opponent must expand and threaten the player so the economy
and path to victory have consequences. Losing the player's stronghold must
produce an equally complete defeat state.

The selected scope is a compact, 19-province shard readable without a
minimap, one player hero, one rival power, and short battles with small
armies. Four starting hero classes change play: Warrior, Scout, Commander
and Wizard. Five stronghold buildings cover economic growth, recruitment,
magic and recovery.

| Area | Concrete scope target |
|---|---|
| Strategy | Seeded connected provinces, ownership, visible adjacency, local exploration, sites, healing/resting, rival expansion. |
| Economy | Gold and crystals, explicit income/upkeep, building costs and unlocks; choices should show their consequences before acting. |
| Development | Five useful buildings covering economy, military recruitment, magic and recovery. No decorative upgrades. |
| Army | Distinct melee, ranged and durable troop roles; persistent casualties and hero experience. |
| Tactics | Separate hex field, legal movement highlights, melee/ranged attacks, retaliation, terrain effects, at least one useful spell, and enemy turns. |
| Campaign | Encounters feed casualties, experience, territory and treasure back into strategy exactly once. |
| Usability | Title/help, clear action availability, turn indication, restart, save/load, readable battle outcome and victory/defeat. |

Choose a small set of original unit names, encounters and procedural art.
Use deterministic combat previews wherever possible so players understand
what the rules will do. Keep simplified initiative, damage, healing and
income rules explicit in the game documentation. This adaptation deliberately
uses a hero mana pool for tactical spells instead of the reference game's
prepared spell uses. That choice reduces preparation bookkeeping and is
a game rule, not a Saga2D magic abstraction.

This increment omits the astral metacampaign, branching authored story,
diplomatic factions, racial alliances, karma, rebellion simulation, advanced
hero multiclassing, large equipment inventories, multiplayer, and the
commercial games' content catalogue. These are deferred game features, not
unimplemented framework promises.

## Framework boundary

The existing architecture already supplies rendering, camera/input spaces,
scene ownership, reactive labels, buttons, overlays and save slots. Reuse
those before inventing abstractions. Read `DESIGN.md` as the current contract.

| Put in Saga2D when exercised | Keep in the game |
|---|---|
| Hex coordinate conversion, neighbors, distance and polygon corners: useful independently of fantasy rules. | Province ownership, exploration and generated encounters. |
| A small generic weighted search helper, only if both reachability and AI need it concretely. | Movement costs, occupancy, attack range and tactical combat formulas. |
| Callable button availability/text, if repeated state synchronization proves cumbersome. | Available campaign commands, building prerequisites and resource affordability. |
| Existing scene-stack and save-slot conveniences. | Campaign state, battle outcome application and serialization schema. |
| General drawing/input/layout fixes demonstrated by both reference games. | Hero classes, troop data, spells, opponent decisions, economy and victory. |

Avoid a universal strategy-game engine, an entity-component rewrite, or a
generic economy/quest system. The useful abstraction test is whether a game
author can express an intent with less bookkeeping while retaining ordinary
Python rules. Two games should share a primitive, not inherit each other's
domain model.

## Completion evidence

Integration tests should traverse recruitment, movement into an encounter,
tactical actions and resolution back to the campaign; demonstrate income
and upkeep, exploration rewards, a save/load continuation, and victory and
defeat. Invariants should survive multiple generated seeds and automated
campaign turns. Play through real mouse and keyboard input, render the
strategic and tactical scenes through pyglet, and inspect the screenshots
before calling the slice complete. Keep the existing Tribes suite passing.
