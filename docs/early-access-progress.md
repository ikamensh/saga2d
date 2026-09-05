# Early Access progress and evidence

Criteria: [early-access-criteria.md](early-access-criteria.md).
All release gates remain incomplete unless evidence below explicitly proves
them. Last completed development milestone was a single-shard prototype;
the current goal is substantially broader.

## Baseline audit — 2026-09-05

- Authoritative baseline: `2d26787`; only unrelated `.gitignore` work was
  present when the release-quality goal began.
- Existing tests: 314 at the preceding milestone, confirmed by a fresh run.
- The release gap includes content/decision variety, rival strategy,
  progression choices, save robustness, usability, audio, packaging and
  release-scale testing. These are not resolved by a green baseline suite.
- Model audit reproduced a safe capital-camping strategy: by turn 65 the
  army reached level 4 with 791 gold and 66 crystals, then won at turn 68.
  Scheduled attacks provide repeated rewards without a changing opponent.
- Rival conquest can replace a four-unit eastern guard with two units,
  reducing danger when the rival expands. Crystals start at four while
  the only expense is one Mage Tower costing two.

## Gate status

G01–G19: **incomplete**. The baseline has partial evidence for basic tactical
commands (G08), public-behavior tests (G16) and framework separation (G17),
but does not satisfy their release-candidate scope.

## Progression and save reliability — 2026-09-05

- All four heroes have two rankable disciplines. Every discipline and
  relic has a tested behavioral effect; mastery can stay on its chosen
  path instead of converging into the same build at level three.
- Six adventure archetypes have distinct defending parties and rewards.
  Six relics offer equipment-versus-money choices, with explicit duplicate
  handling. Their choices and equipped effects have playable UI.
- Schema v2 validates game IDs and state invariants, including live battle
  context and pending decisions. Captured prototype fixtures migrate
  explicitly. Corrupt JSON, oversized integers and excessive nesting
  report recoverable errors at the parser boundary.
- Three manual slots, three rolling autosaves, a save browser and explicit
  previous-file recovery are usable from live campaigns and decisions.
  Failed loads preserve live state; incompatible campaigns preserve their
  backups; Save & title leaves only after writing a chosen manual slot.
- Framework additions remain generic: queued-input transition safety;
  durable, validated SaveManager writes and explicit backup reads; cleanup
  of partially initialized scenes and failed game startup.
- Standalone macOS ARM64 build and extracted-package smoke passed. See
  [packaging.md](packaging.md) for commands, hashes and limitations. That
  artifact is an earlier source snapshot; Windows and a clean-machine
  release candidate remain unverified.
- Latest checkpoint: **395 tests passed**, including complete campaign
  input, saved decisions, equipment, damaged-file recovery and safe return
  to title. Real Pyglet keyboard/mouse verification passed, including
  Shift-number backup recovery. Screenshots of shard, battles, guide,
  choices, inventory, save browser and error states were inspected at
  1280×800 / macOS HiDPI (`/tmp/shardbound-reviewed`).
- Independent review found and drove fixes for giant-number JSON escaping
  the game error boundary and repeated equipment hotkeys rotating away
  useful autosaves. Framework lifecycle tests also reproduce resource
  leaks and startup failure recovery.

G01–G19 remain incomplete. This increment advances G03–G05, G12–G14,
G16–G17; content counts alone do not establish their full release bar.
Large-scale stress evidence is running separately. Immediate design work
is a finite opponent with observable intent, resources and lasting army
losses; the current timer-driven rival remains a known release gap.

No release claim or publication is authorized by this progress log.
