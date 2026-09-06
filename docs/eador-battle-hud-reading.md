# Battle facts, guidance and history

**Text size / F2** now enlarges selected-unit health, readiness, attack/defense,
movement (including Pin and cargo), range, shared mana and spell ownership.
These facts, unit orders, spells and forecasts compose an ordinary measured
Column. Auto-play and Retreat sit beneath the board; their shortcuts remain A/T.

The footer wraps recent events beside contextual action guidance. Its reserved
height keeps the board still when orders change the log. Long history is always
available through **Battle log / L**, a complete read-only snapshot with shared
reading size and measured pages. Oversized battle messages expose **Read message
/ M**; they retain their exact text and leave the already-applied command intact.
Return restores the selected unit, aimed hex and pending order.

The existing game-owned message reader accepts a neutral body color for history;
diagnostics keep their error color. No model, schema or framework API changes.
Piece health badges and other compact board markers keep their normal sizes;
full selected/target health and effects are available in the enlarged sidebar.

Public tests preserve a real Guard result, stable board centers, keyboard refusal
cues, empty spell targeting and read-only log/settings isolation. The stress
driver explicitly visits message readers and asserts that reading cannot mutate
the campaign. Seed 4 retains the random click that first opened Battle log.
