from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "blocked_owner"),
    [
        ("[12.12 사태]", "12.12 사태", "event"),
        ("사건은 [12.12 사태]입니다", "사건은 12.12 사태입니다", "event"),
        ("[긴급번호 112는]", "긴급번호 112는", "emergency"),
        ("[국민콜 110에]", "국민콜 110에", "public_number"),
    ],
)
def test_square_bracket_internal_phase14_claims_are_blocked(
    text: str, expected: str, blocked_owner: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert not any(claim.owner == blocked_owner for claim in output.trace.claim_logs)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(12.12 사태)", ""),
        ("사건은 (12.12 사태)입니다", "사건은 입니다"),
        ("(긴급번호 112는)", ""),
    ],
)
def test_parenthesized_phase14_claims_are_elided_without_claim(text: str, expected: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert not any(
        claim.owner in {"event", "emergency", "public_number"}
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("text", "expected", "forbidden"),
    [
        ("112(긴급)에 신고", "백십이에 신고", "일일이에 신고"),
        ("119(화재)에 연락", "백십구에 연락", "일일구에 연락"),
        ("12.12(사태)", "십이-쩜-일이", "십이십이"),
    ],
)
def test_parenthesis_internal_context_does_not_leak(
    text: str, expected: str, forbidden: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert output.normalized_text != forbidden
    assert not any(
        claim.owner in {"event", "emergency"} for claim in output.trace.claim_logs
    )
