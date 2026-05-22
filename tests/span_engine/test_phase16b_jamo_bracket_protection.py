from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[ㄱㄴㄷ]", "ㄱㄴㄷ"),
        ("입력 [ㄱㄴㄷ] 확인", "입력 ㄱㄴㄷ 확인"),
        ("(ㄱㄴㄷ)", ""),
        ("입력 (ㄱㄴㄷ) 확인", "입력 확인"),
    ],
)
def test_jamo_bracket_protection(text: str, expected: str) -> None:
    assert transform(text) == expected

