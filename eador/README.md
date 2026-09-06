# Shardbound

An Eador-inspired strategy game built on Saga2D. Develop a stronghold,
explore guarded sites, lead a persistent army through hex battles, and
capture Duskspire before the rival takes Westwatch. Its three-shard linked
campaign and quick standalone mode use original content and procedural art.

From the repository root:

```bash
uv sync --extra dev
uv run python -m eador                       # title and hero selection
uv run python -m eador --seed 7              # start immediately as Commander
uv run python -m eador --seed 7 --hero Wizard --theme elderwild
uv run python -m eador --campaign --seed 7 --hero Commander
uv run python -m pytest tests/eador -q
```

On the title, **L** begins a linked campaign with your hero and seed, starting
in Frontier. **Enter** starts one standalone shard in your selected world.
Linked victories offer two next challenges, followed by a choice of up to
two surviving veterans and two relics. Use **Left/Right**, **Up/Down** and
**Space** to choose a retinue, then **Enter** to depart; **Esc** returns to
challenge comparison. Learned skills persist, traveling health and mana
recover, and local holdings and buildings stay behind. A first lost capital
offers one recovery expedition; another loss ends the run. See the
[linked campaign guide](../docs/eador-linked-ui.md) for carryover and saves.
**J** opens your current contract, numbered map objectives, rank limits and
recovery status. Its numbered **Locate** controls select a required province
without spending an action. The final ritual's briefing shows the deployment,
seal, defending army and deadline before you commit the assault. Retinue
pages also have mouse-accessible **Previous / Next** controls.

`--hero` accepts `Commander`, `Warrior`, `Scout` or `Wizard`; `--theme` accepts
`frontier`, `elderwild` or `ruins`. With `--seed` they start that world directly;
otherwise they preselect the title choices. Frontier has mixed borders,
Elderwild a wet interior and a longer merchant road, and Ruins defended
checkpoints with weaker, poorer flanks. The title explains these choices and
provides hero, world and seed controls. Saves live in `~/.shardbound/saves`. **F6** opens three
manual slots and three rolling autosaves. **F5/F9** quickly save/load Manual
1. Campaign actions and battle rounds checkpoint automatically; pending
battles and reward decisions resume exactly where saved. Each slot also
retains its previous version, opened explicitly with **Backup** or
**Shift + the slot's displayed number**. Damaged or incompatible files are
reported without replacing live play; recover a backup and save to another
manual slot. **Save & title** asks for a slot and leaves only after writing it.

**O** opens settings from the title or field guide. **S / D** selects Sound
or Display. Arrow keys or visible buttons adjust volume, mute, window size,
fullscreen and reduced motion; **Enter** applies, **Esc** cancels the preview.
Reduced motion keeps battle damage and healing numbers still. The logical
canvas stays the same size and letterboxes to fit the window.
Preferences live separately in `~/.shardbound/settings.json` and survive
loading another campaign. Damaged settings are reported and kept until you
explicitly choose retained recovery. Original campaign/battle music and action
cues are included; settings affect music and effects already playing. Listening
and mix review remain part of release preparation.

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
   adjacent province and press **Enter** to invade. Check **V** before
   spending turns on recovery or exploration. Meet the rival's expedition
   in its province to intercept it, or stand in its announced target to
   defend. Invest your rewards in recovery and reinforcements; each
   conquered province also adds income.
7. Before attacking Duskspire, restore every unit to within about 6 health
   of its maximum. Its five Dread Guards and two Archers demand a prepared
   army. A direct rush with the starting troops is unlikely to succeed.
8. The rival's numbered diamond marks its moving army. **V** reveals its
   troops, wounds, gold, next target and countdown. It loses actual troops
   in battles and pays to heal/recruit at Duskspire. Breaking its expedition
   gives you a counterattack window while it rebuilds; Duskspire's garrison
   remains a separate force. Save with **F5** before a difficult expedition.

