# Readable saves and recovery

Rendered source is `4d7e9e7`. The native run began at `bdcfe3f` with the
implementation uncommitted; its recorded HEAD is preserved. All 172 recorded
source/fixture hashes match the committed files. The linked fuzz hashes also
match, with no changes during either run. See [provenance](provenance.json).

- The full suite passed **1,114 tests in 133.76 seconds**. Tribes passed 60 AI
  games and 20 scene runs. [Linked Shardbound stress](linked-fuzz.json) passed
  12 model campaigns and 12 scene runs with 2,208 inputs.
- The [native Pyglet matrix](native.json) passed **54 complete pages and 301
  inputs** across twelve earned/retained phases, both reading sizes, three
  native windows and load/save/save-before-title modes. Full descriptions and
  original slot shortcuts remain intact; hidden slots cannot receive input.
- The input journey changes and restarts the shared setting, refuses a damaged
  version, explicitly restores a backup, rejects real directory paths, then
  recovers save-and-return-to-title using another manual slot. Exact reloads
  and byte-identical files are asserted where the interaction is read-only.

All five retained PNGs were opened and inspected: the Settings scope, larger
slot pages including a victory awaiting acceptance, the full directory error,
and the failed save-before-title screen. Text and controls remain separate.
The implementation uses existing game reading helpers and framework Labels;
it adds no save schema or framework API.

This is macOS source evidence, not a packaged build, Windows or human-playtest
result. G01–G19 remain incomplete. The `0e27175` artifact predates this work.
