from __future__ import annotations

import pytest

from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner", "blocked_owners"),
    [
        ("1-1-9", "일 일 구", "hyphen_digit_blocks", {"emergency", "counter_noun"}),
        ("1234-5678", "일이삼사 오육칠팔", "phone", {"hyphen_digit_blocks"}),
        ("12.12 사태", "십이십이 사태", "event", {"decimal", "number"}),
        ("긴급번호 112는 경찰 신고 번호다", "긴급번호 일일이는 경찰 신고 번호다", "emergency", {"number"}),
        ("21명", "스물한 명", "counter_noun", {"number"}),
    ],
)
def test_span_claim_owner_precedence(
    text: str,
    expected: str,
    owner: str,
    blocked_owners: set[str],
):
    output = transform_with_trace(text)
    owners = {claim.owner for claim in output.trace.claim_logs}
    assert output.normalized_text == expected
    assert owner in owners
    assert owners.isdisjoint(blocked_owners)
