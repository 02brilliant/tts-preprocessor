from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_fraction_digits
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.sign_aliases import (
    MINUS_SIGN_ALIASES,
    SIGNED_NUMERIC_SIGN_ALIASES,
    is_minus_sign_alias,
    is_signed_numeric_sign,
    strip_signed_numeric_sign,
)
from engine.span_engine.units import starts_with_supported_unit

_ALLOWED_TAILS = (
    "",
    "였고",
    "였지만",
    "였다",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "에게",
    "로",
    "으로",
    "와",
    "과",
    "도",
    "만",
    "부터",
    "까지",
    "처럼",
    "이다",
    "다",
    "입니다",
)

_TAIL_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", "…", "。", "，", "！", "？"})
_CELSIUS_UNITS = frozenset({"℃", "ºC", "°C", "º C", "° C"})
_FAHRENHEIT_UNITS = frozenset({"℉", "ºF", "°F", "º F", "° F"})
_SIGN_CHARS = SIGNED_NUMERIC_SIGN_ALIASES
_MINUS_CHARS = MINUS_SIGN_ALIASES
# Both ASCII degree ° and ordinal indicator º are treated as bare degree.
_BARE_DEGREE_UNITS = frozenset({"°", "º"})
_SIGNED_TEMPERATURE_UNITS = tuple(
    sorted(_CELSIUS_UNITS | _FAHRENHEIT_UNITS, key=len, reverse=True)
)


def parse_signed_numeric(raw_number: str) -> str | None:
    if not isinstance(raw_number, str):
        raise TypeError("raw_number must be str")
    raw_number = raw_number.strip()
    if not raw_number:
        return None
    if "." not in raw_number:
        clean_number = raw_number.replace(",", "")
        if not _is_ascii_digits(clean_number):
            return None
        if len(clean_number) > 1 and clean_number.startswith("0"):
            return None
        value = int(clean_number)
        if value > 9999:
            return None
        return number_to_korean_under_10000(value)
    
    integer_part, fractional_part = raw_number.split(".", 1)
    clean_integer = integer_part.replace(",", "")
    if (
        not clean_integer
        or not fractional_part
        or not _is_ascii_digits(clean_integer)
        or not _is_ascii_digits(fractional_part)
    ):
        return None
    if len(clean_integer) > 1 and clean_integer.startswith("0"):
        return None
    value = int(clean_integer)
    if value > 9999:
        return None
    fractional_reading = _fractional_reading(fractional_part)
    return f"{number_to_korean_under_10000(value)}쩜{fractional_reading}"


def signed_temperature_reading(
    sign: str,
    numeric: str,
    unit: str = "℃",
    *,
    suppress_unit_label: bool = False,
) -> str | None:
    number_reading = _parse_temperature_numeric(numeric)
    if number_reading is None:
        return None
    if sign == "+":
        reading = f"영상 {number_reading}도"
    elif is_minus_sign_alias(sign):
        reading = f"영하 {number_reading}도"
    else:
        return None
    if unit in _FAHRENHEIT_UNITS and not suppress_unit_label:
        return f"화씨 {reading}"
    if unit in _FAHRENHEIT_UNITS:
        return reading
    if unit in _CELSIUS_UNITS:
        return reading
    return None


def _parse_temperature_numeric(raw_number: str) -> str | None:
    raw_number = raw_number.strip()
    reading = parse_signed_numeric(raw_number)
    if reading is None:
        return None
    integer_part, dot, fractional_part = raw_number.replace(",", "").partition(".")
    if not dot or integer_part == "0":
        return reading
    integer_reading = number_to_korean_under_10000(int(integer_part))
    fractional = read_decimal_fraction_digits(fractional_part)
    return f"{integer_reading}쩜{fractional}"


def signed_degree_reading(sign: str, numeric: str, unit: str = "\u00b0") -> str | None:
    """Return reading for a signed bare-degree token.

    ° (DEGREE SIGN, ASCII): keeps the pre-existing
    '플러스 N도' / '마이너스 N도' reading so
    that tests like '+3° -> 플러스 삼도' continue to pass.

    º (MASCULINE ORDINAL INDICATOR, shared with ºC/ºF in this
    codebase): follows the signed-Celsius convention of '영하/영상 N도',
    consistent with '-2.5ºC -> 영하 이쩜오도'.
    """
    number_reading = parse_signed_numeric(numeric)
    if number_reading is None:
        return None
    # º (U+00BA) – ordinal indicator, follows Celsius 영하/영상 convention.
    if unit == "\u00ba":
        if sign == "+":
            return f"영상 {number_reading}도"
        if is_minus_sign_alias(sign):
            return f"영하 {number_reading}도"
        return None
    # ° (U+00B0) – classic degree sign, keeps existing 플러스/마이너스 reading.
    if sign == "+":
        return f"플러스 {number_reading}도"
    if is_minus_sign_alias(sign):
        return f"마이너스 {number_reading}도"
    return None


