# Departure cargo retirement

The candidate sweep at `e5840c7e31cf66e237bfd2da33b326c3e15ec2b3` reached an
obsolete experiment's assumption: `earned_departures()` required living Adept 5
after the first shard. The actual paid route still wins, but that veteran dies.
This is a prototype input failure, not a production campaign failure.

[The exact diagnosis](current-survivors.json.gz) retains the purchased Watch
state, the state after its existing manual route, the current departure, the
historical comparison input, complete campaign log and source hashes. It follows
`prepare_control_watch(State.new_campaign(0, 'Commander'))`,
`watch_control_route`, `finish_battle`, and `play_stage` once, passing one
`CpuBudget(25)` through the existing helpers. No troops, funding or saved fields
were inserted; no cargo branch, matrix or native window ran. Source hashes stayed
unchanged. The measured interval was 0.061368 seconds wall / 0.049388 seconds CPU;
this short interval below the budget's work threshold does not demonstrate a
25% instantaneous CPU cap.

The current first capital assault on turn 16 loses Militia 1 and 2, Sapper 4,
Adept 5 and Skyrider 6, then retreats for a real 20-gold loss. The policy buys
five Swordsmen and wins on turn 19 with 602 gold / 42 crystals. The survivors are
Archer 3 at level 3 and Swordsmen 7–11 at level 1. The original `747b1bf` input
departed on turn 16 with 575 gold / 32 crystals, retaining Militia 1, Adept 5 and
Swordsman 7.

The experiment's distinguishing control was carrying the expensive Adept versus
leaving it behind for cash. Substituting a surviving Swordsman would answer a
different question; restoring the Adept would falsify the earned input. Cargo
has no production callers and was deferred without resolving G07, so the live
prototype and only its dedicated CPU-budget regression were deleted. The other
economic prototypes and tests remain.

The [historical proposal](../../eador-departure-cargo-proposal.md) now gives an
isolated historical reproduction command. Its original JSON, the later CPU
receipts and retained probe are unchanged, and their source remains in Git.
The original JSON SHA-256 is
`05381ce89b38c6a77a4ef9af367d89408cca8cfc4bdeea56b1569c404b217df1`.
These retained experiments do not validate current cargo behavior or close an
Early Access gate.

After removal, `python -m pytest --collect-only
tests/tools/test_retained_prototype_budget.py -q` collected exactly the three
remaining tests in 0.01 seconds ([output](collection.txt)). No test bodies or
prototype continuations were rerun for this deletion; the ordinary candidate
sweep retains responsibility for the remaining tests.
