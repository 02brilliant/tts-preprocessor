from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$100", "백-달러"),
        ("€50", "오십-유로"),
        ("₩1200", "천이백-원"),
        ("¥500", "오백-엔"),
        ("£20", "이십-파운드"),
        ("USD 20", "이십-달러"),
        ("EUR 50", "오십-유로"),
        ("KRW1000", "천-원"),
        ("JPY 500", "오백-엔"),
        ("GBP20", "이십-파운드"),
        ("가격은 $100입니다", "가격은 백-달러입니다"),
        ("비용은 €50을 냈다", "비용은 오십-유로를 냈다"),
        ("예산은 KRW1000은 충분하다", "예산은 천-원은 충분하다"),
        ("USD 20는 많다", "이십-달러는 많다"),
    ],
)
def test_currency_owner_minimal_supported_patterns(text: str, expected: str) -> None:
    assert transform(text) == expected
