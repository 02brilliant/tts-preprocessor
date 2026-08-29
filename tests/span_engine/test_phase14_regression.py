from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI", "에이아이"),
        ("FTA은 적용됐다", "에프티에이는 적용됐다"),
        ("가격은 [3kg]입니다", "가격은 3kg입니다"),
        ("50kg", "오십-킬로그램"),
        ("21명", "스물한-명"),
        ("3~8cm", "삼에서 팔-센티미터"),
        ("2025-01-03", "이천이십오년 일월 삼일"),
        ("회의는 13:05에 시작한다", "회의는 십삼시 오분에 시작한다"),
        ("12.12 사태", "십이십이 사태"),
        ("긴급번호 112는", "긴급번호 일일이는"),
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("3.14", "삼쩜일사"),
        ("12.12", "십이쩜일이"),
        ("2025.01.03", "이천이십오년 일월 삼일"),
        ("5·18", "오·일팔"),
    ],
)
def test_phase14_expected_owner_outputs(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "score 12:30",
        "112abc",
    ],
)
def test_phase14_unsupported_or_ambiguous_inputs_preserve(text: str) -> None:
    assert transform(text) == text


def test_phase14_range_compatible_korean_suffix_transform() -> None:
    assert transform("3~8명") == "삼에서 팔-명"