The starting army is usable immediately; Barracks is one possible opening,
not a required build. Marketplace provides income instead, while Wizard
starts with both spells and can invest elsewhere.
Investment, exploration and responding to the announced expedition win the
seed-7 Commander campaign in the integration journey using automatic
battles; manual decisions and different seeds can change the outcome.
For Wizard, a Mage Tower before the Temple
adds mana to support the two spells already learned.

## Controls

| Screen | Input | Action |
|---|---|---|
| Title | Tab / click class | Choose hero class |
| Title | Left / Right / click world | Choose Frontier, Elderwild or Ruins |
| Title | Enter / Space | Start the selected shard |
| Title | N | Choose a new shard seed |
| Title / guide | O | Open sound and display settings |
| Settings | S / D | Select Sound / Display |
| Settings | Up / Down, Left / Right | Select a row, adjust its value |
| Settings | Enter / Esc | Apply preferences / cancel live preview |
| Shard | Click province | Select and inspect it |
| Shard | Tab | Cycle provinces adjacent to the hero |
| Shard | Home | Select the hero's current province |
| Shard | V | Inspect the rival's expedition and next order |
| Rival plan | L / Esc | Locate its province / close the report |
| Shard | Enter / Space | Travel to or invade the selected adjacent province |
| Shard | X | Explore the hero's current province; preview authored expeditions |
| Expedition briefing | Enter / Esc | Enter for one action / return without spending |
| Adventure briefing | 1 / 2 | Compare deployment, fee or reward choices |
| Shard | B / R | Open construction / recruitment |
| Shard / decision | H | Inspect skills and equip relics |
| Shard, battle, guide, hero or decision | C | Open the rules codex |
| Codex | 1–6 / Tab / Shift+Tab | Select / cycle categories |
| Codex | Arrows / Page Up / Page Down | Turn pages |
| Decision | 1 / 2 | Choose the corresponding skill or reward |
| Hero | 1–4 / U | Equip a visible relic / unequip |
| Hero | Left / Right | Previous / next inventory page |
| Catalogue | Number key / click | Buy the corresponding visible building or troop |
| Recruitment | Left / Right or Previous / Next | Change troop page |
| Shard | E | End campaign turn |
| Battle | Click friendly unit / Tab | Select unit / cycle units with an action or movement left |
| Battle | Click empty hex / enemy | Move / attack with selected unit |
| Battle | Arrows / Page Up / Page Down | Aim at neighboring hexes (Page keys provide the other two diagonals) |
| Battle | Enter / Space | Select, move, attack or cast at the aimed hex |
| Battle | F | Cycle enemies, or legal targets for the selected order |
| Battle | 1 / 2, then click target | Hero Bolt / Heal with the selected Acolyte, otherwise the hero |
| Battle | S, then F / click target / Enter | Exchange a Warden with an adjacent ally |
| Battle | Q, then F / click target / Enter | Rally an adjacent Pinned ally with Militia |
| Battle | D, then F / click hex / Enter | Place a Sapper's finite Smoke screen |
| Battle | R, then F / click target / Enter | Preview and Repulse an enemy with a Rune Adept |
| Objective battle | O | Aim at the seal or cycle exits |
| Extraction battle | V | Evacuate with an unspent hero on an uncontested exit |
| Battle | P, then F / click target / Enter | Aim Pin with an Archer or Storm Quiver hero |
| Battle | G / Guard or Brace button | Spend the selected unit's order on its defensive stance |
| Battle | E | End round, or accept a completed battle's result |
| Battle | A | Auto-play one round |
| Battle | T / Retreat button | Withdraw with surviving troops and a gold penalty |
| Shard, battle or decision | F5 / F9 | Quicksave / quickload Manual 1 |
| Title, shard, battle or decision | F6 | Open all saves |
| Saves | 1–6 / Shift + 1–6 | Load a slot / recover its previous version |
| Saves | Tab | Switch Save / Load; only manual slots can be overwritten |
| Shard or battle | F1 | Open guide, including Save & title |
| Guide | S | Choose a save slot before returning to the title |
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
lost. Ten recruitable roles have different orders and costs. Militia fill
cheap front-line slots; Swordsmen provide stronger melee attacks; Archers
offer ranged damage and Pin; Pikemen Brace against melee approaches.