def scan_signed_temperature_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    candidates = _scan_invalid_signed_temperature_preserve_candidates(
        raw_text, excluded_ranges
    )
    for unit in _SIGNED_TEMPERATURE_UNITS:
        candidates.extend(
            _scan_signed_candidates(
                raw_text, excluded_ranges, unit, "signed_temperature"
            )
        )
    return sorted(candidates, key=lambda x: x.core_span.start)


def scan_signed_degree_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    """Scan for signed bare-degree tokens (both ° and º)."""
    candidates = _scan_invalid_signed_degree_preserve_candidates(
        raw_text, excluded_ranges
    )
    for unit in sorted(_BARE_DEGREE_UNITS, key=len, reverse=True):
        candidates.extend(
            _scan_signed_candidates(raw_text, excluded_ranges, unit, "signed_degree")
        )
    return sorted(candidates, key=lambda x: x.core_span.start)


def scan_signed_number_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    return _scan_signed_candidates(raw_text, excluded_ranges, "", "signed_number")


def parse_signed_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    parsed = _parse_signed_surface(raw)
    if parsed is None:
        return None
    sign, numeric, unit = parsed
    if unit in _CELSIUS_UNITS or unit in _FAHRENHEIT_UNITS:
        return signed_temperature_reading(
            sign,
            numeric,
            unit,
            suppress_unit_label=_has_matching_temperature_label_context(
                raw_text, candidate.core_span.start, unit
            ),
        )
    if unit in _BARE_DEGREE_UNITS:
        return signed_degree_reading(sign, numeric, unit)
    if unit == "":
        number_reading = parse_signed_numeric(numeric)
        if number_reading is None:
            return None
        if sign == "+":
            return f"플러스 {number_reading}"
        if sign in _MINUS_CHARS:
            return f"마이너스 {number_reading}"
    return None


def _scan_signed_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None,
    unit: str,
    owner: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        if _is_blocked_start(raw_text, index, owner):
            index += 1
            continue
        span = _scan_signed_span(raw_text, index, unit)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        tail = raw_text[span.end :]
        if not _tail_is_allowed(tail):
            index += 1
            continue
        reading = parse_signed_candidate(
            raw_text,
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner=owner,
                surface_type="SIGNED_SURFACE",
            ),
        )
        if reading is None:
            index += 1
            continue
        
        if owner == "signed_temperature":
            surface_type = "SIGNED_TEMPERATURE_SURFACE"
        elif owner == "signed_degree":
            surface_type = "SIGNED_DEGREE_SURFACE"
        else:
            surface_type = "SIGNED_NUMBER_SURFACE"

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner=owner,
                surface_type=surface_type,
                reason=f"{owner}_surface",
                metadata={"reading": reading, "tail": _tail_prefix(tail)},
            )
        )
        index = span.end
    return candidates


def _scan_invalid_signed_temperature_preserve_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        span = _scan_numeric_temperature_span(raw_text, index)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        if _is_valid_signed_temperature_surface(raw_text, index, span):
            index = span.end
            continue
        full_span = SourceSpan(span.start, _consume_ascii_tail(raw_text, span.end))
        candidates.append(
            SurfaceCandidate(
                core_span=full_span,
                full_span=full_span,
                owner="preserve",
                surface_type="INVALID_SIGNED_TEMPERATURE_PRESERVE_SURFACE",
                reason="invalid_signed_temperature_dot_fraction_preserve",
            )
        )
        index = full_span.end
    return candidates


def _scan_invalid_signed_degree_preserve_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        span = _scan_numeric_degree_span(raw_text, index)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        if _is_valid_signed_degree_surface(raw_text, index, span):
            index = span.end
            continue
        full_span = SourceSpan(span.start, _consume_ascii_tail(raw_text, span.end))
        candidates.append(
            SurfaceCandidate(
                core_span=full_span,
                full_span=full_span,
                owner="preserve",
                surface_type="INVALID_SIGNED_DEGREE_PRESERVE_SURFACE",
                reason="invalid_signed_degree_preserve",
            )
        )
        index = full_span.end
    return candidates


