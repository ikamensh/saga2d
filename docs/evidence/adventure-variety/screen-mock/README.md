# Screen input migration

All five `tests/eador/test_screen_scene.py` cases pass in 17.11 seconds.
The losslessly compressed reports and logs retain actual mock input and saved
continuation. No native run occurred in this check.

The Scout wins in round 5 with all six allies alive, spending two Heal costs
and killing the Sapper before its first Smoke. Its deliberately failed branch
instead loses the hero in round 53 and all five troop IDs 1–5. Recovery and
return travel advance turn 6 to turn 10, retaining the one surviving 20-HP
enemy Archer. Four new Swordsmen, IDs 6–9, cost 180 gold; explicit Scout and
Swordsman orders rout that Archer in round 1. All retry allies survive, with
four total wounds. The full failed/retry journey records 644 inputs and
62 exact reload pairs. No dead veteran is silently resurrected.

The initial shared retry check executed successfully but failed its obsolete
round-3 expectation. That failure is retained. The final test checks the
observed round-1 rout, actual casualties, new roster, expenditure and reward.
The verifier closes its public Game session in `finally`.
