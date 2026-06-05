from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.amount_reading import (
    SINO_DIGIT_READINGS,
    read_integer_under_100_million,
)
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.number import number_to_korean_under_10000

COMPOUND_SLASH_UNIT_READINGS: dict[str, str] = {
    "km/h": "시속 {number} 킬로미터",
    "㎞/h": "시속 {number} 킬로미터",
    "km/hr": "시속 {number} 킬로미터",
    "km/s": "초속 {number} 킬로미터",
    "㎞/s": "초속 {number} 킬로미터",
    "m/min": "분속 {number} 미터",
    "m/sec": "초속 {number} 미터",
    "m/s": "초속 {number} 미터",
    "cm/s": "초속 {number} 센티미터",
    "㎝/s": "초속 {number} 센티미터",
    "km/L": "리터당 {number} 킬로미터",
    "km/l": "리터당 {number} 킬로미터",
    "km/ℓ": "리터당 {number} 킬로미터",
    "㎞/L": "리터당 {number} 킬로미터",
    "㎞/l": "리터당 {number} 킬로미터",
    "㎞/ℓ": "리터당 {number} 킬로미터",
    "m/L": "리터당 {number} 미터",
    "m/l": "리터당 {number} 미터",
    "mg/L": "리터당 {number} 밀리그램",
    "㎎/L": "리터당 {number} 밀리그램",
    "g/L": "리터당 {number} 그램",
    "KB/s": "초당 {number} 킬로바이트",
    "Kb/s": "초당 {number} 킬로바이트",
    "kb/s": "초당 {number} 킬로바이트",
    "MB/s": "초당 {number} 메가바이트",
    "Mb/s": "초당 {number} 메가바이트",
    "mb/s": "초당 {number} 메가바이트",
    "GB/s": "초당 {number} 기가바이트",
    "Gb/s": "초당 {number} 기가바이트",
    "gb/s": "초당 {number} 기가바이트",
    "TB/s": "초당 {number} 테라바이트",
    "Tb/s": "초당 {number} 테라바이트",
    "tb/s": "초당 {number} 테라바이트",
    "PB/s": "초당 {number} 페타바이트",
    "Pb/s": "초당 {number} 페타바이트",
    "pb/s": "초당 {number} 페타바이트",
    "mg/dL": "데시리터당 {number} 밀리그램",
}

for _unit, _reading in list(COMPOUND_SLASH_UNIT_READINGS.items()):
    if "/" in _unit:
        COMPOUND_SLASH_UNIT_READINGS.setdefault(_unit.replace("/", "／"), _reading)
COMPOUND_EXACT_UNIT_READINGS: dict[str, str] = {
    "Mbps": "{number} 메가비피에스",
    "Gbps": "{number} 기가비피에스",
    "rpm": "{number} 알피엠",
    "fps": "{number} 에프피에스",
    "ppm": "{number} 피피엠",
    "ppb": "{number} 피피비",
    "dBi": "{number} 디비아이",
}

_ORDERED_COMPOUND_UNITS = sorted(
    COMPOUND_SLASH_UNIT_READINGS, key=len, reverse=True
)
_ORDERED_COMPOUND_EXACT_UNITS = sorted(
    COMPOUND_EXACT_UNIT_READINGS, key=len, reverse=True
)
_DECIMAL_ENABLED_UNITS = frozenset(COMPOUND_SLASH_UNIT_READINGS)
_COMMA_ENABLED_UNITS = frozenset(COMPOUND_SLASH_UNIT_READINGS)
_TAIL_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":"})
_BLOCKING_PREV_CHARS = frozenset("+-.,~:/_")


def compound_slash_unit_reading(unit: str, numeric: str) -> str | None:
    if not isinstance(unit, str):
        raise TypeError("unit must be str")
    if not isinstance(numeric, str):
        raise TypeError("numeric must be str")
    template = COMPOUND_SLASH_UNIT_READINGS.get(unit)
    if template is None:
        return None
    number_reading = read_decimal_for_compound_unit_only(numeric, unit)
    if number_reading is None:
        return None
    return template.format(number=number_reading)


