# Shardbound

An Eador-inspired strategy game built on Saga2D. Develop a stronghold,
explore guarded sites, lead a persistent army through hex battles, and
capture Duskspire before the rival takes Westwatch. It is an independently
implemented single-shard adaptation with procedural art.

From the repository root:

```bash
uv sync --extra dev
uv run python -m eador                       # title and hero selection
uv run python -m eador --seed 7              # start immediately as Commander
uv run python -m eador --seed 7 --hero Wizard
uv run python -m pytest tests/eador -q
```

`--hero` accepts `Commander`, `Warrior`, `Scout` or `Wizard` when starting
directly with `--seed`. The title screen has its own class selection and
New seed button. Saves live in `~/.shardbound/saves`. **F6** opens three
manual slots and three rolling autosaves. **F5/F9** quickly save/load Manual
1. Campaign actions and battle rounds checkpoint automatically; pending
battles and reward decisions resume exactly where saved. Each slot also
retains its previous version, opened explicitly with **Backup** or
**Shift + the slot's displayed number**. Damaged or incompatible files are
reported without replacing live play; recover a backup and save to another
manual slot. **Save & title** asks for a slot and leaves only after writing it.

## Your first turns

1. Start with Commander. You have 100 gold, two militia, an archer and your
   hero. Press **B**, then **1** to build Barracks for 45 gold. Close with
   **Esc**, press **R**, then **2** to recruit a Swordsman for 45 gold.
2. Close recruitment and press **X** to explore Westwatch's guarded site.
   This first expedition earns treasure and experience before you advance.
3. In battle, click a friendly unit, then a blue reachable hex to move.
   Click an enemy marked as a target to attack. Keep the archer behind
   the front line; forest and hills reduce incoming attack damage.
4. Press **E** after your units act to let the enemy take its turn. **A**
   plays your remaining actions and the enemy turn automatically for one
   round; repeat it if you want assistance with the encounter.
5. After victory, press **E** to return with treasure and experience.
   Resolve any skill or relic decisions with **1/2**. Keeping a relic adds
   it to your inventory; **H**, then its number equips it. Press **E**
   on the shard to end the campaign turn, collect income,
   pay upkeep, heal and regain mana. Build a Temple when you can afford
   its 65 gold, then fill free troop slots with Swordsmen.
6. Move east through Silverford, Heartwood and Cinderwood: select an
   adjacent province and press **Enter** to invade. Rest after each
   conquest, explore its site with **X**, then rest again. Invest the
   rewards in recovery and reinforcements; every conquered province also
   adds income.
7. Before attacking Duskspire, restore every unit to within about 6 health
   of its maximum. Its five Dread Guards and two Archers demand a prepared
   army. A direct rush with the starting troops is unlikely to succeed.
8. The rival starts with three eastern provinces and first advances when
   turn 5 begins, then on turns 9, 13, 17 and every four turns thereafter.
   An unopposed advance can reach Westwatch on turn 17. Save with **F5**
   before a difficult expedition.

The starting army is usable immediately; Barracks is one possible opening,
not a required build. Marketplace provides income instead, while Wizard
starts with both spells and can invest elsewhere.
The investment-and-exploration route above wins the seed-7 Commander
campaign in the integration journey using automatic battles; manual decisions and different
seeds can change the outcome. For Wizard, a Mage Tower before the Temple
adds mana to support the two spells already learned.

## Controls

| Screen | Input | Action |
|---|---|---|
| Title | Tab / click class | Choose hero class |
| Title | Enter / Space | Start the selected shard |
| Shard | Click province | Select and inspect it |
| Shard | Tab | Cycle provinces adjacent to the hero |
| Shard | Home | Select the hero's current province |
| Shard | Enter / Space | Travel to or invade the selected adjacent province |
| Shard | X | Explore the hero's current province |
| Shard | B / R | Open construction / recruitment |
| Shard / decision | H | Inspect skills and equip relics |
| Decision | 1 / 2 | Choose the corresponding skill or reward |
| Hero | 1–4 / U | Equip a visible relic / unequip |
| Hero | Left / Right | Previous / next inventory page |
| Catalogue | Number key / click | Buy the corresponding building or troop |
| Shard | E | End campaign turn |
| Battle | Click friendly unit / Tab | Select unit / cycle units that can still act |
| Battle | Click empty hex / enemy | Move / attack with selected unit |
| Battle | Arrows / Page Up / Page Down | Aim at neighboring hexes (Page keys provide the other two diagonals) |
| Battle | Enter / Space | Select, move, attack or cast at the aimed hex |
| Battle | F | Cycle enemy targets, or friendly targets while aiming Heal |
| Battle | 1 / 2, then click target | Cast Arcane Bolt / Heal |
| Battle | E | End round, or accept a completed battle's result |
| Battle | A | Auto-play one round |
| Battle | T / Retreat button | Withdraw with surviving troops and a gold penalty |
| Shard, battle or decision | F5 / F9 | Quicksave / quickload Manual 1 |
| Title, shard, battle or decision | F6 | Open all saves |
| Saves | 1–6 / Shift + 1–6 | Load a slot / recover its previous version |
| Saves | Tab | Switch Save / Load; only manual slots can be overwritten |
| Shard or battle | F1 | Open guide, including Save & title |
| Shard | Esc | Open guide |
| Battle | Esc | Cancel spell targeting, otherwise open guide |
| Catalogue or guide | Esc | Close overlay |

