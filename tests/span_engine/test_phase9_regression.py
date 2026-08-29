from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("OpenAI", "오픈 에이아이"),
        ("USB3", "USB3"),
        ("3.14", "삼쩜일사"),
        ("3~8cm", "삼에서 팔-센티미터"),
        ("50kg", "오십-킬로그램"),
        ("21명", "스물한-명"),
        ("종로3가", "종로 삼-가"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
        ("{{S:사용자입력}}", "{{S:사용자입력}}"),
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("AI이 적용됐다", "에이아이이 적용됐다"),
    ],
)
def test_phase9_regression_cases(text: str, expected: str) -> None:
    assert transform(text) == expected
