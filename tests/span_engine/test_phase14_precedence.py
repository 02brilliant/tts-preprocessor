from __future__ import annotations

import pytest

from engine.span_engine import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("12.12 사태", "십이십이 사태", "event"),
        ("긴급번호 112는", "긴급번호 일일이는", "emergency"),
        ("국민콜 110에 문의", "국민콜 일일공에 문의", "public_number"),
        ("2025-01-03", "이천이십오년 일월 삼일", "date"),
        ("13:05에 시작", "십삼시 오분에 시작", "time"),
        ("3~8cm", "삼에서 팔-센티미터", "range_with_unit"),
    ],
)
def test_phase14_owner_precedence(text: str, expected: str, owner: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert any(claim.owner == owner for claim in output.trace.claim_logs)


def test_one_digit_event_claims_event_owner() -> None:
    output = transform_with_trace("12.3 비상계엄")

    # Phase 28B: Expected to fail until Phase 28C
    assert output.normalized_text == "십이삼 비상계엄"
    assert any(claim.owner == "event" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)


def test_emergency_disallowed_tail_uses_explicit_counter_policy() -> None:
    output = transform_with_trace("112명")

    assert output.normalized_text == "백십이-명"
    assert not any(claim.owner == "emergency" for claim in output.trace.claim_logs)
    assert any(claim.owner == "counter_noun" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)
