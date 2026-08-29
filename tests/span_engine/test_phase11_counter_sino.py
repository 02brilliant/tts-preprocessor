from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21층", "21층"),
        ("21호", "21호"),
        ("21동", "21동"),
        ("21년", "이십일년"),
        ("01월", "일월"),
        ("03일", "삼일"),
        ("2개월", "이개월"),
        ("21원", "이십일-원"),
        ("21도", "이십일도"),
        ("3미터", "삼-미터"),
        ("3킬로그램", "삼-킬로그램"),
        ("2학년", "이학년"),
        ("2학기", "이학기"),
        ("62회", "육십이-회"),
    ],
)
def test_sino_counter_owner(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_prefixed_ordinal_counter_uses_numeric_suffix_policy_v102() -> None:
    assert transform("제62회") == "제-육십이회"
