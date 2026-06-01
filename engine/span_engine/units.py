from __future__ import annotations

from engine.span_engine.amount_reading import read_decimal_amount_text
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_fraction_digits
from engine.span_engine.sign_aliases import (
    SIGNED_NUMERIC_SIGN_ALIASES,
    is_minus_sign_alias,
    is_signed_numeric_sign,
    strip_signed_numeric_sign,
)

SIMPLE_UNIT_READINGS: dict[str, str] = {
    "kHz": "킬로헤르츠",
    "MHz": "메가헤르츠",
    "GHz": "기가헤르츠",
    "Ghz": "기가헤르츠",
    "ghz": "기가헤르츠",
    "mL": "밀리리터",
    "ml": "밀리리터",
    "ML": "밀리리터",
    "kWh": "킬로와트시",
    "mm": "밀리미터",
    "cm": "센티미터",
    "km": "킬로미터",
    "mg": "밀리그램",
    "kg": "킬로그램",
    "Hz": "헤르츠",
    "hz": "헤르츠",
    "dB": "데시벨",
    "KB": "킬로바이트",
    "MB": "메가바이트",
    "GB": "기가바이트",
    "PB": "페타바이트",
    "m": "미터",
    "ｍ": "미터",
    "g": "그램",
    "L": "리터",
    "%": "퍼센트",
    "％": "퍼센트",
    "﹪": "퍼센트",
}

SPECIAL_UNIT_READINGS: dict[str, str] = {
    "㎜": "밀리미터",
    "㎝": "센티미터",
    "㎞": "킬로미터",
    "㎎": "밀리그램",
    "㎏": "킬로그램",
    "㎖": "밀리리터",
    "㎠": "제곱센티미터",
    "㎢": "제곱킬로미터",
    "㎡": "제곱미터",
    "m²": "제곱미터",
    "cm²": "제곱센티미터",
    "km²": "제곱킬로미터",
    "㎤": "세제곱센티미터",
    "㎦": "세제곱킬로미터",
    "㎥": "세제곱미터",
    "m³": "세제곱미터",
    "m3": "세제곱미터",
    "cm³": "세제곱센티미터",
    "cm3": "세제곱센티미터",
    "km³": "세제곱킬로미터",
    "km3": "세제곱킬로미터",
    "㎐": "헤르츠",
    "㎒": "메가헤르츠",
    "㎓": "기가헤르츠",
    "㏈": "데시벨",
    "℃": "도",
    "℉": "화씨",
    "º": "도",
    "ºC": "도",
    "ºF": "화씨",
    "°C": "도",
    "°F": "화씨",
    "º C": "도",
    "º F": "화씨",
    "° C": "도",
    "° F": "화씨",
    "°": "도",
}

# N-M range compatibility is opt-in. The current unit registry is a simple
# reading dictionary, so this registry-backed metadata table preserves existing
# approved unit behavior while missing entries default to non-compatible.
RANGE_COMPATIBLE_UNIT_READINGS: dict[str, str] = {
    **SIMPLE_UNIT_READINGS,
    **SPECIAL_UNIT_READINGS,
}

