"""Properties of the zero-dep fallback synthesiser.

When ANTHROPIC_API_KEY is absent, ``synthesise_consensus`` falls back
to :func:`_naive_consensus` — a keyword-overlap heuristic. Not as good
as an LLM synthesis but catches the spirit: "what concepts do both
reviewers mention?"
"""

from __future__ import annotations

from examples.ring_of_pain.ai_review import _naive_consensus


def test_naive_consensus_finds_shared_keyword() -> None:
    a = "The TITLE typography feels generic and placeholder-like."
    b = "Typography needs better hierarchy; title feels too large."
    out = _naive_consensus([("A", a), ("B", b)])
    assert "typography" in out.lower()
    assert "title" in out.lower()


def test_naive_consensus_separates_drift() -> None:
    a = "Alpha-only concept: rim glow."
    b = "Beta-only concept: shadow rendering."
    out = _naive_consensus([("A", a), ("B", b)])
    assert "rim" in out.lower() or "glow" in out.lower()
    assert "shadow" in out.lower() or "rendering" in out.lower()
    # Stop-words like "concept" are ≥ 4 chars; but they are genuine
    # shared keywords so we just make sure the drift sections have
    # the distinctive words.
    assert "Alpha-only concept" not in out  # exact phrasing not copied


def test_naive_consensus_handles_empty_overlap() -> None:
    a = "Apple banana cherry donkey elephant."
    b = "Fox giraffe hippo iguana jaguar."
    out = _naive_consensus([("A", a), ("B", b)])
    assert "No shared keywords" in out or "CONSENSUS" in out


def test_naive_consensus_is_structured_markdown() -> None:
    a = "Text placement is consistent."
    b = "Labels appear consistent across nodes."
    out = _naive_consensus([("A", a), ("B", b)])
    # Must have the same three-section skeleton as the Claude path so
    # downstream tooling can parse either variant.
    assert "## CONSENSUS" in out
    assert "## DRIFT" in out
    assert "## RECOMMENDED NEXT ACTION" in out
