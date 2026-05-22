from __future__ import annotations

import re

_COMMA_INTEGER_RE = re.compile(r"\d{1,3}(?:,\d{3})+")
_PLAIN_INTEGER_RE = re.compile(r"\d+")
_DIGIT_READINGS = {
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
_SMALL_UNITS = ("", "십", "백", "천")
_LARGE_UNITS = ("", "만", "억", "조", "경")


def normalize_integer_text(text: str) -> str | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if _COMMA_INTEGER_RE.fullmatch(text):
        normalized = text.replace(",", "")
    elif _PLAIN_INTEGER_RE.fullmatch(text):
        normalized = text
    else:
        return None
    if len(normalized) > 1 and normalized.startswith("0"):
        return None
    return normalized


def read_integer_text(text: str) -> str | None:
    normalized = normalize_integer_text(text)
    if normalized is None:
        return None
    return read_integer_value(int(normalized))


def read_spaced_integer_text(text: str) -> str | None:
    normalized = normalize_integer_text(text)
    if normalized is None:
        return None
    return read_spaced_integer_value(int(normalized))


def read_integer_value(value: int) -> str:
    if not isinstance(value, int):
        raise TypeError("value must be int")
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return _DIGIT_READINGS["0"]

    groups: list[int] = []
    remaining = value
    while remaining:
        groups.append(remaining % 10000)
        remaining //= 10000
    if len(groups) > len(_LARGE_UNITS):
        raise ValueError("value is too large")

    parts: list[str] = []
    for index in range(len(groups) - 1, -1, -1):
        group_value = groups[index]
        if group_value == 0:
            continue
        group_reading = _read_under_10000(group_value)
        large_unit = _LARGE_UNITS[index]
        if large_unit == "만" and group_reading == "일":
            parts.append(large_unit)
        else:
            parts.append(f"{group_reading}{large_unit}")
    return "".join(parts)


def read_spaced_integer_value(value: int) -> str:
    if not isinstance(value, int):
        raise TypeError("value must be int")
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return _DIGIT_READINGS["0"]

    groups: list[int] = []
    remaining = value
    while remaining:
        groups.append(remaining % 10000)
        remaining //= 10000
    if len(groups) > len(_LARGE_UNITS):
        raise ValueError("value is too large")

    parts: list[str] = []
    for index in range(len(groups) - 1, -1, -1):
        group_value = groups[index]
        if group_value == 0:
            continue
        group_reading = _read_under_10000(group_value)
        large_unit = _LARGE_UNITS[index]
        if large_unit == "만" and group_reading == "일":
            parts.append(large_unit)
        else:
            parts.append(f"{group_reading}{large_unit}")
    return " ".join(parts)


def read_decimal_text(text: str) -> str | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    integer_part, dot, fractional_part = text.partition(".")
    if not dot or not fractional_part.isascii() or not fractional_part.isdigit():
        return None
    integer_reading = read_integer_text(integer_part)
    if integer_reading is None:
        return None
    return f"{integer_reading}쩜{read_decimal_fraction_digits(fractional_part)}"


def read_decimal_fraction_digits(fractional_part: str) -> str:
    """Read ordinary decimal fractional digits.

    This helper is intentionally for ordinary decimal owners only. Phone,
    code, date/time, and identifier digit-sequence readers keep their own
    owner-specific zero policy.
    """
    if not isinstance(fractional_part, str):
        raise TypeError("fractional_part must be str")
    if not fractional_part or not fractional_part.isascii() or not fractional_part.isdigit():
        raise ValueError("fractional_part must be non-empty ASCII digits")
    return "".join(_DIGIT_READINGS[digit] for digit in fractional_part)


def read_number_text(text: str) -> str | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if "." in text:
        return read_decimal_text(text)
    return read_integer_text(text)


def read_fraction_text(numerator: str, denominator: str) -> str | None:
    numerator_normalized = normalize_integer_text(numerator)
    denominator_normalized = normalize_integer_text(denominator)
    if numerator_normalized is None or denominator_normalized is None:
        return None
    numerator_value = int(numerator_normalized)
    denominator_value = int(denominator_normalized)
    if numerator_value <= 0 or denominator_value <= 0:
        return None
    return (
        f"{read_integer_value(denominator_value)}분의 "
        f"{read_integer_value(numerator_value)}"
    )


def _read_under_10000(value: int) -> str:
    if value <= 0 or value > 9999:
        raise ValueError("value must be between 1 and 9999")
    digits = f"{value:04d}"
    parts: list[str] = []
    for offset, digit in enumerate(digits):
        if digit == "0":
            continue
        unit = _SMALL_UNITS[3 - offset]
        if digit == "1" and unit:
            parts.append(unit)
        else:
            parts.append(f"{_DIGIT_READINGS[digit]}{unit}")
    return "".join(parts)


__all__ = [
    "normalize_integer_text",
    "read_decimal_text",
    "read_decimal_fraction_digits",
    "read_fraction_text",
    "read_integer_text",
    "read_integer_value",
    "read_number_text",
    "read_spaced_integer_text",
    "read_spaced_integer_value",
]