_SIMPLE_UNITS_BY_LENGTH = sorted(SIMPLE_UNIT_READINGS, key=len, reverse=True)
_SPECIAL_UNITS_BY_LENGTH = sorted(SPECIAL_UNIT_READINGS, key=len, reverse=True)
_RANGE_COMPATIBLE_UNITS_BY_LENGTH = sorted(
    RANGE_COMPATIBLE_UNIT_READINGS, key=len, reverse=True
)
_PREV_BLOCKERS = frozenset(".,~:/") | SIGNED_NUMERIC_SIGN_ALIASES
_PREV_SYMBOL_BLOCKERS = frozenset("$€£¥₩")
_NEXT_BLOCKERS = frozenset(",~:/") | SIGNED_NUMERIC_SIGN_ALIASES
_SUPERSCRIPT_EXPONENTS = frozenset("²³")
_UNSAFE_TAIL_UNITS_BY_LENGTH = sorted(
    {
        *SIMPLE_UNIT_READINGS,
        *SPECIAL_UNIT_READINGS,
        "ºC",
        "ºF",
        "°C",
        "°F",
    },
    key=len,
    reverse=True,
)
_COMPOUND_SLASH_UNIT_SURFACES_BASE = frozenset(
    {
        "km/h",
        "㎞/h",
        "km/hr",
        "km/s",
        "㎞/s",
        "m/min",
        "m/sec",
        "m/s",
        "km/L",
        "km/l",
        "km/ℓ",
        "㎞/L",
        "㎞/l",
        "㎞/ℓ",
        "m/L",
        "m/l",
        "mg/L",
        "g/L",
        "KB/s",
        "Kb/s",
        "kb/s",
        "MB/s",
        "Mb/s",
        "mb/s",
        "GB/s",
        "Gb/s",
        "gb/s",
        "TB/s",
        "Tb/s",
        "tb/s",
        "PB/s",
        "Pb/s",
        "pb/s",
        "mg/dL",
    }
)
_COMPOUND_SLASH_UNIT_SURFACES = frozenset(
    _COMPOUND_SLASH_UNIT_SURFACES_BASE
    | {
        unit.replace("/", "／")
        for unit in _COMPOUND_SLASH_UNIT_SURFACES_BASE
        if "/" in unit
    }
)
_COMPOUND_SLASH_NUMERATOR_PREFIXES = frozenset(
    {
        "km",
        "㎞",
        "m",
        "mg",
        "g",
        "KB",
        "Kb",
        "kb",
        "MB",
        "Mb",
        "mb",
        "GB",
        "Gb",
        "gb",
        "TB",
        "Tb",
        "tb",
        "PB",
        "Pb",
        "pb",
    }
)
_DATA_RATE_NUMERATOR_PREFIXES = frozenset(
    {"KB", "Kb", "kb", "MB", "Mb", "mb", "GB", "Gb", "gb", "TB", "Tb", "tb", "PB", "Pb", "pb"}
)
_COMPOUND_EXACT_UNIT_SURFACES = frozenset(
    {"Mbps", "Gbps", "rpm", "fps", "ppm", "ppb", "dBi"}
)
_DECIMAL_AMOUNT_UNIT_SURFACES = frozenset(
    {
        "MB",
        "GB",
        "PB",
        "kWh",
        "mm",
        "cm",
        "km",
        "mg",
        "kg",
        "mL",
        "ml",
        "ML",
        "dB",
        "m",
        "ｍ",
        "g",
        "L",
        "Hz",
        "hz",
        "MHz",
        "GHz",
        "Ghz",
        "ghz",
        "℃",
        "℉",
        "º",
        "ºC",
        "ºF",
        "°",
        "°C",
        "°F",
        "㎡",
        "m²",
        "cm²",
        "km²",
        "㎠",
        "㎢",
        "㎥",
        "m³",
        "m3",
        "cm³",
        "cm3",
        "km³",
        "km3",
        "㎤",
        "㎦",
        "㎐",
        "㎒",
        "㎓",
        "%",
        "％",
        "﹪",
    }
)
_SPACED_AMOUNT_UNIT_SURFACES = frozenset({"Hz", "hz"})


def scan_simple_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    return _scan_unit_candidates(raw_text, SIMPLE_UNIT_READINGS, _SIMPLE_UNITS_BY_LENGTH, "simple_unit", "SIMPLE_UNIT_SURFACE")


def scan_special_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    return _scan_unit_candidates(raw_text, SPECIAL_UNIT_READINGS, _SPECIAL_UNITS_BY_LENGTH, "special_unit", "SPECIAL_UNIT_SURFACE")


def scan_unit_contamination_preserve_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (_is_ascii_digit(raw_text[index]) or is_signed_numeric_sign(raw_text[index])):
            index += 1
            continue
        if _has_blocking_previous_context(raw_text, index):
            index += 1
            continue
        repeated_sign_candidate = _repeated_sign_unit_preserve_candidate(raw_text, index)
        if repeated_sign_candidate is not None:
            candidates.append(repeated_sign_candidate)
            index = repeated_sign_candidate.full_span.end
            continue
        suffix_spacing_candidate = _unit_suffix_spacing_preserve_candidate(
            raw_text, index
        )
        if suffix_spacing_candidate is not None:
            candidates.append(suffix_spacing_candidate)
            index = suffix_spacing_candidate.full_span.end
            continue
        numeric_start = index + 1 if is_signed_numeric_sign(raw_text[index]) else index
        numeric_end = _consume_decimal_number(raw_text, index)
        if is_signed_numeric_sign(raw_text[index]):
            numeric_end = _consume_decimal_number(raw_text, numeric_start)
        if numeric_end is None:
            index += 1
            continue
        candidate = _unit_tail_preserve_candidate(raw_text, index, numeric_end)
        if candidate is None:
            candidate = _compound_slash_tail_preserve_candidate(
                raw_text, index, numeric_end
            )
        if candidate is None:
            index += 1
            continue
        candidates.append(candidate)
        index = candidate.full_span.end
    return candidates


