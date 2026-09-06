# Reading the rival expedition

**Rival plan / V** uses the shared 100% / 125% Reading size. Its mode,
location, force names and health, income/upkeep, refit prices and applicable
counterplay advice scale and wrap. The existing large order title, treasury
amount and broken-expedition title retain their normal sizes, as do controls.

The finite army appears beside its treasury and operations. Every normal
six-troop expedition fits at 125% in the supported windows. Whole troop rows
can page if measured space requires it; prices and counterplay stay visible.
**Previous/Next** and Left/Right follow the displayed pages. Settings preserves
the first visible troop as the reading anchor. Existing message text reserves
footer space before force rows are packed.

**Text size / T** opens the existing Settings row. Apply/Cancel and restart
use the same preference as the other reading views. **Locate expedition / L**
selects the actual current province and returns to the map without travelling,
spending a turn or changing orders. **Close / Esc** simply returns. Inspecting
the rival does not write campaign saves.

The layout uses existing wrapped Labels, Columns, Rows and game-owned
`reading_pages`; vector portraits and health bars use component bounds.
No framework API, preference key, model rule or save schema was added.

`tools/verify_eador_rival_reading.py` prepares 15 actual saved states. All three
modes cover opening and first conquest. A paid Standard expedition supplies
announced attack, surviving wounds after interception/withdrawal, paid
recovery, healed troops, defeat and paid rebuilding. Existing v11, Challenge-1
and fortified-capital saves verify preserved rules and encirclement advice.
No troop health, money, intent or progress is inserted into these snapshots.

```sh
uv run python tools/verify_eador_rival_reading.py --output /tmp/shardbound-rival-reading
uv run python -m pytest tests/eador/test_rival_scene.py tests/eador/test_rival.py -q
```

The matrix reads every state at both sizes in 1280×720, 1280×800 and
1920×1080 windows. It checks complete troop identities/health, order/location,
prices, actual rule-dependent replacement delays and all breakout routes,
then compares full state JSON after keyboard/mouse Locate actions. It also
checks Settings Cancel/Apply/restart and an exact save/load after closing.
This verifies the rival reading slice toward G10; map and tactical HUD text
are outside it. These checks do not establish AI strength or campaign balance.