def read_decimal_for_compound_unit_only(numeric: str, unit: str) -> str | None:
    if not isinstance(numeric, str):
        raise TypeError("numeric must be str")
    if not isinstance(unit, str):
        raise TypeError("unit must be str")
    normalized = numeric.replace(",", "")
    if "." not in numeric:
        if "," in numeric and unit not in _COMMA_ENABLED_UNITS:
            return None
        if not _is_valid_integer(numeric):
            return None
        if len(normalized) > 1 and normalized.startswith("0"):
            return None
        value = int(normalized)
        if value >= 100000000:
            return None
        return read_integer_under_100_million(
            value,
            overflow_message="compound unit amount must be below 100000000",
        )
    if unit not in _DECIMAL_ENABLED_UNITS:
        return None
    integer_part, fractional_part = numeric.split(".", 1)
    normalized_integer = integer_part.replace(",", "")
    if "," in integer_part and unit not in _COMMA_ENABLED_UNITS:
        return None
    if (
        not integer_part
        or not fractional_part
        or not _is_valid_integer(integer_part)
        or not _is_ascii_digits(fractional_part)
    ):
        return None
    if len(normalized_integer) > 1 and normalized_integer.startswith("0"):
        return None
    value = int(normalized_integer)
    if value >= 100000000:
        return None
    fractional = "".join(SINO_DIGIT_READINGS[digit] for digit in fractional_part)
    integer_reading = read_integer_under_100_million(
        value,
        overflow_message="compound unit amount must be below 100000000",
    )
    return f"{integer_reading}쩜{fractional}"


def compound_exact_unit_reading(unit: str, numeric: str) -> str | None:
    if not isinstance(unit, str):
        raise TypeError("unit must be str")
    if not isinstance(numeric, str):
        raise TypeError("numeric must be str")
    template = COMPOUND_EXACT_UNIT_READINGS.get(unit)
    if template is None:
        return None
    if not _is_ascii_digits(numeric):
        return None
    if len(numeric) > 1 and numeric.startswith("0"):
        return None
    value = int(numeric)
    if value > 9999:
        return None
    return template.format(number=number_to_korean_under_10000(value))


def scan_compound_slash_unit_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        if is_url_or_path_context(raw_text, index):
            index += 1
            continue
        for candidate in _match_compound_candidate(raw_text, index, excluded_ranges):
            candidates.append(candidate)
            index = candidate.full_span.end
            break
        else:
            index += 1
    return candidates


def scan_compound_exact_unit_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        if is_url_or_path_context(raw_text, index):
            index += 1
            continue
        for candidate in _match_compound_exact_candidate(
            raw_text, index, excluded_ranges
        ):
            candidates.append(candidate)
            index = candidate.full_span.end
            break
        else:
            index += 1
    return candidates


def parse_compound_slash_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "compound_slash_unit":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    numeric = candidate.metadata.get("numeric")
    unit = candidate.metadata.get("unit")
    if not isinstance(numeric, str) or not isinstance(unit, str):
        return None
    return compound_slash_unit_reading(unit, numeric)


def parse_compound_exact_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "compound_exact_unit":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    numeric = candidate.metadata.get("numeric")
    unit = candidate.metadata.get("unit")
    if not isinstance(numeric, str) or not isinstance(unit, str):
        return None
    return compound_exact_unit_reading(unit, numeric)


