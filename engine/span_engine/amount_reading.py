from __future__ import annotations

from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.numeric_prosody import join_decimal_prosody

SINO_DIGIT_READINGS = {
    "0": "영",
    "1": "일",
    "2": "이",
    "3": "삼",
    "4": "사",
    "5": "오",
    "6": "육",
    "7": "칠",
    "8": "팔",
    "9": "구",
}


def read_integer_under_100_million(value: int, *, overflow_message: str) -> str:
    if value < 10000:
        return number_to_korean_under_10000(value)
    if value >= 100000000:
        raise ValueError(overflow_message)
    high = value // 10000
    low = value % 10000
    high_reading = "" if high == 1 else number_to_korean_under_10000(high)
    reading = f"{high_reading}만"
    if low:
        reading = f"{reading} {number_to_korean_under_10000(low)}"
    return reading


def read_decimal_amount_text(amount: str, *, overflow_message: str) -> str:
    integer_part, _, decimal_part = amount.partition(".")
    integer_reading = read_integer_under_100_million(
        int(integer_part.replace(",", "")),
        overflow_message=overflow_message,
    )
    if not decimal_part:
        return integer_reading
    return join_decimal_prosody(integer_reading, decimal_part)


__all__ = [
    "SINO_DIGIT_READINGS",
    "read_decimal_amount_text",
    "read_integer_under_100_million",
]
