# Independent visual review — 8 September 2026

Reviewed all 19 source native pyglet captures at a 1280 × 800 logical canvas:
ten map views and nine Settlement UI views, after inspecting earlier captures
and reporting defects. The final files in `native/` and `settlement/` replace
those earlier captures. Survey views deliberately reveal fog and freeze the
simulation; they are inspection views. The Settlement overlays were rechecked
after the final camera fix at `85becd0fda8493fffc14ad33baee32f4fccdee64`.

Also inspected all nine final Mac portable frames and all nine installed-app
frames from that same source and version `0.1.0-preview.3`. The installed
[receipt and image list](mac-package/installed-native.json) identify the actual
`/Applications/Warband.app` executable and Apple M4 renderer.

## Confirmed findings and fixes

- **Ground seams resolved in the refreshed surveys.** The initial captures
  had faint straight lines crossing grass and water at chunk boundaries in
  every theme. The refreshed [summer](native/summer-regions.png),
  [winter](native/winter-regions.png) and
  [wasteland](native/wasteland-regions.png) views no longer show that grid.
  The fix extrudes image-edge colours into atlas padding and paints additional
  neighbouring terrain before cropping each overlapping ground chunk.
- **Map containment looks correct.** In the six final fogged northwest and
  southeast views, the stone rim gives the board an intentional boundary and
  no bright ground or trees spill beyond the fog/rim. The rim remains intact
  in the refreshed full-map surveys across all three themes.
- **Tutorial/Menu collision and empty command-card stub resolved.** The
  initial gameplay frames showed the tutorial covering Menu/F10 and an empty
  command-card outline at the lower-right with nothing selected. The
  [final Settlement capture](settlement/01-settlement-unselected.png) shows the
  tutorial below the top controls and the empty outline removed.
- **Plans and map markers are readable.** All nine final Settlement captures
  were inspected. The [waiting list](settlement/05-waiting-plans.png),
  [cancelled plan](settlement/06-plan-cancelled.png) and
  [active production](settlement/09-active-production.png) keep names,
  reasons, costs and cancellation buttons distinct. The
  [blueprint and assembly flag](settlement/07-blueprint-and-assembly.png)
  have different colours and clear labels.
- **Final spacing and production status confirmed.** The Settlement heading
  now has room before Build, and the [Build catalogue](settlement/02-build-catalogue-costs.png)
  keeps the full Workshop label without a cramped badge. The final sequence
  waits for the opening banner to finish and for the construction status to
  refresh. The active-production frame shows “Building 4% · Paid” for the Farm
  and “Training 8%” for the Town Hall's Peasant, matching the visible foundation
  and queued production.

- **Transparent overlays preserve the map camera.** A later packaged
  Crimson-seat capture exposed the underlying map jumping to the origin when
  Plans opened. This was less obvious in the earlier Azure-seat fixture. The
  shared renderer now retains the visible game scene's camera under a
  transparent menu. The final installed [Train catalogue](mac-package/installed-native-settlement-train.png),
  [Plans panel](mac-package/installed-native-settlement-plans.png) and
  [Match menu](mac-package/installed-native-match-menu.png) keep the Crimson
  base at the same screen position. The portable sequence and refreshed
  source Settlement overlays also show stable map placement.
- **Packaged menu flow remains readable.** Both final Mac sequences show the
  title, Multiplayer menu, copied room code, pasted code, joined match, Train,
  Plans, Match menu and a fresh offline match. Room controls, costs, waiting
  reason, cancellation and menu labels are legible. The horizontal blue rules
  in the first offline frame belong to the temporary opening banner; they
  are distinct from the resolved terrain seams.

## Optional art refinements

Winter's per-tile brightness changes still give clearings a subtle checkerboard
appearance. Crystal fields and sparse wasteland trees reveal their aligned
tile rows. Smoother ground tint and modest variation within each tile could
make those areas feel more natural; these are aesthetic observations,
separate from the resolved rendering seams.

The larger meadow, forest, pond and rocky regions are visually distinct.
Buildings, trees and resources remain legible in all three palettes. This
review establishes the appearance of the inspected source and Mac package
captures. The [runtime receipt](mac-package/mac-verification.json) separately
records successful native input and public-network checks; screenshots alone
do not establish animation/performance coverage, physical Windows GPU
compatibility or a complete match.
The Plans screenshots contain up to four entries; they do not establish
every pagination or long-message layout.