## Rules and scope

The campaign has 19 connected provinces, a single controllable hero and a
rival that starts with three eastern provinces and expands along the
frontier toward Westwatch. Initially, central provinces have three defenders, the
eastern approach has four, and Duskspire has seven. Travel and site
exploration spend campaign actions: two per turn, or three for Scout.
Construction and recruitment spend resources without consuming actions;
recruitment is available in any province you control. There is one guarded
site per eligible province, resolved in a single expedition.

| Class | Difference |
|---|---|
| Commander | Six troop slots and +1 troop attack |
| Warrior | +12 starting health and +4 hero attack |
| Scout | Three campaign actions and ranged hero attacks |
| Wizard | +6 starting mana and both spells already learned |

Other classes have five troop slots. Troops are individual fighters, not
stacks. Victories improve the hero and surviving veterans; dead troops are
lost. The four recruitable types are Militia, Swordsman, Archer and Acolyte.
Acolytes improve campaign recovery; spellcasting belongs to the hero.

Each level offers two class disciplines. Choose a new discipline or deepen
one already learned, up to rank three. Commander balances recruitment and
recovery against retaliation-free troop attacks; Warrior chooses safe,
stronger strikes or healing; Scout chooses terrain traversal or attacking
before moving away; Wizard specializes in cheaper Bolt or stronger,
cheaper Heal. **H** shows learned effects.

Six sites have different defending parties and gold/crystal rewards:
Buried Shrine, Forgotten Tower, Old Barrow, Wolf Den, Lost Caravan and Elder
Grove. Winning offers a relic or its gold value. Keep and equip one of six
relics to gain healing or damage spells, avoid retaliation, cross difficult
terrain, improve army recovery or reduce recruitment costs. Duplicate
relics can instead be distilled into four crystals. These choices belong
to this adaptation; they do not reproduce the commercial game's catalogue.

| Building | Cost | Benefit |
|---|---|---|
| Barracks | 45 gold | Recruit Swordsmen |
| Archery Range | 55 gold | Recruit Archers |
| Temple | 65 gold | Recruit Acolytes, learn Heal, improve recovery |
| Mage Tower | 75 gold + 2 crystals | Learn Arcane Bolt and gain 4 maximum mana |
| Marketplace | 60 gold | Add 8 gold income each turn |

Owned provinces provide gold and hills provide crystals; army upkeep is
deducted each campaign turn. Ending the turn restores health on friendly
land and 4 mana. Before skill and relic modifiers, Arcane Bolt deals 14 damage; Heal restores up to 16 health
to a living ally. Both cost 4 mana, have a range of four hexes and use the
hero's action. A move can precede an attack or spell; attacking or casting
ends that unit's movement unless the Scout's Skirmisher discipline allows
an attack followed by movement. Surviving adjacent targets can retaliate once
per full round. Forest and marsh cost extra movement; forest and hills
provide cover. Ranged attacks use distance without line-of-sight blocking.

Capture Duskspire to win; taking every province is unnecessary. If the
rival reaches a province containing your hero, you fight a defensive
battle. Other targeted provinces change hands immediately. Losing
Westwatch ends the campaign. Retreating or losing an ordinary battle keeps
survivors' wounds and costs up to 20 gold; defending territory is lost on
retreat. New shard becomes available after victory or defeat.

This slice has no astral metacampaign, diplomatic simulation, karma,
rebellions, multiclassing, multiplayer, fog of war or
the original games' large content catalogue. The rival's scheduled
expansion is a pressure system, not a second fully simulated player
economy. Tactical morale, stamina and spell preparation are simplified
away. Hero mana replaces Eador's prepared spells and gem costs; crystals
here fund construction rather than individual casts.

## Game and framework

`model.py` owns campaign commands, income, progression, opponent expansion
and serialization. `battle.py` owns movement permissions, combat and enemy
decisions. `scene.py` turns input into commands; `art.py` draws the world.
`content.py` holds authored skills, sites and relics. `persistence.py`
owns the campaign schema boundary, manual slot policy and autosave rotation.
The rule modules are usable without a window and import Saga2D's general
`HexGrid` geometry/navigation primitive.

Saga2D owns drawing, input dispatch, scenes, UI and save slots. Hex layout,
picking, distance, reachable costs and routes are shared framework work;
terrain meaning, army ownership, action budgets, spells and victory remain
game rules. Measured paragraph wrapping is another framework responsibility:
the game supplies text and available width, while Saga2D fits actual font
metrics. This removes character-count guesses from guides and catalogues.
See the [HexGrid cookbook](../docs/framework-hexgrid.md) and
[framework design](../DESIGN.md).

The [research and scope notes](../docs/eador-research.md) cite the official
[Eador manual](https://store.steampowered.com/manual/232050) and
[Genesis store page](https://store.steampowered.com/app/235660/Eador_Genesis/),
and distinguish source mechanics from this adaptation's choices.
