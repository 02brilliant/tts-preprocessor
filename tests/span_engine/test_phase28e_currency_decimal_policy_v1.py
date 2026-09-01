from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('$1.25', '일-쩜-이오-달러'),
        ('$1.25는', '일-쩜-이오-달러는'),
        ('$25.99', '이십오-쩜-구구-달러'),
        ('USD1.25', '일-쩜-이오-달러'),
        ('1.25USD', '일-쩜-이오-달러'),
        ('1.25 USD', '일-쩜-이오-달러'),
        ('USD 1.25', '일-쩜-이오-달러'),
        ('€1.25', '일-쩜-이오-유로'),
        ('€1,234.56', '천이백삼십사-쩜-오육-유로'),
        ('1,234.56€', '천이백삼십사-쩜-오육-유로'),
        ('EUR1,234.56', '천이백삼십사-쩜-오육-유로'),
        ('1,234.56 EUR', '천이백삼십사-쩜-오육-유로'),
    ],
)
def test_currency_decimal_full_consume_policy_v1(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("₩12,300", "만 이천삼백-원"),
        ("￥1,500", "천오백-엔"),
    ],
)
def test_integer_currency_existing_behavior_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "[€1.25]",
        "[$1.25]",
    ],
)
def test_bracketed_currency_decimal_is_protected_policy_v1(text: str) -> None:
    assert transform(text) == text[1:-1]


@pytest.mark.parametrize(
    "text",
    [
        "USD20abc",
        "€abc",
        "$100kg",
        "$1.25abc",
        "€1.25abc",
        "EUR1.25abc",
        "1.25EURabc",
    ],
)
def test_currency_invalid_tail_preserves_policy_v1(text: str) -> None:
    assert transform(text) == text
