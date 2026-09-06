# Broken Observatory: a contested hill and two firing lanes

This bounded work adds one Ruins adventure at `(-1, 0)`, using the
existing hold objective and approach/save fields. The central hill seal is
`(0, 0)`: control it through two consecutive uncontested enemy phases by round
8, or rout the defenders. A Dread Guard and three separated Archers remain the
same finite roster for both approaches. Clearing forest `(-1, 0)` costs two
crystals and opens movement and sight for both armies. The free approach keeps
that forest. The reward is 55 gold, three crystals and Ember Lens.

The executable manual plans in `tools/eador_observatory_campaign.py` prepare
ordinary purchased armies through home and western conquests. They accept the
same State-like input adapter as the native adventure verifiers. No resources,
levels, positions or battle statistics are injected. Seed seven produces:

| Commander plan | Campaign arrival / hero level | Building / recruitment gold spent | Entry crystals | Battle rounds | Mana spent | Missing player HP | Orders |
|---|---|---|---|---|---|---|---|
| Warden, Sapper, Acolyte; cleared lane | 5 / 2 | 170 / 145 | 2 | 4 | 12 | 22 | 46 |
| Warden, Rune Adept, Acolyte; forest retained | 8 / 3 | 185 / 143 | 0 | 5 | 12 | 8 | 62 |
| Same Rune army and orders; cleared lane | 8 / 3 | 185 / 143 | 2 | 5 | 12 | 2 | 62 |

All three hold with all seven player units and one enemy Archer alive. The
Sapper army arrives with 15 crystals and 12 mana; the Rune army arrives with
21 crystals and 14 of its 18 mana. The latter's slower funding route includes
an earned rival interception and higher hero/support levels. Comparing their
four- and five-round victories does not isolate the effect of the entry fee.
The paired Rune run does: two crystals save six wounds without saving a phase.
This is evidence for those specific orders, not a universal or optimal trade.

The open lane lets the hero reach the hill in the first phase. Smoke protects
an exposed Militia; healing sustains the holder while melee and ranged attacks
remove successive contesters. Pin holds the northern bowman away for the first
successful phase; a body closes its longer route before Pin expires. This is
a manual plan, not an optimality or campaign-balance claim. The Rune plan first
clears the occupied hill and northern firing position, then uses Repulse to
push the southern contester out of seal adjacency. Moving the Warden and
Acolyte clears both the push destination and the Adept's approach; the two
Militia then block the bowman's return. Healing sustains that final hold.

The same guard identities, reward and objective are used for both approaches.
Only forest `(-1, 0)` changes to plains: the hero can reach the hill in the
first phase, and sight opens in both directions across that lane. This is a
visible terrain choice rather than a hidden combat-stat adjustment.

The first western-seal experiment was rejected because a full army could
form a ring and win without engaging the defended problem. The central hill
requires crossing the approach and clearing its anchor. No Saga2D changes,
new tactical commands, scenario DSL or save schema are needed.

The retained old Barrow fixture was generated and continued with actual prior
source `f9b3a70`, before adding this site. It reloads with the original Barrow
at `(-1, 0)` and reaches the identical complete campaign result. Saved world
arrays are never regenerated.

Six public integration tests cover all three plans with an exact reload after
each order and attack, Pin and Heal forecasts checked against their immediate
results. They also cover once-only rewards while enemies remain alive, a saved
paid retreat with one killed and one wounded defender followed by a free retry,
and 100 Ruins seeds. Those seeds keep the home Shrine, Wolf Den, Explorer's Camp,
Border Watch and Sealed Vault/Mirror Badge; both central Old Barrows still
provide Iron Crown. Frontier and Elderwild do not acquire this site.

Source checkpoint `3579eeb` passes 908 tests, including all eight earned active
relic tests. The new western adventure does not require changing their campaign
preparation. Source-hashed manual evidence is retained in
`docs/evidence/shardbound-observatory-2026-09-06/manual-routes.json`.

To replay a plan, call `prepare_observatory()` followed by
`observatory_route(state, 'clear')`, or prepare with `support='adept'` and use
`observatory_rune_route(state, 'covered')`. Both route helpers accept
`orders_type` for native input or saved-command verification. The latter also
accepts `'clear'` for the paired comparison.

The same checkpoint passes 300 randomized campaigns and 20 mock scene runs
with 10,003 random inputs; both approaches were reached and source hashes
remained unchanged. This is reliability evidence, not a campaign win-rate
benchmark. The [native journeys](evidence/shardbound-observatory-2026-09-06/native/README.md)
at integrated source `46a5aa8` replay all three purchased armies and approaches
through 610 inputs and 26 exact reloads. Briefing, Smoke/Repulse forecasts and
all three results were visually inspected. This content increment does not complete G05: it is one
battlefield family, and its two approaches are not two authored patterns.