def _scan_dot_fraction_temperature_span(raw_text: str, start: int) -> SourceSpan | None:
    index = start + 1
    if index >= len(raw_text) or raw_text[index] != ".":
        return None
    fraction_start = index + 1
    fraction_end = _consume_digits(raw_text, fraction_start)
    if fraction_end == fraction_start:
        return None
    for unit in _SIGNED_TEMPERATURE_UNITS:
        if raw_text.startswith(unit, fraction_end):
            return SourceSpan(start, fraction_end + len(unit))
    return None


def _scan_numeric_temperature_span(raw_text: str, start: int) -> SourceSpan | None:
    numeric_end = _consume_signed_numeric_end(raw_text, start)
    if numeric_end is None:
        return _scan_dot_fraction_temperature_span(raw_text, start)
    for unit in _SIGNED_TEMPERATURE_UNITS:
        if raw_text.startswith(unit, numeric_end):
            return SourceSpan(start, numeric_end + len(unit))
    return None


def _scan_numeric_degree_span(raw_text: str, start: int) -> SourceSpan | None:
    numeric_end = _consume_signed_numeric_end(raw_text, start)
    if numeric_end is None:
        return None
    for unit in sorted(_BARE_DEGREE_UNITS, key=len, reverse=True):
        if raw_text.startswith(unit, numeric_end):
            return SourceSpan(start, numeric_end + len(unit))
    return None


def _consume_signed_numeric_end(raw_text: str, start: int) -> int | None:
    index = start + 1
    integer_end = _consume_digits_and_commas(raw_text, index)
    if integer_end == index:
        return None
    index = integer_end
    if index < len(raw_text) and raw_text[index] == ".":
        fraction_start = index + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        index = fraction_end
    return index


