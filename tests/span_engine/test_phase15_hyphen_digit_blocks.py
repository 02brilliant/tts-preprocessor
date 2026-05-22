from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("123-456-7890", "일이삼 사오육 칠팔구공"),
        ("010-1234-5678", "공일공 일이삼사 오육칠팔"),
        ("1-1-9", "일 일 구"),
        ("12-34-56", "일이 삼사 오육"),
        ("1-2-3-4", "일 이 삼 사"),
        ("번호는 123-456-7890입니다", "번호는 일이삼 사오육 칠팔구공입니다"),
        ("전화는 010-1234-5678로", "전화는 공일공 일이삼사 오육칠팔로"),
        ("코드는 1-1-9입니다", "코드는 일 일 구입니다"),
    ],
)
def test_hyphen_digit_block_expected_output(text: str, expected: str) -> None:
    assert transform(text) == expected

