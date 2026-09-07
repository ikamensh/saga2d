# Saved discovery reading

The same bounded journey passed through mock input and native pyglet input.
All eight native PNGs were inspected: selected site names, conquest defenders,
source locations, controls and army health remain readable at the captured
100%/125% sizes, with no blocking clipping or overlap. The Sites and Relics
pages agree with the selected saved province; the cleared Caravan remains
identified as cleared and its Merchant Seal as owned.

## Receipts

- `mock.log`: one shared integration regression passed in 1.79 seconds.
- `native.log`: native process exited 0 and `Game.close()` closed its window.
- `native/verification.json.gz`: lossless original receipt, with complete
  initial/final states, input events, read text, fixture provenance and SHA256
  hashes for the tested game/framework source and assets.
- Native: 5 worlds, 8 reading cases, 186 input activations, 186 state checks,
  5 exact F5/F9 save/load pairs and 8 PNGs. No preparation commands.
- Native timing: 30.02588216692675 seconds wall, 7.600303 seconds CPU;
  requested CPU allowance 25%, native input paced at 30 FPS.
- All captures use the 1280×800 logical/window size; native PNGs are
  2560×1600 framebuffer captures.

The run's base revision was `a7a6c5020232d539a7f4d616597942a47174b396`,
with the exact in-progress implementation identified by `dirty_at_start`
and `source_sha256` in the receipt. Its source/assets fingerprint was unchanged
from start to finish. The reader was subsequently committed as `6c2cf5b`
without changing its tested bytes. The uncompressed receipt SHA256 is
`fcc6f97f18b2642f47984b0a4ffda844bdd88688b43303d10a63bb34625d8928`.
`manifest.sha256` authenticates the retained files; PNGs and logs are exact copies.

## Inspected frames

| PNG | Observation |
| --- | --- |
| `frontier-5-selected-100.png` | Neutral Heartwood shows Stranded Explorer at `(0,0)`, moved from baseline `(0,-1)`. |
| `frontier-5-sites-125.png` | Explorer rules and `Recorded sources: Heartwood` fit the measured page. |
| `frontier-5-relics-125.png` | Wayfarer Boots lists both the Camp at Old Hollow and Explorer at Heartwood. |
| `frontier-12-selected-125.png` | Neutral Mossfell shows Muster Yard at `(-1,2)`, moved from baseline `(-1,1)`. |
| `ruins-7-selected-125.png` | Neutral Amber Fields shows Broken Observatory at `(-2,1)`, moved from baseline `(-1,0)`. |
| `historical-ruins-selected-125.png` | The historical Sealed Vault remains at Winding Vale `(-1,1)`. |
| `cleared-caravan-selected-125.png` | The earned Caravan result shows `Lost Caravan · cleared` at Greenwater. |
| `cleared-caravan-relics-125.png` | Merchant Seal is owned; its Greenwater source is marked `(cleared)`. |

## Scope and limits

Fresh Frontier seeds 5 and 12 and Ruins seed 7 start through Title/Enter as
Commander on Standard, and are read at both 100% and 125%. The old initial
Ruins world and earned Caravan result are fixed, hash-authenticated v12 saves,
read at 125%; their historical preparation is not executed. The Caravan's
historical preparation included autoplay. No battles, purchases, conquest,
army preparation or model edits occur in this reader.

Opening Codex and changing text size preserve the selected province and exact
model. F5/F9 preserves the complete saved model. Selection is UI state, so its
actual post-load value is recorded, then the source is selected again through
an ordinary map click. Historical source files remain unchanged.

Baseline coordinates are comparison evidence only; current destinations come
from the world's stored provinces. These few reading cases establish readable
locations and save preservation, not world-distribution coverage, adventure
completion, strategic balance, independent human discovery or release acceptance.
Audio is silent; no audible sound judgment is claimed.