Acolytes improve campaign recovery and can Heal a wounded ally within four
hexes. Select the Acolyte, press **2**, then **F** and **Enter** or click a
highlighted ally. The preview shows actual HP restored. Heal spends that
Acolyte's order and remaining movement, using the same finite mana as the
hero. The hero keeps its own order.

Rangers can shoot and then use their remaining movement. Moving before
shooting gives no second move, and Pin still slows the escape. After firing,
the status reads **Can move** and blue hexes show the available retreat.
Wardens use **S** to exchange places with an adjacent ally. Both units spend
their remaining movement; the Warden spends its action, while the ally keeps
any unspent action. Guard, Brace and Pin remain unchanged. Ranger and Warden are
on recruitment's second page; **Left/Right** or **Previous/Next** changes pages.

Militia can **Rally** with **Q**, clearing an adjacent ally's Pin. The green
forecast shows that ally's actual reachable hexes after Rally. The Militia
spends its own action and movement; the ally keeps its existing spent orders.
Sappers cost 60 gold and one crystal after Marketplace construction. **D**
places one Smoke screen per battle within three visible hexes. It blocks
both sides' ranged attacks, Pin and spells through that hex until the Sapper's
next turn. The cloud badge and **Smoke · 0** persist across loading.

Rune Adepts cost 65 gold and two crystals after Mage Tower construction.
**R** uses one Repulse per battle to push an adjacent enemy one hex away,
without damage or changing its spent orders. The landing is previewed and
must be empty; Guard and Brace anchor enemies against displacement.
Skyriders cost 85 gold and three crystals after Temple construction. Their
four-hex flight crosses occupied or rough ground, with an empty landing.
Pin still slows them and melee attacks still face Brace.

Each level offers two class disciplines. Choose a new discipline or deepen
one already learned, up to rank three. Commander balances recruitment and
recovery against retaliation-free troop attacks; Warrior chooses safe,
stronger strikes or healing; Scout chooses terrain traversal or attacking
before moving away; Wizard specializes in cheaper Bolt or stronger,
cheaper Heal. **H** shows learned effects.

Twelve sites have different defending parties and gold/crystal rewards:
Buried Shrine, Forgotten Tower, Old Barrow, Wolf Den, Lost Caravan and Elder
Grove, Border Watch, Explorer's Camp, Courier's Crossing, Supply Cache,
Sealed Vault and Pack Hunt.
The Watch shows its layout and rewards before you commit
an action. Hold its seal for two uncontested enemy turns by round eight, or
defeat every defender. **O** locates the seal during its battle. Winning offers a relic or its gold value. Keep and equip one of eight
relics to gain healing or damage spells, avoid retaliation, cross difficult
terrain, improve army recovery or reduce recruitment costs. Duplicate
relics can instead be distilled into four crystals. These choices belong
to this adaptation; they do not reproduce the commercial game's catalogue.

Courier's Crossing, Supply Cache and Sealed Vault ask you to carry cargo out of a defended
battlefield. Their briefing compares two approaches with **1/2** and shows
the actual deployment, exits, defenders and reward before **Enter** commits
an action. **Esc** returns for free. At the Crossing, a guide costs 20 gold
and changes your deployment; at the Cache, a larger reward slows your hero.
The Ruins Vault offers a second escape door for two crystals.
During battle, **O** cycles marked exits. Reach one with an unspent hero action
and no adjacent enemy, then use **V** to Evacuate with all surviving troops.
Moving or being delivered by a Warden keeps the hero's action; attacking,
casting or Guarding spends it. Rout also wins. Escape before the eighth enemy
phase ends; failed attempts retain wounded defenders and spent fees, while
success pays the chosen reward once. The Codex shows saved approach details.

