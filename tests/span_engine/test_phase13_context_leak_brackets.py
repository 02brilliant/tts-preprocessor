from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[2025-01-03]", "2025-01-03"),
        ("날짜는 [2025-01-03]입니다", "날짜는 2025-01-03입니다"),
        ("(2025-01-03)", ""),
        ("날짜는 (2025-01-03)입니다", "날짜는 입니다"),
        ("[13:05에]", "13:05에"),
        ("회의는 [13:05에] 시작", "회의는 13:05에 시작"),
        ("(13:05에)", ""),
    ],
)
def test_bracket_protection_with_date_time(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 13:05(시작)에 열린다", "회의는 십삼시 오분에 열린다"),
        ("13:05(시작)", "13:05"),
        ("값은 12:30(비율)이다", "값은 12:30이다"),
    ],
)
def test_parenthesis_context_does_not_gate_time(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_bracket_internal_date_time_claim_is_skipped() -> None:
    output = transform_with_trace("날짜는 [2025-01-03]입니다")

    assert output.normalized_text == "날짜는 2025-01-03입니다"
    assert not any(claim.owner in {"date", "time"} for claim in output.trace.claim_logs)
    assert output.trace.bracket_filter_logs
