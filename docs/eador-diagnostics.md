# Complete save/load diagnostics

Saves and troop replacement retain their ordinary inline messages when measured
text fits beside the complete controls. A longer real filesystem diagnostic now
opens a read-only `DiagnosticScene`; the original screen keeps a short failure
notice and a visible **Read error (D)** button. The entire original error remains
available. No pathname, exception or purchase consequence is truncated.

The view uses the existing game-owned `reading_text_pages` and Saga2D wrapped
Labels and `Scene.measure`. Left/Right or PageUp/PageDown change pages; Text size
(T) opens the existing shared 100/125 reading preference. Return or Esc returns
to the original slot or exact replacement review. A separate scene gives queued
input the framework's normal transition isolation: a second Enter, a number or
Space in the closing batch cannot load a save or confirm a replacement below it.
The diagnostic itself has no save, recovery or model commands.

Saves retains the activated slot during error reflow, with the same explicit
backup and other-slot controls. Replacement retains its outgoing troop, incoming
quote and applied status. Its completed acknowledgement can still open Saves to
write a different manual slot, without applying the purchase again. Retrying a
failed command opens its new complete diagnostic; simply returning or resizing
does not repeatedly reopen the same message. The game owns this presentation and
retry policy; no framework primitive, file schema or persistence behavior changes.

`tools/verify_eador_diagnostics.py` reproduces errors using a valid nested save
directory longer than 700 characters and a directory occupying a real save-file
path. The native SaveScene reproduction previously exhausted its slot budget;
the replacement reproduction previously raised `Replacement does not fit`.
The public-input verifier covers a preserved backup, an actual earned six-troop
roster, Skyrider/Warden quotes, a paid Warden, complete diagnostic pages and
reading reflow at three window sizes. It checks exact state/file preservation,
reopening, input-batch isolation and explicit post-purchase save/reload. Mock
metrics can fit an error that native Verdana cannot; native verification is
therefore required for the original Saves failure.

Campaign and Title retain their existing diagnostic presentation. This increment
does not claim that every game message has been converted to the new view.

The [retained Mac evidence](evidence/shardbound-diagnostics-fca7596/README.md)
records the verified source, full suite, native input matrices, fuzz results and
five inspected screenshots.
