# Saved worlds and future content

A campaign save records its current province array, battle and rules profile.
Loading that save uses those recorded values. It must not regenerate the world
because a new authored site or reward has been added to the catalogue. Recovery
also restores the recorded campaign entry world, including its original site
identities and rewards. Resting and continuing an active battle preserve those
same arrays and all ordinary state changes exactly.

Advancing to an **unentered future shard** is different: that shard has no saved
province array yet. Its recorded seed and selected theme generate a new world
using current content. Adding a site can therefore change that newly entered
world, while treasury, retinue, mana, difficulty rules, rival parameters, order
history and all other transition behavior continue under their recorded rules.
The new arrival's entry checkpoint records the world that was actually created,
so later recovery preserves it exactly.

This is the existing `campaign.advance` / `campaign.recover` boundary; no content
version or save schema was added for Smuggler Screen. It does not promise that a
future, ungenerated shard will reproduce every site from an older release.

The historical difficulty fixtures remain byte-for-byte original. Only their
Rootward **advance outputs** use `tools/eador_save_expectations.py` to construct
the expected fresh province arrays from public `worldgen.generate(seed, theme)`.
The helper verifies Rootward/stage two/Elderwild, substitutes the complete live
and newly recorded entry arrays, and retains every other recorded key. Tests
then compare the complete snapshot. Loaded inputs, rest, active battles,
recovery and replay of recorded entry worlds retain their original expectations.
No province arrays or other fields are discarded to make a comparison pass.

Independent content checks retain real pre-Screen Grove and Caravan battle
fixtures and their exact completed outputs, and audit the new source and all
required relic sources across 100 seeds. Thus the fresh-generation comparison
cannot stand in for testing either content correctness or old-world preservation.
