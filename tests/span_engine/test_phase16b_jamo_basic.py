from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ㄱ", "기역"),
        ("ㄴ", "니은"),
        ("ㅏ", "아"),
        ("ㅣ", "이"),
        ("ㄱㄴㄷ", "기역 니은 디귿"),
        ("ㅏㅣ", "아 이"),
        ("ㄱㅏ", "기역 아"),
        ("입력 ㄱㄴㄷ", "입력 기역 니은 디귿"),
        ("자모 ㅏㅣ 테스트", "자모 아 이 테스트"),
        ("ㄱ AI", "기역 에이아이"),
        ("AI ㄱ", "에이아이 기역"),
        ("ㄱ 123", "기역 백이십삼"),
    ],
)
def test_jamo_basic_expected_output(text: str, expected: str) -> None:
    assert transform(text) == expected

