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
New seed button. Saves use slot 1 in `~/.shardbound/saves`; saving replaces
that slot and loading restores the campaign, including an unfinished battle.

## Your first turns

1. Start with Commander. You have 100 gold, two militia, an archer and your
   hero. Press **B**, then **1** to build Barracks for 45 gold. Close with
   **Esc**, press **R**, then **2** to recruit a Swordsman for 45 gold.
2. Close recruitment. Select a province next to Westwatch and press
   **Enter** to invade. The neighboring western provinces have lighter
   defenders than the eastern approach to Duskspire.
3. In battle, click a friendly unit, then a blue reachable hex to move.
   Click an enemy marked as a target to attack. Keep the archer behind
   the front line; forest and hills reduce incoming attack damage.
4. Press **E** after your units act to let the enemy take its turn. **A**
   plays your remaining actions and the enemy turn automatically for one
   round; repeat it if you want assistance with the encounter.
5. After victory, press **E** to return to the shard. Your surviving troops
   keep their wounds and earn experience. The conquered province earns
   income. **X** explores a guarded site in the province where your hero
   stands, spending an action and starting another battle for treasure.
6. End a campaign turn with **E** to collect income, pay upkeep, heal and
   regain mana. Reinforce and work toward Duskspire. The rival first
   advances when turn 9 begins, then on turns 13, 17 and every four turns
   thereafter. Save with **F5** before a difficult expedition.

The starting army is usable immediately; Barracks is one possible opening,
not a required build. Marketplace provides income instead, while Wizard
starts with both spells and can invest elsewhere.

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
| Catalogue | Number key / click | Buy the corresponding building or troop |
| Shard | E | End campaign turn |
| Battle | Click friendly unit / Tab | Select unit / cycle units that can still act |
| Battle | Click empty hex / enemy | Move / attack with selected unit |
| Battle | 1 / 2, then click target | Cast Arcane Bolt / Heal |
| Battle | E | End round, or accept a completed battle's result |
| Battle | A | Auto-play one round |
| Battle | Retreat button | Withdraw with surviving troops and a gold penalty |
| Shard or battle | F5 / F9 | Save / load |
| Shard or battle | F1 | Open guide, including Save & title |
| Shard | Esc | Open guide |
| Battle | Esc | Cancel spell targeting, otherwise open guide |
| Catalogue or guide | Esc | Close overlay |

## Rules and scope

The campaign has 19 connected provinces, a single controllable hero and a
rival that expands along the frontier toward Westwatch. Travel and site
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

| Building | Cost | Benefit |
|---|---|---|
| Barracks | 45 gold | Recruit Swordsmen |
| Archery Range | 55 gold | Recruit Archers |
| Temple | 65 gold | Recruit Acolytes, learn Heal, improve recovery |
| Mage Tower | 75 gold + 2 crystals | Learn Arcane Bolt and gain 4 maximum mana |
| Marketplace | 60 gold | Add 8 gold income each turn |

Owned provinces provide gold and hills provide crystals; army upkeep is
deducted each campaign turn. Ending the turn restores health on friendly
land and 4 mana. Arcane Bolt deals 14 damage; Heal restores up to 16 health
to a living ally. Both cost 4 mana, have a range of four hexes and use the
hero's action. A move can precede an attack or spell; attacking or casting
ends that unit's movement. Surviving adjacent targets can retaliate once
per full round. Forest and marsh cost extra movement; forest and hills
provide cover. Ranged attacks use distance without line-of-sight blocking.

Capture Duskspire to win; taking every province is unnecessary. If the
rival reaches a province containing your hero, you fight a defensive
battle. Other targeted provinces change hands immediately. Losing
Westwatch ends the campaign. Retreating or losing an ordinary battle keeps
survivors' wounds and costs up to 20 gold; defending territory is lost on
retreat. New shard becomes available after victory or defeat.

This slice has no astral metacampaign, diplomatic simulation, karma,
rebellions, equipment inventory, multiclassing, multiplayer, fog of war or
the original games' large content catalogue. The rival's scheduled
expansion is a pressure system, not a second fully simulated player
economy. Tactical morale, stamina and spell preparation are simplified
away. Hero mana replaces Eador's prepared spells and gem costs; crystals
here fund construction rather than individual casts.

## Game and framework

`model.py` owns campaign commands, income, progression, opponent expansion
and serialization. `battle.py` owns movement permissions, combat and enemy
decisions. `scene.py` turns input into commands; `art.py` draws the world.
The rule modules are usable without a window and import Saga2D's general
`HexGrid` geometry/navigation primitive.

Saga2D owns drawing, input dispatch, scenes, UI and save slots. Hex layout,
picking, distance, reachable costs and routes are shared framework work;
terrain meaning, army ownership, action budgets, spells and victory remain
game rules. See the [HexGrid cookbook](../docs/framework-hexgrid.md) and
[framework design](../DESIGN.md).

The [research and scope notes](../docs/eador-research.md) cite the official
[Eador manual](https://store.steampowered.com/manual/232050) and
[Genesis store page](https://store.steampowered.com/app/235660/Eador_Genesis/),
and distinguish source mechanics from this adaptation's choices.
