# Complete battle HUD and history

Accepted source **ef9a67f**. Original report HEADs and dirty states are preserved;
all recorded Python fingerprints match the accepted commit (`provenance.json`).
These are development checks on macOS, not packaged or human playtests.

- `hud-verification.json`: **222 unit views**, all ten recruitable roles plus
  heroes, three windows × 100/125; **1,065 native inputs and 37 exact reloads**.
  Paid preparations and untouched v8/v10 active saves supply the bodies.
  Actual Move → Guard matches a separate public-model copy and preserves every
  board center. History/settings preserve aim and isolate underlying orders.
- A real **2,878-character** autosave failure after End round remains complete
  across three pages; queued Return/order keys cannot repeat the round. Existing
  autosaves remain intact and manual save/reload preserves the applied state.
- `forecast-verification.json` and route reports: **126 layouts, 970 native
  inputs, 21 exact reloads**, including Smoke, Repulse, Watch, Rally, sight,
  Crossing and Wizard spell consequences. Compact recent events may use the
  complete Battle log reader when they exceed their reserved area.
- `dense-report.json`: 20 additional native inputs place real Guard/Smoke/Pin
  markers; inspected markers remain clear of adjacent health text and the footer.
- Full suite: **1,156 passed in 149.43s**. Tribes: 60 AI / 20 scene runs.
  Linked Shardbound: 12 campaigns / 12 scenes, **2,226 inputs**, 2,238 ticks,
  including two message-reader inputs. All bounded invariant checks pass.

All six retained PNGs were opened and inspected. Independent review also
inspected the remaining error pages, role views, full log and Settings scope.
Earlier verification caught and fixed spell-key swallowing and a stress-driver
assumption that every unrecognized screen was the map. A sleeping display
interrupted one native attempt; the complete repeated run above passed.

Small board markers and command buttons retain their ordinary size, while
complete selected/target facts scale. No game rule, schema or framework API
changed. G01–G19 remain incomplete.
