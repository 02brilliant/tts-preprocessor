from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2사람", "두-사람"),
        ("3마리", "세-마리"),
        ("4그루", "네-그루"),
        ("5송이", "다섯-송이"),
        ("6자루", "여섯-자루"),
        ("7알", "일곱-알"),
        ("8벌", "여덟-벌"),
        ("9켤레", "아홉-켤레"),
        ("10그릇", "열-그릇"),
        ("11공기", "열한-공기"),
        ("12잔", "열두-잔"),
        ("20병", "스무-병"),
        ("23조각", "스물세-조각"),
        ("13살", "열세-살"),
        ("고양이 3마리", "고양이 세-마리"),
        ("아이 2사람", "아이 두-사람"),
        ("나이는 13살입니다", "나이는 열세-살입니다"),
    ],
)
def test_native_counter_owner(text: str, expected: str) -> None:
    assert transform(text) == expected
