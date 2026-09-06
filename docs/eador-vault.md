# Sealed Vault: a crystal-funded escape route

The third extraction adventure is an authored Ruins battlefield at `(-1, 1)`
on new shards. It adds content to the existing game-owned extraction contract;
there are no framework changes, new tactical commands or new save fields.
Its two approaches count as one pattern. G05 and the wider release criteria
remain incomplete.

## The choice and its tactical consequence

Face the crossfire for free through the eastern exit, or spend **two crystals**
before entry to open a second exit to the south. Both approaches have identical
deployment, terrain and four finite defenders: a Warden, two Archers and a
Dread Guard. Marsh slows the southern crossing; separated Archers cover both
flanks, while the eastern Warden can rescue its wounded Guard. Ordinary
extraction rules apply: an unspent hero order, no adjacent living enemy, and
explicit Evacuate by round eight. Rout remains an alternative.

Current new worlds offer 60 gold, one crystal and **Mirror Badge** by default.
The original checkpoint measured below offered Iron Crown; its retained reports
and older saved rewards remain historical. The paid route spends its two crystals
regardless of the outcome; retreat retains surviving
defender kinds and wounds. Choosing the free approach on a later attempt
neither restores its fallen Archer nor refunds the earlier fee. Victory pays
once and closes the site even when enemy survivors remain.

Home Shrine, Border Watch, Wolf Den and Explorer's Camp remain available.
New placement does not change saved province arrays. A real active v10 Ruins
fixture retains its recorded Tower at this location and reaches exactly its
old post-battle campaign result after migration, apart from the schema tag.
The Vault also passes with the merged v11 sight/capability rules; this layout
uses hills and marsh rather than forest sight blockers.

## A measured pair of ordinary purchased armies

`tools/eador_vault_campaign.py` exposes `prepare_vault(state=None)` and
`vault_route(state, approach, orders_type=AdventureOrders)` so model tests and
real controls execute the same public preparation and orders. The paired
seed-seven Commander arrives on turn five, having spent 100 gold on buildings
and 98 on recruits. Its two veteran Militia and Archer are joined by a paid
Warden and Ranger; no units or resources are injected into this journey.

| Same starting army | Free crossfire | Unseal for two crystals |
|---|---:|---:|
| Escape round | 4 | 2 |
| Healing mana spent | 4 | 0 |
| Missing player HP at escape | 58 | 13 |
| Player units lost | 0 | 0 |
| Enemies left alive | 1 | 3 |
| Manual battle orders | 41 | 17 |

The free route suppresses the rear Archer, engages the eastern Warden, and
breaks a real enemy Swap rescue. The hero spends an earlier turn healing and
the army clears the exit before allied Warden delivery. The paid route uses
Ranger fire followed by movement, eliminates the rear Archer, and Pins the
eastern one. Its genuinely Pinned hero walks one hex before the Warden swaps
it onto the southern exit. The delivery preserves the hero's action, allowing
explicit evacuation that turn. The second door saves tactical rounds and wounds
in this pair; the free door keeps two crystals. This tactical comparison alone
does not establish that the fee prevents another desired purchase. It is a
reproducible plan comparison, not an optimal-play or universal safety claim.

The [later campaign continuation](eador-vault-continuation.md) starts both routes
with the same earned 131 gold and 17 crystals. Paid captures a production province
two turns earlier and preserves a veteran in the ensuing interception; the
report separates those consequences from recovery waits and earned progression.

The same paid manual route also succeeds with Warrior, Scout and Wizard on
seed seven. Their army composition matches, but their preparation costs,
skills and arrival times differ; they are not substituted into the paired
Commander comparison. Tests roundtrip the complete campaign after each order,
check actual attack/Pin/Heal forecasts, and resolve the reward only once.

## Native controls and retained evidence

`tools/verify_eador_vault.py` is a thin verifier using the existing
`PlayerInput` and `PlayerOrders` adapters. It buys and prepares the army through
controls, selects and cancels each approach before entry, compares exact fees,
cycles the actual exits, checks disabled evacuation and target forecasts,
reloads saved battle/result states, then resolves exactly one reward.

Both hidden Pyglet runs completed at the default 1280×800 logical resolution
on macOS 26.6.2 arm64 with Python 3.13.2, source `eb39e79`:
free used 158 input activations and six exact reloads; paid used 105 and four.
The briefings, starting board, Heal/Swap forecasts, ready Pinned carrier and
result were rendered and inspected. No Vault-specific UI change was needed.
These are scripted real-input journeys, not first-time human playtests.

Retained [free](evidence/shardbound-vault-2026-09-06/crossfire/journey.json) and
[paid](evidence/shardbound-vault-2026-09-06/unseal/journey.json) reports record
the clean, unchanged source revision. Their adjacent PNGs retain both
briefings, ready carriers and results. The [300-campaign robustness report](evidence/shardbound-vault-2026-09-06/campaigns.json)
exercises 100 seeds per theme, including 16 free and 13 paid Vault entries,
47,858 state checks and 12,816 rejected commands that leave state unchanged.
Six victories and 294 defeats describe this random policy, not a balance claim.
The same checkpoint passed **831 full tests**; three subsequent focused
regressions retain the other heroes' paid manual routes. These counts describe
that historical checkpoint, rather than the current game and reward catalogue.

Run from a checkout with its Python dependencies installed:

```sh
python -m pytest tests/eador/test_vault.py tests/eador/test_vault_scene.py -q
python tools/verify_eador_vault.py --approach crossfire --output /tmp/vault-free
python tools/verify_eador_vault.py --approach unseal --output /tmp/vault-paid
```

The verifier writes `journey.json` with each input/order, resource amounts,
surviving HP, source hashes, Git revision, Python/platform, backend and elapsed
time. It rejects a source change during the run. Prior soak and package
reports do not establish this newer candidate's readiness. The
[next-encounter roadmap](eador-encounter-roadmap.md) proposes the remaining
path toward twelve meaningful authored patterns without implementing them
or treating the content count as a release-quality verdict.