def starts_with_supported_compound_exact_unit(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return any(text.startswith(unit) for unit in _ORDERED_COMPOUND_EXACT_UNITS)


def is_url_or_path_context(raw_text: str, start: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(start, int):
        raise TypeError("start must be int")
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char == "/":
        return True
    prefix = raw_text[:start]
    return prefix.endswith("http://") or prefix.endswith("https://")


def is_unsafe_compound_slash_tail(tail: str) -> bool:
    if not isinstance(tail, str):
        raise TypeError("tail must be str")
    if tail == "":
        return False
    first = tail[0]
    if first.isascii() and first.isalnum():
        return True
    if first in {"/", "／", "_"}:
        return True
    if first == ".":
        return True
    if first in _TAIL_PUNCTUATION:
        return False
    return False


def _match_compound_candidate(
    raw_text: str, start: int, excluded_ranges: list[BracketRange]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for unit in _ORDERED_COMPOUND_UNITS:
        span = _scan_compound_span(raw_text, start, unit)
        if span is None:
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        numeric = raw_text[start : span.end - len(unit)].strip()
        reading = compound_slash_unit_reading(unit, numeric)
        if reading is None:
            continue
        tail = raw_text[span.end :]
        if is_unsafe_compound_slash_tail(tail):
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="compound_slash_unit",
                surface_type="COMPOUND_SLASH_UNIT_SURFACE",
                reason="compound_slash_unit_inventory_match",
                metadata={"reading": reading, "numeric": numeric, "unit": unit},
            )
        )
        break
    return candidates


def _match_compound_exact_candidate(
    raw_text: str, start: int, excluded_ranges: list[BracketRange]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for unit in _ORDERED_COMPOUND_EXACT_UNITS:
        span = _scan_compound_span(raw_text, start, unit)
        if span is None:
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        numeric = raw_text[start : span.end - len(unit)]
        reading = compound_exact_unit_reading(unit, numeric)
        if reading is None:
            continue
        tail = raw_text[span.end :]
        if is_unsafe_compound_slash_tail(tail):
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="compound_exact_unit",
                surface_type="COMPOUND_EXACT_UNIT_SURFACE",
                reason="compound_exact_unit_inventory_match",
                metadata={"reading": reading, "numeric": numeric, "unit": unit},
            )
        )
        break
    return candidates


def _scan_compound_span(raw_text: str, start: int, unit: str) -> SourceSpan | None:
    numeric_end = _consume_numeric(raw_text, start, unit)
    if numeric_end is None:
        return None
    if numeric_end < len(raw_text) and raw_text[numeric_end] == " ":
        numeric_end += 1
    if not raw_text.startswith(unit, numeric_end):
        return None
    span = SourceSpan(start, numeric_end + len(unit))
    if not _valid_boundaries(raw_text, span):
        return None
    return span


def _consume_numeric(raw_text: str, start: int, unit: str) -> int | None:
    index = start
    integer_end = _consume_integer(raw_text, index)
    if integer_end is None:
        return None
    integer = raw_text[index:integer_end]
    normalized_integer = integer.replace(",", "")
    if "," in integer and unit not in _COMMA_ENABLED_UNITS:
        return None
    if len(normalized_integer) > 1 and normalized_integer.startswith("0"):
        return None
    if int(normalized_integer) >= 100000000:
        return None
    index = integer_end
    if index < len(raw_text) and raw_text[index] == ".":
        if unit not in _DECIMAL_ENABLED_UNITS:
            return None
        fraction_start = index + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        index = fraction_end
    return index


def _consume_integer(raw_text: str, start: int) -> int | None:
    digit_end = _consume_digits(raw_text, start)
    if digit_end == start:
        return None
    if digit_end >= len(raw_text) or raw_text[digit_end] != ",":
        return digit_end
    if digit_end - start > 3:
        return None
    index = digit_end
    while index < len(raw_text) and raw_text[index] == ",":
        group_start = index + 1
        group_end = _consume_digits(raw_text, group_start)
        if group_end - group_start != 3:
            return None
        index = group_end
    return index


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_valid_integer(text: str) -> bool:
    if not text:
        return False
    if "," not in text:
        return _is_ascii_digits(text)
    groups = text.split(",")
    if not (1 <= len(groups[0]) <= 3 and _is_ascii_digits(groups[0])):
        return False
    return all(len(group) == 3 and _is_ascii_digits(group) for group in groups[1:])


def _valid_boundaries(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _BLOCKING_PREV_CHARS:
            return False
    return True


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "COMPOUND_EXACT_UNIT_READINGS",
    "COMPOUND_SLASH_UNIT_READINGS",
    "compound_exact_unit_reading",
    "compound_slash_unit_reading",
    "is_unsafe_compound_slash_tail",
    "is_url_or_path_context",
    "parse_compound_exact_unit_candidate",
    "parse_compound_slash_unit_candidate",
    "read_decimal_for_compound_unit_only",
    "scan_compound_exact_unit_candidates",
    "scan_compound_slash_unit_candidates",
    "starts_with_supported_compound_exact_unit",
]
