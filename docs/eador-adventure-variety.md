# Adventure locations and route decisions

The twelve authored adventure families already met the content-count floor.
Most nevertheless occupied fixed provinces on every seed. Terrain and income
changed, but knowing the reward itinerary often removed the need to investigate
another route. This increment varies the locations of existing complete sites,
and exposes their saved locations before the player pays for a conquest.

## Generation and ownership

Shardbound permutes complete site packages within the western and central
progression bands. A package carries its name, content ID, finite guard roster,
gold, crystals and relic. Guard health is initialized from that roster. Home,
the Watch, eastern sites and the economic roads' Caravan/Tower sources retain
their locations. At least two home-adjacent provinces retain ordinary, untimed
adventures. A separate seeded random stream leaves province terrain, income,
conquest defenders, capitals and rival planning unchanged.

The possible placements are finite combinations of eligible provinces. There is
no retry-until-lucky generator, special successful seed, or new framework API.
This remains game content and generation. Saga2D's existing grid, UI and save
mechanics suffice. Loading uses the complete recorded province array; it never
rerolls a saved map. Newly created worlds, including later campaign shards,
use the new placement rule.

Preserving packages does not imply equal access costs or equal difficulty.
Different travel, conquests, recovery and rival responses can change an army's
experience, wounds and available resources before the same tactical problem.
That consequence needs actual played-route evidence, separately from structural
generation checks.

## Information for players

Selecting a province shows its saved site even before conquest. Sites and
Relics in the Codex name the provinces containing their current sources;
cleared sources are marked so they do not promise a second reward. Browsing
does not spend a turn or change the saved game. Historical worlds use their
recorded locations and rewards, even when current generation would differ.

## Declared route comparison

The [two declared Frontier plans](evidence/adventure-variety/route-declarations.md)
were selected from map inspection before battles. Their generator SHA-256 is
unchanged in this implementation, built on `a7a6c50`. Each begins a fresh
Commander/Standard linked campaign; neither starts from a prepared army.

Seed 5 prioritizes the nearby Caravan's Merchant Seal, buys its planned troops
at the actual discount, and pays for the guided Courier approach. Seed 12
prioritizes nearby Boots, gives up the Tower alternative and its spell/reward,
then equips mobility instead of Moonstone healing for Stranded Explorer. The
declared stops, recovery allowance, failure handling and nominal forecasts were
retained before play. Both routes reached their declared reward endpoint.

| Actual route | Investment and equipment | Endpoint |
| --- | --- | --- |
| [Seed 5: Caravan → Courier](evidence/adventure-variety/route-seed5-outcome.md) | Seal saves 19 gold on recruits; guided entry costs 20. Moonstone supplies Heal. | Five battles; T3 with one action, 112 gold/10 crystals, six troops alive and 11 wounds. |
| [Seed 12: Camp → Explorer](evidence/adventure-variety/seed12-outcome.md) | Full-price recruits; Archer waits for Silverford's reward. Boots replace Heal for the free northern rescue. | Six battles; T3 with no actions, 121 gold/14 crystals, six troops alive and 15 wounds. |

Both evacuations used Warden Swap and finished in round 2 with defenders still
alive. Each route used two mandatory end-turns and no elective recovery,
retreat, defeat, autoplay or rewind. One rejected move per route is retained
with exact state unchanged. The 107/112 accepted commands preserve every paid
step and saved continuation. Different seed economics, conquest XP and rewards
also affect the comparison; it does not isolate a single equipment effect.

These local adventure routes cannot establish three successful whole-campaign
strategies, optimal play, general economic balance or an Early Access gate.
The structural audit separately compares 100 worlds per theme with the exact
retained pre-change worlds; geometric placement orders are never counted as
played itineraries. Verification is tracked in
[the evidence folder](evidence/adventure-variety/).
