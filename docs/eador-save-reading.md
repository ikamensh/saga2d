# Readable save slots

The Saves browser shares the 100/125 reading preference. T opens its setting;
Apply, Cancel and native resizing keep the first visible slot. Slot names,
timestamps, full campaign/phase metadata, recovery advice and immediate errors
use measured wrapped Labels. Previous/Next and Left/Right page complete rows.

Slot shortcuts keep their original identities: 1–3 are manual, 4–6 autosaves,
and Shift+number loads that slot's backup. Only shown rows own shortcuts; hidden
slots cannot save or load accidentally. The existing Save/Load switch, explicit
backup recovery and save-before-title flow keep their original policies. An
unreadable slot explains how to recover, and activating it shows the full error
without replacing the current campaign or changing the damaged bytes. Metadata
now distinguishes a completed battle awaiting acceptance from an active round.

The layout reserves measured error/footer space before paging slots. No slot
description or error is shortened to fit. Navigation buttons and the large title
keep their ordinary sizes. CampaignSaves owns metadata and checkpoint policy;
Saga2D continues to supply ordinary UI composition and safe file I/O without a
new API, save format or migration.

`tools/verify_eador_saves.py` runs with `--backend mock` or native Pyglet. Its
public-input tracer begins a linked campaign, saves an active battle, changes
reading size, explicitly saves another slot, refuses a 5,000-character invalid
version, recovers the original backup with Shift+1 and preserves every file.
It also refuses a real directory at a save-file path and recovers the
save-and-return-to-title flow through a different manual slot.

The separate read-only matrix displays twelve earned/retained phases in load,
save and save-before-title modes at both reading sizes in three native windows.
It covers opening, battle, result, choice, departure, recovery, defeat, spent
recovery, completion, Challenge and actual v1/v10 saves. All descriptions remain
reachable once and every file stays byte-identical through layout changes.
Hidden-number activation is checked when native measurements produce more than
one page. A fresh Game verifies 125% persistence. Screenshots still require
inspection; these checks do not establish Windows or complete G10/G12.

For unusually long filesystem errors, the [complete diagnostic view](eador-diagnostics.md)
now preserves all text in measured pages while leaving the selected slot and its
explicit recovery controls available on return. Short errors remain inline.
