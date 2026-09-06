# Tactical forecast reading evidence

Production source: **086ce14**. All 144 recorded native source hashes match this
commit. The original report HEAD is preserved; [provenance](provenance.json)
records the implementation and artifact hashes.

- [Native matrix](native.json): **96 layouts / 865 inputs / 21 exact save/reloads**.
  Sixteen encountered forecast/status categories at 100/125 in 1280×720,
  1280×800 and 1920×1080 windows. Every reading pause preserves exact saved
  state, selected unit, cursor, hovered hex and targeting mode.
- The seven journey reports retain real paid routes and exact ability outcomes,
  including the Wizard's damage/mana result and unchanged T retreat action.
- Full suite: **1,144 passed in 117.02 seconds**. The final verifier-only change
  retained the Wizard's input report; production/test code stayed identical.
- Independent review: **28 focused tests**, native pointer changes, both Settings
  entry paths, exact aim preservation and spell execution. Its one discovery
  finding, missing arrow guidance, was fixed and protected by a regression.

All eight retained screenshots were opened and inspected. Forecast text fits
above End battle round without clipping or overlapping controls. The current
and older sight guidance remain distinct. Settings accurately names the scope.

This is source/Pyglet evidence, not a new package or human playtest. Selected-unit
HUD values, objective text and the battle log retain their existing sizes.
All G01–G19 release gates remain incomplete.
