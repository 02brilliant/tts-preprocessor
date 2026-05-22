from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("종로3가", "종로삼가"),
        ("주소는 종로3가입니다", "주소는 종로삼가입니다"),
        ("역삼동 12번지", "역삼동 십이번지"),
        ("주소는 역삼동 12번지입니다", "주소는 역삼동 십이번지입니다"),
        ("종로3가는 복잡하다", "종로삼가는 복잡하다"),
        ("역삼동 12번지는 조용하다", "역삼동 십이번지는 조용하다"),
    ],
)
def test_phase17c_admin_suffix_basic_expected_output(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
