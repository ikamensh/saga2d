# Shardbound relic presentation

`eador.art.relic(scene, x, y, kind, scale=1)` draws the twelve original relic
medallions with ordinary Saga2D vector calls. Shapes, silhouettes and palette
choices were authored for Shardbound; no Eador images or other borrowed artwork
are included. A common rim holds distinct objects: boots, a leaf standard, lens,
moonstone, crown, charter seal, bell, quiver, censer, carved doorway rune, mirror
badge and drum. Their silhouettes also distinguish them without accent color.

Reward headings and equipment rows use the same family. Equipment retains four
items per page and the existing number keys. The longer Censer/Porter/Mirror copy
needed taller rows, and reward cards needed more space above their buttons. These
are fixed layouts for the 1280×800 logical canvas, not a text-scaling facility.
`draw_paragraph` measures and wraps text, but the manually placed controls still
need space reserved for it; a future multiline layout component could remove that
specific manual coordination if font scaling is introduced.

Run `python tools/verify_eador_relic_art.py` for native screenshots and real input.
It checks an old saved eight-relic collection, records actual choices along paid
public campaign routes for all three themes, reloads each new reward, and equips
it through visible controls. It also captures every icon at equipment/detail
sizes and a real skill choice. The same journey runs with the mock backend in
`tests/eador/test_relic_art.py`. Native captures were inspected for full reward
copy, all four new equipped relics, old/current paging and the skill screen.
The general development campaign policy is only a way to earn presentation
fixtures here; this verification makes no difficulty or route-quality claim.

`tests/eador/fixtures/v11_relic_collection.json` was earned before source changes
at commit 99b56c5: `State.new_campaign(0)` followed by `play_campaign` with home,
every sorted non-capital province, then Duskspire. It preserves the earlier eight
relics and their recorded sources; no inventory or reward was injected.

The Abilities reference names the four relic alternatives beside their troop
sources: Censer/Smoke, Rune/Repulse, Badge/Swap and Drum/Rally. It counts the living
hero only when the active battle actually contains that capability, and keeps
used charges separate from unspent orders. The Relics reference identifies the
equipped hero's recorded battle capability and keeps source names from the saved
shard. Replacing a spell-granting relic and spending the hero's own active order
before Evacuate are explicit tradeoffs.

`python tools/verify_eador_relic_codex.py` earns the Censer, enters Watch, spends
hero Smoke through the visible button/hex controls, saves/reloads, and browses
all Abilities/Relics pages. The same pages are checked against an older active
v10 save. Opening, paging and closing the Codex change neither state nor save
files. Native screenshots for the long descriptions, saved charge count and
old capability counts were inspected; the fixed three-entry layout required
concise Swap, Smoke and Evacuate wording.
