# Broken Observatory: first paid hold tracer

This bounded work adds one proposed Ruins adventure at `(-1, 0)`, using the
existing hold objective and approach/save fields. The central hill seal is
`(0, 0)`: control it through two consecutive uncontested enemy phases by round
8, or rout the defenders. A Dread Guard and three separated Archers remain the
same finite roster for both approaches. Clearing forest `(-1, 0)` costs two
crystals and opens movement and sight for both armies. The free approach keeps
that forest. The reward is 55 gold, three crystals and Ember Lens.

The first manual Commander plan is executable in
`tools/eador_observatory_campaign.py`. It buys a Warden, Sapper and Acolyte,
using 170 gold on buildings and 145 on recruitment through home and western
conquests. On seed seven it arrives on campaign turn five with 15 crystals,
pays two, and wins by hold on battle round four. All seven player units survive;
one northern Archer remains alive. The plan spends 12 mana, ending with 22
missing player HP. Every immediate forecast and each of its 46 orders is
checked through exact campaign reloads.

The open lane lets the hero reach the hill in the first phase. Smoke protects
an exposed Militia; healing sustains the holder while melee and ranged attacks
remove successive contesters. Pin holds the northern bowman away for the first
successful phase; a body closes its longer route before Pin expires. This is
a manual plan, not an optimality or campaign-balance claim.

The first western-seal experiment was rejected because a full army could
form a ring and win without engaging the defended problem. The central hill
requires crossing the approach and clearing its anchor. No Saga2D changes,
new tactical commands, scenario DSL or save schema are needed.

The retained old Barrow fixture was generated and continued with actual prior
source `f9b3a70`, before adding this site. It reloads with the original Barrow
at `(-1, 0)` and reaches the identical complete campaign result. Saved world
arrays are never regenerated.

The free manual approach, alternate purchased army, finite failed retry,
100-seed source audit, native journey and broader evidence are still pending.
This checkpoint does not complete G05 or a seven-pattern acceptance claim.
