from __future__ import annotations

import pytest

from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("회의는 12:30에 시작한다", "회의는 열두시 삼십분에 시작한다", "time"),
        ("12.12 사태", "십이십이 사태", "event"),
        ("긴급번호 112는 경찰 신고 번호다", "긴급번호 일일이는 경찰 신고 번호다", "emergency"),
        ("21명", "스물한-명", "counter_noun"),
        ("21층", "21층", "contextual_number_unit"),
    ],
)
def test_positive_gate_owner_claims(text: str, expected: str, owner: str):
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert any(claim.owner == owner for claim in output.trace.claim_logs)


@pytest.mark.parametrize(
    ("text", "expected", "blocked_owner"),
    [
        ("score 12:30", "score 12:30", "time"),
        ("긴급 신고는 112번으로 한다", "긴급 신고는 백십이-번으로 한다", "emergency"),
    ],
)
def test_negative_gate_paths_do_not_claim_blocked_owner(
    text: str,
    expected: str,
    blocked_owner: str,
):
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    claims = [] if output.trace is None else output.trace.claim_logs
    assert not any(claim.owner == blocked_owner for claim in claims)
