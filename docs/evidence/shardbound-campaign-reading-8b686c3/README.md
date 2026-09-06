# Campaign transition reading evidence

All captures and checks use source **8b686c337dc8f3dc5b56813ade0144a19e2ba6e7**.
[Provenance](provenance.json) records exact artifact hashes and screenshot sizes.
Seven representative PNGs are retained unchanged; they and the second oversized
diagnostic page were opened and inspected.

The [native matrix](matrix.json) contains 570 measured transition/item layouts
from 16 actual earned or historical saved states at 100%/125% in 1280×720,
1280×800 and 1920×1080 windows. It records 999 public input activations and four
exact save reloads, including the long-path recovery journey. It checks complete
offer/rival-arrival prose, every retinue item and focused relic description,
actual veteran health/funding, both finales and recovery/ending records.

| Frame | Evidence |
| --- | --- |
| [Departure at 100%](standard-departure-100-page-1.png) | Both offers, arrival timing and carryover rules. |
| [Retinue after 125% reflow](focus-reflow-125.png) | Kept relics survive; the gold focus remains on a visible row. |
| [Historical Challenge-1 recovery](saved-challenge1-recover-125-page-1.png) | Actual saved veterans, funding and one-recovery rules. |
| [Completed recovered campaign](throne-completed-125-page-1.png) | Three earned records, hero build and used recovery. |
| [Ordinary filesystem error and notes](standard-departure-save-error-125-page-2.png) | Full error remains visible while whole prose sections page. |
| [Oversized diagnostic](long-path-error-page-1.png) | A real 760-character path produces a complete two-page diagnostic. |
| [Return from the diagnostic](long-path-return-to-retinue-125.png) | Retinue stays selected; Read error reopens it before retrying. |

The exact source passed **1,126 tests in 104.42 seconds**, Tribes 60 AI games +20
monkey runs (seed17), and [linked Shardbound stress](linked-fuzz.json): 60 model
campaigns +20 scene runs /3,730 inputs. The random model runs ended in defeat;
these are invariant checks, not evidence of balance or enjoyable play.

The independent reviewer reproduced the oversized-path failure before the fix.
The retained public regression now reads the complete diagnostic, ignores hidden
retinue/abandon keys, returns through Settings/Saves, preserves selections and
page anchors, retries after removing the real directory conflict and reloads the
exact pre-departure snapshot. No model values or messages were injected.

This is scoped reading/layout and input evidence. It does not claim global text
scaling, Steam readiness, broader platform testing or a rebuilt package.