def parse_unit_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner not in {"simple_unit", "special_unit"}:
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    parsed = _parse_surface(raw)
    return parsed[2] if parsed is not None else None


def starts_with_supported_unit(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return any(text.startswith(unit) for unit in _SIMPLE_UNITS_BY_LENGTH + _SPECIAL_UNITS_BY_LENGTH)


def supported_unit_prefix_length(text: str) -> int | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    for unit in _SIMPLE_UNITS_BY_LENGTH + _SPECIAL_UNITS_BY_LENGTH:
        if text.startswith(unit):
            return len(unit)
    return None


def range_compatible_unit_reading(unit: str) -> str | None:
    if not isinstance(unit, str):
        raise TypeError("unit must be str")
    return RANGE_COMPATIBLE_UNIT_READINGS.get(unit)


def range_compatible_units_by_length() -> list[str]:
    return list(_RANGE_COMPATIBLE_UNITS_BY_LENGTH)


def _scan_unit_candidates(
    raw_text: str,
    inventory: dict[str, str],
    ordered_units: list[str],
    owner: str,
    surface_type: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (_is_ascii_digit(raw_text[index]) or is_signed_numeric_sign(raw_text[index])):
            index += 1
            continue
        amount_start = index
        numeric_start = amount_start + 1 if is_signed_numeric_sign(raw_text[amount_start]) else amount_start
        amount_end = _consume_decimal_number(raw_text, numeric_start)
        if amount_end is None:
            index += 1
            continue
        amount = raw_text[amount_start:amount_end]
        unit_start = _consume_optional_ascii_space(raw_text, amount_end)
        has_decimal_amount = "." in amount
        has_space_before_unit = unit_start != amount_end
        for unit in ordered_units:
            unit_name = inventory[unit]
            if not raw_text.startswith(unit, unit_start):
                continue
            if has_decimal_amount and unit not in _DECIMAL_AMOUNT_UNIT_SURFACES:
                continue
            span = SourceSpan(amount_start, unit_start + len(unit))
            if not _valid_amount_and_boundary(raw_text, span, amount):
                continue
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner=owner,
                    surface_type=surface_type,
                    reason=f"{owner}_numeric_prefix",
                    metadata={
                        "amount": amount,
                        "unit": unit,
                        "unit_reading": unit_name,
                        "reading": _reading(amount, unit_name),
                    },
                )
            )
            break
        index = max(amount_end, index + 1)
    return candidates


def _parse_surface(raw: str) -> tuple[str, str, str] | None:
    for inventory, ordered_units in (
        (SIMPLE_UNIT_READINGS, _SIMPLE_UNITS_BY_LENGTH),
        (SPECIAL_UNIT_READINGS, _SPECIAL_UNITS_BY_LENGTH),
    ):
        for unit in ordered_units:
            if raw.endswith(unit):
                amount = raw[: -len(unit)].strip()
                unsigned_amount = _unsigned_amount(amount)
                if unsigned_amount is not None and _is_valid_number(unsigned_amount):
                    unit_name = inventory[unit]
                    return amount, unit_name, _reading(amount, unit_name)
                if unsigned_amount is not None and _is_supported_decimal_amount(unsigned_amount):
                    unit_name = inventory[unit]
                    return amount, unit_name, _reading(amount, unit_name)
    return None


def _reading(amount: str, unit_name: str) -> str:
    amount_reading = _amount_reading(amount)
    if unit_name == "화씨":
        return f"화씨 {amount_reading}도"
    separator = "" if unit_name == "도" else " "
    return f"{amount_reading}{separator}{unit_name}"


def _amount_reading(amount: str) -> str:
    sign = _amount_sign(amount)
    unsigned = _unsigned_amount(amount)
    if unsigned is None:
        raise ValueError("invalid signed unit amount")
    if sign == "+":
        return "플러스 " + _plus_decimal_amount_reading(unsigned)
    if sign is not None and is_minus_sign_alias(sign):
        return "마이너스 " + _plus_decimal_amount_reading(unsigned)
    return _plus_decimal_amount_reading(unsigned)


def _plus_decimal_amount_reading(amount: str) -> str:
    integer_part, dot, fractional_part = amount.partition(".")
    integer_reading = read_decimal_amount_text(
        integer_part,
        overflow_message="unit amount must be below 100000000",
    )
    if not dot:
        return integer_reading
    fractional = read_decimal_fraction_digits(fractional_part)
    return f"{integer_reading}쩜{fractional}"


