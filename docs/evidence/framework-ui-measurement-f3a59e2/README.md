# Unattached UI measurement

Implementation and migrated callers are committed at `f3a59e2`. Native and
linked-stress reports preserve the HEAD recorded before that commit; all
recorded source hashes match the committed files. [Provenance](provenance.json)
records that comparison and distinguishes the older rival matrix format,
which emits no source hashes, from the hashed reports.

- **1,119 full tests passed in 94.42 seconds**. Tribes passed 60 AI games and
  20 scene runs; linked Shardbound passed 12 model campaigns and 12 scene runs
  with 2,208 input activations.
- The independent [native example](native.json) passed 12 layouts and 22
  inputs. It measures short/long cards with two fonts in three window sizes,
  verifies their eventual rendered dimensions, and accepts keyboard/mouse
  orders only after the card joins the visible UI.
- Migrated Shardbound [Saves](saves.json) passed 54 pages / 301 inputs, including
  damaged files and explicit backup/title recovery. [Rival intelligence](rival.json)
  passed 90 layouts / 818 inputs / one exact reload at the same frozen source.

All four retained images were opened and inspected: both independent cards,
larger complete save metadata and the six-troop rival view. Font measurements,
wrapping and controls retain their prior layout. The new primitive contains
no game imports, content, paging or save policy. See the
[interface and independent runnable example](../../framework-ui-measurement.md).

This is a development checkpoint; it does not pass the release/platform or
human-playtest gates. The older packaged Mac checkpoint predates these changes.
