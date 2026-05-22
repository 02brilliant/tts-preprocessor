from __future__ import annotations

SINO_DIGITS = {
    0: "영",
    1: "일",
    2: "이",
    3: "삼",
    4: "사",
    5: "오",
    6: "육",
    7: "칠",
    8: "팔",
    9: "구",
}

SINO_UNITS = ((1000, "천"), (100, "백"), (10, "십"))


def number_to_korean_under_10000(value: int) -> str:
    if not isinstance(value, int):
        raise TypeError("value must be int")
    if value < 0 or value > 9999:
        raise ValueError("value must be between 0 and 9999")
    if value == 0:
        return SINO_DIGITS[0]

    remaining = value
    parts: list[str] = []
    for unit_value, unit_name in SINO_UNITS:
        digit = remaining // unit_value
        remaining %= unit_value
        if digit == 0:
            continue
        if digit > 1:
            parts.append(SINO_DIGITS[digit])
        parts.append(unit_name)
    if remaining:
        parts.append(SINO_DIGITS[remaining])
    return "".join(parts)


__all__ = ["number_to_korean_under_10000"]