def _amount_sign(amount: str) -> str | None:
    sign, _ = strip_signed_numeric_sign(amount)
    return sign


def _unsigned_amount(amount: str) -> str | None:
    sign, unsigned = strip_signed_numeric_sign(amount)
    if sign is not None:
        return unsigned if unsigned else None
    return amount


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_supported_decimal_amount(text: str) -> bool:
    integer_part, dot, fractional_part = text.partition(".")
    if not dot:
        return _is_valid_number(integer_part)
    return _is_valid_number(integer_part) and _is_ascii_digits(fractional_part)


def _consume_decimal_number(raw_text: str, start: int) -> int | None:
    integer_end = _consume_integer(raw_text, start)
    if integer_end is None:
        return None
    if integer_end < len(raw_text) and raw_text[integer_end] == ".":
        fraction_start = integer_end + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return integer_end
        return fraction_end
    return integer_end


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
    if index < len(raw_text) and raw_text[index] == ",":
        return None
    return index


def _is_valid_number(text: str) -> bool:
    if not text:
        return False
    if "," not in text:
        return _is_ascii_digits(text)
    groups = text.split(",")
    if not (1 <= len(groups[0]) <= 3 and _is_ascii_digits(groups[0])):
        return False
    return all(len(group) == 3 and _is_ascii_digits(group) for group in groups[1:])


