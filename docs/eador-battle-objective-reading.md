# Battle objective reading

The shared **Text size / F2** setting now enlarges the complete objective banner
alongside target forecasts. Rout explains hero survival and exhaustion. Hold
shows the live progress/deadline and explicitly describes consecutive enemy turns
and the reset when control is lost. Extraction shows its deadline, exact escape
conditions and the current reason Evacuate is unavailable, or the ready instruction.

Shardbound composes ordinary Labels, Rows, Columns and Buttons. It measures the
banner with `Scene.measure`, then fits the existing HexGrid underneath. The same
grid places tiles and resolves input. Locate seal/exit and Evacuate remain visible;
the selected unit, aimed cell and queued order survive reading/resize changes.
No model, save schema, terrain or framework API changes.

The public-input regression locates a real paid Watch's seal, changes reading size
and all three supported verification windows, then checks exact state/aim and
complete scoring instructions. `tools/verify_eador_forecast.py` now checks live
objective facts at every input and pauses each newly reached objective state for
the same native 100/125 × three-window matrix. Its paid Watch and Crossing routes
still execute their original hold/escape outcomes and exact save/reloads.

This increment leaves selected-unit HUD values, action guidance and the battle log
at their existing sizes. Other early-access criteria remain incomplete.
