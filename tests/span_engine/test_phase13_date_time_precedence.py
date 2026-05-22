from __future__ import annotations

import pytest

from engine.span_engine import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("2025-01-03", "이천이십오년 일월 삼일", "date"),
        ("2025/01/03", "이천이십오년 일월 삼일", "date"),
        ("13:05에", "십삼시 오분에", "time"),
        ("3시 5분", "세 시 오분", "time"),
        ("1~11월", "일월에서 십일월", "range"),
        ("3월", "삼월", "date"),
        ("2025년", "이천이십오년", "date"),
    ],
)
def test_date_time_precedence(text: str, expected: str, owner: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert any(claim.owner == owner for claim in output.trace.claim_logs)
    if owner in {"date", "time"}:
        assert not any(claim.owner == "number" for claim in output.trace.claim_logs)