def _has_blocking_previous_context(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return False
    if prev_char.isascii() and prev_char.isalnum():
        return True
    if "\uac00" <= prev_char <= "\ud7a3":
        return True
    return prev_char in _PREV_BLOCKERS or prev_char in _PREV_SYMBOL_BLOCKERS


def _unit_tail_preserve_candidate(
    raw_text: str, start: int, numeric_end: int
) -> SurfaceCandidate | None:
    unit_start = _consume_optional_ascii_space(raw_text, numeric_end)
    for exact_unit in _COMPOUND_EXACT_UNIT_SURFACES:
        if not raw_text.startswith(exact_unit, unit_start):
            continue
        exact_end = unit_start + len(exact_unit)
        if _consume_unsafe_ascii_tail(raw_text, exact_end) == exact_end:
            return None
    for unit in _UNSAFE_TAIL_UNITS_BY_LENGTH:
        if not raw_text.startswith(unit, unit_start):
            continue
        unit_end = unit_start + len(unit)
        data_rate_slash_space_end = _consume_data_rate_slash_space_tail(
            raw_text, unit, unit_end
        )
        if data_rate_slash_space_end is not None:
            return _preserve_candidate(
                start,
                data_rate_slash_space_end,
                "data_rate_slash_space_non_goal_preserve",
            )
        tail_end = _consume_unsafe_ascii_tail(raw_text, unit_end)
        if tail_end == unit_end:
            return None
        return _preserve_candidate(
            start,
            tail_end,
            "unit_like_ascii_tail_contamination",
        )
    return None


def _unit_suffix_spacing_preserve_candidate(
    raw_text: str, start: int
) -> SurfaceCandidate | None:
    amount_end = _consume_numeric_like_surface(raw_text, start)
    if amount_end is None:
        return None
    space_end = amount_end
    while space_end < len(raw_text) and raw_text[space_end].isspace():
        space_end += 1
    spacing = raw_text[amount_end:space_end]
    unit = _supported_unit_at(raw_text, space_end)
    if unit is None:
        return None
    amount = raw_text[start:amount_end]
    if _is_valid_signed_decimal_amount(amount) and spacing in {"", " "}:
        return None
    return _preserve_candidate(
        start,
        space_end + len(unit),
        "unit_percent_suffix_invalid_or_disallowed_spacing_preserve",
    )


def _repeated_sign_unit_preserve_candidate(
    raw_text: str, start: int
) -> SurfaceCandidate | None:
    if not is_signed_numeric_sign(raw_text[start]):
        return None
    index = start + 1
    if index >= len(raw_text) or not is_signed_numeric_sign(raw_text[index]):
        return None
    while index < len(raw_text) and is_signed_numeric_sign(raw_text[index]):
        index += 1
    numeric_end = _consume_decimal_number(raw_text, index)
    if numeric_end is None:
        return None
    unit_start = _consume_optional_ascii_space(raw_text, numeric_end)
    unit = _supported_unit_at(raw_text, unit_start)
    if unit is None:
        return None
    return _preserve_candidate(
        start,
        unit_start + len(unit),
        "unit_percent_repeated_sign_preserve",
    )


def _consume_numeric_like_surface(raw_text: str, start: int) -> int | None:
    index = start
    if index < len(raw_text) and is_signed_numeric_sign(raw_text[index]):
        index += 1
    numeric_start = index
    while index < len(raw_text) and (
        _is_ascii_digit(raw_text[index]) or raw_text[index] in {",", "."}
    ):
        index += 1
    if index == numeric_start:
        return None
    return index


def _supported_unit_at(raw_text: str, start: int) -> str | None:
    for unit in _SIMPLE_UNITS_BY_LENGTH + _SPECIAL_UNITS_BY_LENGTH:
        if raw_text.startswith(unit, start):
            return unit
    return None


def _is_valid_signed_decimal_amount(amount: str) -> bool:
    unsigned = _unsigned_amount(amount)
    if unsigned is None:
        return False
    integer_part, dot, fractional_part = unsigned.partition(".")
    if not _is_valid_integer_amount(integer_part):
        return False
    if not dot:
        return True
    return _is_ascii_digits(fractional_part)


def _is_valid_integer_amount(integer_part: str) -> bool:
    if not _is_valid_number(integer_part):
        return False
    digits = integer_part.replace(",", "")
    return len(digits) == 1 or not digits.startswith("0")


def _consume_data_rate_slash_space_tail(
    raw_text: str, unit: str, unit_end: int
) -> int | None:
    if unit not in _DATA_RATE_NUMERATOR_PREFIXES:
        return None
    if not raw_text.startswith(" / ", unit_end):
        return None
    tail_start = unit_end + 3
    if not raw_text.startswith("s", tail_start):
        return None
    tail_end = tail_start + 1
    if _consume_unsafe_ascii_tail(raw_text, tail_end) != tail_end:
        return None
    return tail_end


def _compound_slash_tail_preserve_candidate(
    raw_text: str, start: int, numeric_end: int
) -> SurfaceCandidate | None:
    segment_start = _consume_optional_ascii_space(raw_text, numeric_end)
    segment_end = segment_start
    while segment_end < len(raw_text) and (
        raw_text[segment_end].isascii()
        and raw_text[segment_end].isalpha()
        or raw_text[segment_end] in {"㎞", "ℓ", "/", "／"}
    ):
        segment_end += 1
    if segment_end == segment_start or not any(
        slash in raw_text[segment_start:segment_end] for slash in {"/", "／"}
    ):
        return None
    segment = raw_text[segment_start:segment_end]
    normalized_segment = segment.replace("／", "/")
    numerator = normalized_segment.split("/", 1)[0]
    if numerator not in _COMPOUND_SLASH_NUMERATOR_PREFIXES:
        return None
    if segment in _COMPOUND_SLASH_UNIT_SURFACES:
        return None
    return _preserve_candidate(
        start,
        segment_end,
        "compound_unit_like_ascii_tail_contamination",
    )


def _consume_unsafe_ascii_tail(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if not (char.isascii() and char.isalnum()):
            break
        index += 1
    return index


def _preserve_candidate(start: int, end: int, reason: str) -> SurfaceCandidate:
    span = SourceSpan(start, end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="UNIT_CONTAMINATION_PRESERVE_SURFACE",
        reason=reason,
    )


def _valid_amount_and_boundary(raw_text: str, span: SourceSpan, amount: str) -> bool:
    unsigned_amount = _unsigned_amount(amount)
    if unsigned_amount is None:
        return False
    integer_part = unsigned_amount.split(".", 1)[0].replace(",", "")
    if len(integer_part) > 1 and integer_part.startswith("0"):
        return False
    if int(integer_part) > 9999:
        if "," not in unsigned_amount:
            return False
        if int(integer_part) >= 100000000:
            return False
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
    next_non_space = raw_text[span.end :].lstrip()
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
        if prev_char in _PREV_SYMBOL_BLOCKERS:
            return False
    if next_char is None:
        return True
    if next_char in _SUPERSCRIPT_EXPONENTS:
        return False
    if next_char.isspace() and next_non_space.startswith("/"):
        return False
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in _NEXT_BLOCKERS and next_char != ",":
        return False
    if next_char == ".":
        return not (next_next is not None and next_next.isdigit())
    return True


__all__ = [
    "RANGE_COMPATIBLE_UNIT_READINGS",
    "SIMPLE_UNIT_READINGS",
    "SPECIAL_UNIT_READINGS",
    "parse_unit_candidate",
    "range_compatible_unit_reading",
    "range_compatible_units_by_length",
    "scan_simple_unit_candidates",
    "scan_special_unit_candidates",
    "scan_unit_contamination_preserve_candidates",
    "supported_unit_prefix_length",
    "starts_with_supported_unit",
]
