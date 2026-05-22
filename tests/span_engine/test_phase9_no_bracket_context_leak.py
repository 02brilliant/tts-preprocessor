from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_square_bracket_ai_and_number_are_not_claimed() -> None:
    output = transform_with_trace("[AI] [123] JSON")

    assert output.normalized_text == "AI 123 제이슨"
    assert not any(
        claim.owner in {"dictionary", "acronym_fallback", "number"}
        and claim.span.start < 10
        for claim in output.trace.claim_logs
    )
    assert any(claim.owner == "dictionary" and claim.span.start >= 10 for claim in output.trace.claim_logs)


def test_parenthesis_ai_and_number_are_not_claimed() -> None:
    output = transform_with_trace("(AI) (123) JSON")

    assert output.normalized_text == "제이슨"
    assert all(claim.owner == "dictionary" for claim in output.trace.claim_logs)
    assert all(claim.span.start >= 11 for claim in output.trace.claim_logs)
