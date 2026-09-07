# Declared Frontier route candidates — before battles

Read-only generation review found no concrete placement bug. The source under
review is `/tmp/saga2d-adventure-routes-1524c48`, HEAD
`1524c48a3fff7fa4694df42f04c3f090e5cd4599`, with uncommitted `eador/worldgen.py`
SHA256 `07042bd83c96edfcbbd5dfd2941dcc332932b4bc47f942112af510b57cdf5690`.
The complete fresh Commander openings for Frontier seeds 0–23 are retained in
`/tmp/shardbound-adventure-route-candidates-1524c48.json.gz`. Generation used
`CpuBudget(25)` with a checkpoint after each save. No battle, campaign command,
test, native window, alternative tactical simulation or state edit was executed.

These are declared candidates for root to freeze before play, not completed
journeys. All money/action forecasts below assume the preceding victories and
no casualties, elective recovery or replacement spending. Actual results must
replace forecasts in the eventual evidence.

Both start Commander, Standard Frontier, T1, 100g/4c, two actions, hero36HP/10mana,
two Militia and one Archer. Rival: six full troops at Blackfen(2,-1),60g,
attacking Frostmere(1,-1) in three end-turns. Choose Tactician whenever a skill
choice is earned, so Quartermaster does not obscure recruitment costs.

Common first purchase: Barracks45g and Warden55g, exhausting the initial100g.
Complete home Shrine, keep/equip Moonstone, then the branch's adjacent conquest.
Take the mandatory end-turn after spending both T1 actions. After the nearby
relic, buy Swordsman, Archery Range and a second Archer in that order as soon as
each is affordable. Buildings and ordinary recruits consume no campaign action.
This gives six troops including the paid Warden; no veteran is retired.

## Seed5 — discount funds the short northern expedition

Candidate `State.new` inspection save SHA256 (the fresh linked campaign adds its
campaign object and records its own canonical initial hash in the journey):
`44d2377ea9155271d9444d93ba74d411e041ee4a54b7cc3675d06de0994c65e6`.

Route: Westwatch Shrine → Briarwood(-1,-1) conquest → its Caravan →
Greenwater(0,-1) conquest → its Courier’s Crossing.

Briarwood is marsh, one Brigand,8g income. Caravan faces three Brigands and
pays65g/0c plus Merchant Seal. Keep and equip the Seal for the planned purchases:
Swordsman34g, Archery55g and Archer27g. Then equip Moonstone for combat.
After the home/Briarwood victories and first mandatory rest, the projected
Caravan reward leaves153g; all three purchases fit before Greenwater, leaving37g.

Greenwater is forest, three conquest guards,6g income. The Courier is the next
adjacent authored objective. Declare the guided approach for20g: covered southern
deployment supports the slow Commander and preserves Moonstone's Heal. Complete
its actual extraction or rout, retain Veil Censer unequipped, and stop.

The alternative Boots source is Old Hollow(-2,2), requiring two conquests from
home and two more travel steps to the nearest authored adventure at Heartwood.
The nearby Caravan therefore offers a concrete shorter route plus cheaper troops.

Nominal schedule: two battlesT1, Caravan/GreenwaterT2, CourierT3; five attempts,
two mandatory end-turns, one campaign action remaining at the endpoint.

## Seed12 — mobility relic chooses the western approach

Candidate `State.new` inspection save SHA256 (the fresh linked campaign adds its
campaign object and records its own canonical initial hash in the journey):
`108a8e6c0a47eb934fa6c7f05965a99a26f54d4b08a238be13f025af7348b9da`.

Route: Westwatch Shrine → Amber Fields(-2,1) conquest → its Explorer’s Camp →
Silverford(-1,0) conquest → Greenwater(0,-1) conquest → its Stranded Explorer.

Amber Fields is hills, one Brigand,8g/1c income. Camp faces Goblin/Wolf and pays
40g/1c plus Boots. Keep the Boots. The nearby alternative is Briarwood(-1,-1):
one Wolf followed by a two-Goblin Tower,40g/3c plus Ember Lens. The declared
choice gives up Bolt and two site crystals, and adds one conquest/travel action,
to bring terrain-free hero movement to the announced marsh rescue.

Buy the same support roster at full prices: Swordsman45g, Archery55g, Archer35g.
The projected Camp reward leaves128g. Swordsman/Archery leave28g, so the Archer
waits until the25g Silverford conquest reward. Silverford is plains, one Wolf,
9g income; it is the direct bridge from the Camp toward Greenwater.

Take the mandatory end-turn after Camp/Silverford. Greenwater is marsh with
three conquest guards and5g income. Equip Boots for Explorer north, explicitly
giving up Moonstone's Heal in that battle. Use the paid Warden's Swap and actual
ranged cover to assist the carrier; previews and reachable cells must determine
orders. Keep the duplicate Boots by distilling if offered, then stop.

Nominal schedule: two battlesT1, Camp/SilverfordT2, Greenwater/ExplorerT3;
six attempts, two mandatory end-turns, no action remaining at the endpoint.
Greenwater is captured one turn later than seed5, with the real income and rival
timing consequences retained.

## Bound and interpretation

No retries, rewinds, autoplay or hidden state changes. Stop on an actual retreat
or defeat, after the declared reward resolution, or at T5. At most one elective
recovery end-turn is allowed when the hero or Warden is below half maximum HP;
record the trigger and real income/rival response. Any unexpected interception
is retained and counts toward the bound rather than silently rerouting history.
Root should freeze the implementation and confirm the retained fresh origin
before entering a battle; current source is uncommitted.

These examples can demonstrate that generated discoveries prompt different paid
routes and equipment decisions. They cannot isolate the placement change from
all other seed variation, prove either policy optimal, establish a full campaign
result, or close G02/G05 from two branches alone.
