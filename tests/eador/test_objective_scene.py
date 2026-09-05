"""The authored objective can be learned, won and resumed through visible controls."""

from tools.verify_eador_objective import verify


def test_briefing_manual_hold_saved_continuation_and_deadline_with_visible_input(tmp_path):
    """Run the native verifier's complete public-input journey against recording observations."""
    verify(tmp_path, backend="mock")
