from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1-1-9", "일 일 구"),
        ("1-1-2", "일 일 이"),
        ("긴급번호 1-1-9는", "긴급번호 일 일 구는"),
        ("화재 1-1-9에 신고", "화재 일 일 구에 신고"),
    ],
)
def test_hyphen_emergency_like_numbers_route_to_hyphen_block(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_hyphen_emergency_forbidden_signature() -> None:
    assert transform("1-1-9") != "일일구"
    assert "일일구" not in transform("긴급번호 1-1-9는")