Elderwild's Pack Hunt puts six wolves on both sides of a forest divide.
Stand together for free or pay 20 gold to deploy north of the forest.
The same finite pack and reward remain. Defeat every defender while keeping
your hero alive; there is no seal or exit objective. Ordinary rout battles
force a retreat through exhaustion after 80 rounds.

| Building | Cost | Benefit |
|---|---|---|
| Barracks | 45 gold | Recruit Swordsmen, Pikemen and Wardens |
| Archery Range | 55 gold | Recruit Archers and Rangers |
| Temple | 65 gold | Recruit Acolytes and Skyriders, learn Heal, improve recovery |
| Mage Tower | 75 gold + 2 crystals | Recruit Rune Adepts, learn Arcane Bolt and gain 4 maximum mana |
| Marketplace | 60 gold | Recruit Sappers and add 8 gold income each turn |

Owned provinces provide gold and hills provide crystals; army upkeep is
deducted each campaign turn. If every province neighboring Westwatch is
rival-owned, the capital is encircled: its gold, crystals, Marketplace and
local recovery stop. Reclaim any neighboring province to reopen supply.
The shard warns before End Turn if gold plus income cannot cover upkeep.
Unpaid troops leave, preserving higher levels and experience first; among
equal veterans, more expensive/newer recruits leave first. Outlying owned
provinces still produce income.

Ending the turn restores health on friendly land and 4 mana, unless the
hero is inside encircled Westwatch. Before skill and relic modifiers,
Arcane Bolt deals 14 damage; Heal restores up to 16 health
to a living ally. Both cost 4 mana, have a range of four hexes and use the
hero's action. A move can precede an attack or spell; attacking or casting
ends that unit's movement unless the Scout's Skirmisher discipline allows
an attack followed by movement. Surviving adjacent targets can retaliate once
per full round. Forest and marsh cost extra movement; forest and hills
provide cover. Intervening forest blocks ranged attacks, Pin and spells;
forest at a shooter or target provides cover without itself blocking the shot.
Smoke also blocks shots into or out of its hex, while self-healing still works.
Older saved active battles retain their original sight and capabilities.

**G** spends a unit's remaining movement and action on **Guard**, adding two
defense until its next turn. A Pikeman uses **Brace** instead: the first
adjacent melee attacker takes a spear hit before attacking. A lethal spear
hit prevents the attack entirely. Brace replaces ordinary retaliation and
strikes even through retaliation protection. Ranged fire, including adjacent
ranged attacks, avoids Brace. Stance badges, effective defense and the
attack preview show the current rules; saves retain stances exactly.

Capture Duskspire to win; taking every province is unnecessary. If the
rival reaches a province containing your hero, you fight a defensive
battle. Other guarded provinces fight its expedition using the same
tactical rules, with lasting losses on both sides. Losing
Westwatch ends the campaign. Retreating or losing an ordinary battle keeps
survivors' wounds and costs up to 20 gold; defending territory is lost on
retreat. New shard becomes available after victory or defeat.

This slice has no astral metacampaign, diplomatic simulation, karma,
rebellions, multiclassing, multiplayer, fog of war or
the original games' large content catalogue. The rival has a finite
expedition and treasury, with a fixed recruitment plan. Tactical morale,
stamina and spell preparation are simplified
away. Hero mana replaces Eador's prepared spells and gem costs; crystals
fund construction, specialist recruits and some expedition approaches.

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

Archers and heroes carrying Storm Quiver can **Pin**: a ranged shot within
three hexes for half normal damage, slowing a surviving target by two
movement (minimum one) during its next turn. The target can still attack or
Guard. Pin does not stack, and the shooter must skip Pin on its following
turn. The targeting forecast shows both sides' actual HP loss; a **P** badge
marks the slowed unit. **Esc** cancels targeting without spending an order.
Watch Bell grants the hero Brace through **G**, even for a ranged hero.
New worlds place Storm Quiver in Wolf Den, Watch Bell at Border Watch, and
Wayfarer Boots at Explorer's Camp. Older saves retain their recorded rewards
and active battles.
