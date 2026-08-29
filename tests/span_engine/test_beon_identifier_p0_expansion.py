from __future__ import annotations

import pytest

from engine.main import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1번 선택지", "일번 선택지"),
        ("1번 버튼", "일번 버튼"),
        ("2번 메뉴", "이번 메뉴"),
        ("4번 승강장", "사번 승강장"),
        ("3번 선수", "삼번 선수"),
        ("4번 타자", "사번 타자"),
        ("5번 주자", "오번 주자"),
        ("6번 국도", "육번 국도"),
        ("1번 방", "1번 방"),
        ("5번 차량", "5번 차량"),
    ],
)
def test_beon_identifier_p0_exact_allowlist(text: str, expected: str) -> None:
    assert transform(text) == expected
