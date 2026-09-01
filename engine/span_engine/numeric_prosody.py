from __future__ import annotations

FRACTIONAL_DIGIT_CHUNK_SIZE = 4
INTERNAL_PROSODY_BREAK = "-"
MAX_COMPACT_GROUP_SYLLABLES = 6


def chunk_fractional_digits(fractional_part: str) -> list[str]:
    if not isinstance(fractional_part, str):
        raise TypeError("fractional_part must be str")
    if not fractional_part:
        return []

    chunks = [
        fractional_part[index : index + FRACTIONAL_DIGIT_CHUNK_SIZE]
        for index in range(0, len(fractional_part), FRACTIONAL_DIGIT_CHUNK_SIZE)
    ]
    if len(chunks[-1]) == 1 and len(chunks) >= 2:
        previous_four = chunks.pop(-2)
        lone_one = chunks.pop(-1)
        combined = previous_four + lone_one
        chunks.append(combined[:3])
        chunks.append(combined[3:5])
    return chunks


def read_fractional_with_prosody(fractional_part: str) -> str:
    from engine.span_engine.numeric_reading import read_decimal_fraction_digits

    chunks = chunk_fractional_digits(fractional_part)
    if not chunks:
        return ""
    readings = [read_decimal_fraction_digits(chunk) for chunk in chunks]
    return INTERNAL_PROSODY_BREAK.join(readings)


def join_decimal_prosody(integer_reading: str, fractional_part: str) -> str:
    if not isinstance(integer_reading, str):
        raise TypeError("integer_reading must be str")
    if not isinstance(fractional_part, str):
        raise TypeError("fractional_part must be str")
    fractional = read_fractional_with_prosody(fractional_part)
    return (
        f"{integer_reading}{INTERNAL_PROSODY_BREAK}쩜{INTERNAL_PROSODY_BREAK}{fractional}"
    )


def format_decimal_prosody_suffix(fractional_part: str) -> str:
    if not isinstance(fractional_part, str):
        raise TypeError("fractional_part must be str")
    return join_decimal_prosody("", fractional_part)


def apply_compact_group_prosody(reading: str) -> str:
    if not isinstance(reading, str):
        raise TypeError("reading must be str")
    if not reading:
        return reading

    for unit in ("천", "백", "십"):
        index = reading.find(unit)
        if index == -1:
            continue
        head = reading[: index + 1]
        tail = reading[index + 1 :]
        if not tail:
            continue
        if unit == "천":
            cheon_prefix = head[:-1]
            has_lower = any(marker in tail for marker in ("백", "십"))
            if has_lower and cheon_prefix in (
                "삼",
                "사",
                "오",
                "육",
                "칠",
                "팔",
                "구",
            ):
                return (
                    f"{head}{INTERNAL_PROSODY_BREAK}"
                    f"{apply_compact_group_prosody(tail)}"
                )
            continue
        if unit == "백" and len(reading) > 7 and (
            "십" in tail or len(tail) >= 3
        ):
            return (
                f"{head}{INTERNAL_PROSODY_BREAK}"
                f"{apply_compact_group_prosody(tail)}"
            )
        if unit == "십" and len(reading) > 7 and len(tail) >= 2:
            return f"{head}{INTERNAL_PROSODY_BREAK}{tail}"
    return reading


def apply_spaced_integer_prosody(spaced_reading: str) -> str:
    if not isinstance(spaced_reading, str):
        raise TypeError("spaced_reading must be str")
    if not spaced_reading:
        return spaced_reading
    return " ".join(
        apply_compact_group_prosody(segment)
        for segment in spaced_reading.split(" ")
    )


__all__ = [
    "FRACTIONAL_DIGIT_CHUNK_SIZE",
    "INTERNAL_PROSODY_BREAK",
    "MAX_COMPACT_GROUP_SYLLABLES",
    "apply_compact_group_prosody",
    "apply_spaced_integer_prosody",
    "chunk_fractional_digits",
    "format_decimal_prosody_suffix",
    "join_decimal_prosody",
    "read_fractional_with_prosody",
]
