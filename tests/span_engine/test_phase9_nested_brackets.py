from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("문장(임시[확인])입니다", "문장입니다"),
        ("가격은 [3kg(확인)]입니다", "가격은 3kg(확인)입니다"),
        ("[AI(테스트)]", "AI(테스트)"),
        ("(AI[테스트])", ""),
    ],
)
def test_nested_brackets_follow_outermost_policy(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "문장(임시 입니다",
        "가격은 [3kg입니다",
        "문장 임시)입니다",
        "가격은 3kg]입니다",
    ],
)
def test_incomplete_brackets_are_preserved(text: str) -> None:
    assert transform(text) == text
