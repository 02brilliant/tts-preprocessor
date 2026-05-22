from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025.01.03", "이천이십오년 일월 삼일"),
        ("행사는 2025.01.03에 열린다", "행사는 이천이십오년 일월 삼일에 열린다"),
        ("2026.10.21", "이천이십육년 시월 이십일일"),
        ("2025.13.03", "이공이오쩜 일삼쩜 공삼"),
        ("2025.01.32", "이공이오쩜 공일쩜 삼이"),
        ("2024.00.10", "이공이사쩜 공공쩜 일공"),
    ],
)
def test_dotted_full_date_valid_and_invalid_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "2025.01",
        "버전 2025.01",
        "2025.1",
        "docs/2025.01.03",
        "http://x/2025.01.03",
        "v2025.01.03",
        "버전 2025.01.03",
    ],
)
def test_dotted_date_preserve_guards_policy_v1(text: str) -> None:
    assert transform(text) == text


def test_bracketed_dotted_date_is_protected_then_unwrapped_policy_v1() -> None:
    output = transform_with_trace("[2025.01.03]")

    assert output.normalized_text == "2025.01.03"
    assert not any(
        claim.owner in {"date", "date_time.date", "decimal"}
        for claim in output.trace.claim_logs
    )