def _consume_ascii_tail(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isascii() and raw_text[index].isalnum():
        index += 1
    return index


def _scan_signed_span(raw_text: str, start: int, unit: str) -> SourceSpan | None:
    index = start + 1
    integer_end = _consume_digits_and_commas(raw_text, index)
    if integer_end == index:
        return None
    index = integer_end
    if index < len(raw_text) and raw_text[index] == ".":
        fraction_start = index + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        index = fraction_end
    
    if unit:
        if index < len(raw_text) and raw_text[index] == " ":
            index += 1
        if index >= len(raw_text) or not raw_text.startswith(unit, index):
            return None
        span_end = index + len(unit)
    else:
        span_end = index
        
    span = SourceSpan(start, span_end)
    if not _valid_boundaries(raw_text, span, unit):
        return None
    return span


def _parse_signed_surface(raw: str) -> tuple[str, str, str] | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    if len(raw) < 2 or not is_signed_numeric_sign(raw[0]):
        return None
    sign, unsigned_raw = strip_signed_numeric_sign(raw)
    if sign is None:
        return None
    
    temperature_unit = _signed_temperature_unit_suffix(raw)
    if temperature_unit is not None:
        unit = temperature_unit
        numeric = unsigned_raw[: -len(unit)]
    elif raw[-1] in _BARE_DEGREE_UNITS:
        unit = raw[-1]
        numeric = unsigned_raw[:-1]
    else:
        unit = ""
        numeric = unsigned_raw
        
    if parse_signed_numeric(numeric) is None:
        return None
    return sign, numeric, unit


def _signed_temperature_unit_suffix(raw: str) -> str | None:
    for unit in _SIGNED_TEMPERATURE_UNITS:
        if raw.endswith(unit):
            return unit
    return None


def _has_matching_temperature_label_context(raw_text: str, start: int, unit: str) -> bool:
    label = _matching_temperature_label(unit)
    if label is None:
        return False
    left = raw_text[:start].rstrip(" ")
    if not left.endswith(label):
        return False
    label_start = len(left) - len(label)
    prev_char = left[label_start - 1] if label_start > 0 else None
    if prev_char is None:
        return True
    if "\uac00" <= prev_char <= "\ud7a3":
        return False
    if prev_char.isascii() and prev_char.isalnum():
        return False
    return True


def _matching_temperature_label(unit: str) -> str | None:
    if unit in _FAHRENHEIT_UNITS:
        return "화씨"
    if unit in _CELSIUS_UNITS:
        return "섭씨"
    return None


def _consume_digits_and_commas(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        if _is_ascii_digit(raw_text[index]):
            index += 1
        elif raw_text[index] == ",":
            if index + 3 < len(raw_text) and _is_ascii_digits(raw_text[index+1:index+4]) and (index + 4 == len(raw_text) or not _is_ascii_digit(raw_text[index+4])):
                index += 4
            else:
                break
        else:
            break
    return index


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _fractional_reading(fractional_part: str) -> str:
    return read_decimal_fraction_digits(fractional_part)


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_blocked_start(raw_text: str, start: int, owner: str) -> bool:
    if start == 0:
        return False
    prev_char = raw_text[start - 1]
    if prev_char.isspace():
        return False
    if prev_char in {"(", "[", "{", '"', "'"}:
        return False
    if "\uac00" <= prev_char <= "\ud7a3":
        return owner not in {"signed_temperature", "signed_degree"}
    # If the previous character is alphabetic, do not parse as a plain signed number. (e.g. B-2.5, 코드A-3)
    if prev_char.isascii() and prev_char.isalpha():
        return True
    return (
        (prev_char.isascii() and prev_char.isalnum())
        or ("\u3130" <= prev_char <= "\u318f")
        or (prev_char in SIGNED_NUMERIC_SIGN_ALIASES | {".", "_", "/", "℃", "℉", "°", ","})
    )


def _valid_boundaries(raw_text: str, span: SourceSpan, unit: str) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_non_space = raw_text[span.end :].lstrip()
    if prev_char is not None and not (
        prev_char.isspace() or prev_char in {"(", "[", "{", '"', "'"}
    ):
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            if not unit:
                return False
        elif "\u3130" <= prev_char <= "\u318f":
            return False
        if prev_char in SIGNED_NUMERIC_SIGN_ALIASES | {".", "_", "/", "℃", "℉", "°"}:
            return False
        if prev_char == ",":
            if span.start > 1 and _is_ascii_digit(raw_text[span.start - 2]):
                return False
    if next_char is None:
        return True
    if not unit and next_char.isspace() and starts_with_supported_unit(next_non_space):
        return False
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char == ".":
        next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
        if next_next is not None and _is_ascii_digit(next_next):
            return False
    elif next_char in SIGNED_NUMERIC_SIGN_ALIASES | {"_", "/", "℃", "℉", "°"}:
        return False
    if next_char == ",":
        if span.end + 1 < len(raw_text) and _is_ascii_digit(raw_text[span.end + 1]):
            return False
    
    # Do not parse signed number if it's followed by a colon (e.g. 3:-2, 3:2)
    # But for a signed number owner, maybe we just block next_char == ':'
    if not unit and next_char == ":":
        return False
        
    return True


def _is_valid_signed_temperature_surface(
    raw_text: str, start: int, span: SourceSpan
) -> bool:
    if _parse_signed_surface(raw_text[start : span.end]) is None:
        return False
    if _is_blocked_start(raw_text, start, "signed_temperature"):
        return False
    if not _valid_boundaries(raw_text, span, "temperature"):
        return False
    return _tail_is_allowed(raw_text[span.end :])


def _is_valid_signed_degree_surface(raw_text: str, start: int, span: SourceSpan) -> bool:
    if _parse_signed_surface(raw_text[start : span.end]) is None:
        return False
    if _is_blocked_start(raw_text, start, "signed_degree"):
        return False
    if not _valid_boundaries(raw_text, span, "degree"):
        return False
    return _tail_is_allowed(raw_text[span.end :])


def _tail_is_allowed(tail: str) -> bool:
    if tail == "":
        return True
    if tail[0].isspace():
        return True
    if tail[0] in _TAIL_PUNCTUATION:
        return True
    for allowed in (value for value in _ALLOWED_TAILS if value):
        if tail.startswith(allowed):
            return True
    return False


def _tail_prefix(tail: str) -> str | None:
    for allowed in sorted(_ALLOWED_TAILS, key=len, reverse=True):
        if allowed and tail.startswith(allowed):
            return allowed
    return "" if tail == "" else None


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "parse_signed_candidate",
    "parse_signed_numeric",
    "scan_signed_degree_candidates",
    "scan_signed_number_candidates",
    "scan_signed_temperature_candidates",
    "signed_degree_reading",
    "signed_temperature_reading",
]
