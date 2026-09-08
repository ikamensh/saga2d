# Independent visual review — 8 September 2026

Reviewed the native pyglet captures at a 1280 × 800 logical canvas: ten
initial map/gameplay frames, followed by the refreshed summer, winter and
wasteland surveys after the ground and atlas fixes, then nine initial
Settlement UI captures. Survey views deliberately
reveal fog and freeze the simulation; they are inspection views.

## Confirmed findings and fixes

- **Ground seams resolved in the refreshed surveys.** The initial captures
  had faint straight lines crossing grass and water at chunk boundaries in
  every theme. The refreshed [summer](native/summer-regions.png),
  [winter](native/winter-regions.png) and
  [wasteland](native/wasteland-regions.png) views no longer show that grid.
  The fix extrudes image-edge colours into atlas padding and paints additional
  neighbouring terrain before cropping each overlapping ground chunk.
- **Map containment looks correct.** In the six initial fogged northwest and
  southeast views, the stone rim gives the board an intentional boundary and
  no bright ground or trees spill beyond the fog/rim. The rim remains intact
  in the refreshed full-map surveys across all three themes.
- **Tutorial/Menu collision and empty command-card stub resolved.** The
  initial gameplay frames showed the tutorial covering Menu/F10 and an empty
  command-card outline at the lower-right with nothing selected. The first
  [Settlement capture](settlement/01-settlement-unselected.png) shows the
  tutorial below the top controls and the empty outline removed.
- **Plans and map markers are readable.** All nine Settlement captures were
  inspected. The [waiting list](settlement/05-waiting-plans.png),
  [cancelled plan](settlement/06-plan-cancelled.png) and
  [active production](settlement/09-active-production.png) keep names,
  reasons, costs and cancellation buttons distinct. The
  [blueprint and assembly flag](settlement/07-blueprint-and-assembly.png)
  have different colours and clear labels.
- **Final gameplay recapture pending.** The initial Settlement heading
  touches the Build button, and Workshop's hotkey badge crowds its label.
  Both were reported and are being fixed. The active-production capture
  also catches the Farm's status before its next scheduler refresh: a paid
  foundation is already visible in the preceding frame, but the list still
  says “Builder en route” and “Cost”. The final sequence should allow the
  status to refresh and the opening banner to finish before capture.

## Optional art refinements

Winter's per-tile brightness changes still give clearings a subtle checkerboard
appearance. Crystal fields and sparse wasteland trees reveal their aligned
tile rows. Smoother ground tint and modest variation within each tile could
make those areas feel more natural; these are aesthetic observations,
separate from the resolved rendering seams.

The larger meadow, forest, pond and rocky regions are visually distinct.
Buildings, trees and resources remain legible in all three palettes. This
review establishes the appearance of the inspected captures, not packaged
release acceptance, animation/performance coverage or a complete match.
