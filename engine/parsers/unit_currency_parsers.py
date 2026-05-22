from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from engine.dictionary.base_dictionary import BASIC_UNITS, FILESIZE_UNITS
from engine.parsers.numeric_date_parsers import STRICT_COMMA_NUMBER_PATTERN, read_decimal_ko, read_integer_ko


_AMBIGUOUS_SINGLE_LETTER_UNITS = {"A", "V"}
_RISKY_SYMBOLIC_UNITS = {"t", "V", "A", "s", "h", "d"}
_NUMBER_PATTERN = r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?"
_UNIT_PARTICLE_PATTERN = r"(?:입니다|합니까|하고|하며|하면서|으로|에서|에게|한테|이랑|까지|부터|이란|에는|당|은|는|이|가|을|를|와|과|의|에|로|만|도|란|뿐|고|다)?"
_PLAIN_INTEGER_RE = re.compile(r"\d+")
_PLAIN_DECIMAL_RE = re.compile(r"\d+\.\d+")
_DECIMAL_FRACTIONAL_RE = re.compile(r"\d+\.(\d+)")
_NATIVE_DURATION_HOUR_KO = {
    1: "한",
    2: "두",
    3: "세",
    4: "네",
    5: "다섯",
    6: "여섯",
    7: "일곱",
    8: "여덟",
    9: "아홉",
    10: "열",
    11: "열한",
    12: "열두",
    13: "열세",
    14: "열네",
    15: "열다섯",
    16: "열여섯",
    17: "열일곱",
    18: "열여덟",
    19: "열아홉",
    20: "스무",
    21: "스물한",
    22: "스물두",
    23: "스물세",
    24: "스물네",
}


def _has_supported_fractional_length(text: str) -> bool:
    match = _DECIMAL_FRACTIONAL_RE.fullmatch(text)
    if not match:
        return True
    return 1 <= len(match.group(1)) <= 6


def _normalize_number(text: str) -> str | None:
    if text.startswith("-"):
        body = _normalize_number(text[1:])
        if body is None:
            return None
        return f"-{body}"

    if "," in text:
        if not STRICT_COMMA_NUMBER_PATTERN.fullmatch(text):
            return None
        text = text.replace(",", "")

    if _PLAIN_INTEGER_RE.fullmatch(text):
        return text
    if _PLAIN_DECIMAL_RE.fullmatch(text):
        return text
    return None


def _read_number(text: str) -> str | None:
    normalized = _normalize_number(text)
    if normalized is None:
        return None

    if normalized.startswith("-"):
        body = normalized[1:]
        if "." in body:
            return f"마이너스 {read_decimal_ko(body)}"
        return f"마이너스 {read_integer_ko(body)}"

    if "." in normalized:
        return read_decimal_ko(normalized)
    return read_integer_ko(normalized)


def _read_positive_number(text: str) -> str | None:
    normalized = _normalize_number(text)
    if normalized is None or normalized.startswith("-"):
        return None
    if "." in normalized:
        return read_decimal_ko(normalized)
    return read_integer_ko(normalized)


def _read_duration_number(unit_text: str, number_text: str) -> str | None:
    normalized = _normalize_number(number_text)
    if normalized is None or normalized.startswith("-"):
        return None

    if "." in normalized:
        return read_decimal_ko(normalized)

    value = int(normalized)
    if unit_text == "시간" and value in _NATIVE_DURATION_HOUR_KO:
        return _NATIVE_DURATION_HOUR_KO[value]
    return read_integer_ko(normalized)


def _read_number_for_decimal_unit(text: str) -> str | None:
    normalized = _normalize_number(text)
    if normalized is None:
        return None

    unsigned = normalized[1:] if normalized.startswith("-") else normalized
    if "." not in unsigned or not _has_supported_fractional_length(unsigned):
        return None

    return _read_number(normalized)


def _read_positive_number_for_decimal_unit(text: str) -> str | None:
    normalized = _normalize_number(text)
    if normalized is None or normalized.startswith("-"):
        return None
    if "." in normalized and not _has_supported_fractional_length(normalized):
        return None
    return _read_positive_number(normalized)


def try_parse_percent(text: str) -> str | None:
    match = re.fullmatch(r"(.+)%", text)
    if not match:
        return None

    number_reading = _read_positive_number(match.group(1))
    if number_reading is None:
        return None

    return f"{number_reading} 퍼센트"


def try_parse_percent_point(text: str) -> str | None:
    match = re.fullmatch(r"(.+)%p", text)
    if not match:
        return None

    number_reading = _read_positive_number(match.group(1))
    if number_reading is None:
        return None

    return f"{number_reading} 퍼센트포인트"


def try_parse_temperature(text: str) -> str | None:
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)(℃|℉)", text)
    if not match:
        return None

    number_text, unit_text = match.groups()
    is_negative = number_text.startswith("-")
    unsigned_number_text = number_text[1:] if is_negative else number_text
    unsigned_number_reading = _read_positive_number_for_decimal_unit(unsigned_number_text)
    if unsigned_number_reading is None:
        return None

    temperature_reading = (
        f"영하 {unsigned_number_reading}" if is_negative else unsigned_number_reading
    )

    if unit_text == "℃":
        return f"{temperature_reading}도"
    return f"화씨 {temperature_reading}도"


def try_parse_signed_degree_quantity(text: str) -> str | None:
    match = re.fullmatch(r"(-(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?)(?:\s*)도", text)
    if not match:
        return None

    number_reading = _read_number(match.group(1))
    if number_reading is None or not number_reading.startswith("마이너스 "):
        return None
    return f"{number_reading}도"


def try_parse_basic_unit(text: str) -> str | None:
    # USER.md: ambiguous single-letter units such as A/V must be preserved.
    if re.fullmatch(rf"{_NUMBER_PATTERN}(?:\s*)[A-Z]", text):
        unit_candidate = re.sub(rf"^{_NUMBER_PATTERN}(?:\s*)", "", text)
        if unit_candidate in _AMBIGUOUS_SINGLE_LETTER_UNITS:
            return None

    safe_units = {unit: reading for unit, reading in BASIC_UNITS.items() if unit not in _RISKY_SYMBOLIC_UNITS}
    unit_pattern = "|".join(sorted(map(re.escape, safe_units), key=len, reverse=True))
    match = re.fullmatch(rf"({_NUMBER_PATTERN})(?:\s*)({unit_pattern})({_UNIT_PARTICLE_PATTERN})", text)
    if not match:
        return None

    number_text, unit_text, particle_text = match.groups()
    number_reading = _read_positive_number_for_decimal_unit(number_text)
    if number_reading is None:
        return None

    # Sino-Korean numbers should be attached to the unit (no space)
    # Native-Korean numbers (which we don't handle in basic_unit yet, but for future) should be spaced.
    # Current basic units are mostly Sino-Korean or English units.
    # For English units, space is usually better, but for '도' it should be attached.
    if unit_text == "도":
        return f"{number_reading}{unit_text}{particle_text}"
    return f"{number_reading} {safe_units[unit_text]}{particle_text}"


def try_parse_duration(text: str) -> str | None:
    # Duration parsing is exact and local: number+시간/분/초/... is allowed,
    # but this parser does not infer broader time semantics from context.
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(?:\s*)(시간|분|초|일|개월|년)", text)
    if not match:
        return None

    number_text, unit_text = match.groups()
    if "." in number_text and not _has_supported_fractional_length(number_text):
        return None
    number_reading = _read_duration_number(unit_text, number_text)
    if number_reading is None:
        return None

    # Sino-Korean numbers (for 년, 월, 일, 개월) should be attached.
    # Native-Korean numbers (for 시간, 분, 초 - wait, 분/초 are Sino) should be spaced?
    # Policy: Native -> space, Sino -> no space.
    if unit_text == "시간":
        return f"{number_reading} {unit_text}"
    return f"{number_reading}{unit_text}"


def try_parse_filesize(text: str) -> str | None:
    unit_pattern = "|".join(sorted(map(re.escape, FILESIZE_UNITS), key=len, reverse=True))
    match = re.fullmatch(rf"({_NUMBER_PATTERN})(?:\s*)({unit_pattern})({_UNIT_PARTICLE_PATTERN})", text)
    if not match:
        return None

    number_text, unit_text, particle_text = match.groups()
    number_reading = _read_positive_number_for_decimal_unit(number_text)
    if number_reading is None:
        return None

    return f"{number_reading} {FILESIZE_UNITS[unit_text]}{particle_text}"


def try_parse_decimal_attached_unit(text: str) -> str | None:
    safe_units = {unit: reading for unit, reading in BASIC_UNITS.items() if unit not in _RISKY_SYMBOLIC_UNITS}
    attached_units = {"도": "도", **safe_units, **FILESIZE_UNITS}
    unit_pattern = "|".join(sorted(map(re.escape, attached_units), key=len, reverse=True))
    match = re.fullmatch(
        rf"(-?(?:\d+|\d{{1,3}}(?:,\d{{3}})+)\.\d+)(?:\s*)({unit_pattern})",
        text,
    )
    if not match:
        return None

    number_text, unit_text = match.groups()
    number_reading = _read_number_for_decimal_unit(number_text)
    if number_reading is None:
        return None

    if unit_text == "도":
        return f"{number_reading}도"
    return f"{number_reading} {attached_units[unit_text]}"


def try_parse_krw(text: str) -> str | None:
    if text.endswith("원"):
        number_text = text[:-1]
    elif text.startswith("₩"):
        number_text = text[1:]
    else:
        return None

    normalized = _normalize_number(number_text)
    if normalized is None or "." in normalized or normalized.startswith("-"):
        return None

    return f"{read_integer_ko(normalized)} 원"


def try_parse_compact_krw(text: str) -> str | None:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(만|억|조)\s*원", text)
    if not match:
        return None

    number_text, large_unit = match.groups()
    integer_part_text = number_text.split(".", 1)[0]
    multipliers = {"만": Decimal("10000"), "억": Decimal("100000000"), "조": Decimal("1000000000000")}
    try:
        amount = Decimal(number_text) * multipliers[large_unit]
    except InvalidOperation:
        return None

    if amount != amount.to_integral_value():
        return None

    reading = read_integer_ko(str(int(amount)))
    if integer_part_text == "1" and reading.startswith(f"{large_unit} "):
        reading = f"일{reading}"
    return f"{reading} 원"


def try_parse_usd(text: str) -> str | None:
    if not text.startswith("$"):
        return None

    normalized = _normalize_number(text[1:])
    if normalized is None or normalized.startswith("-"):
        return None

    number_reading = _read_positive_number(normalized)
    if number_reading is None:
        return None

    return f"{number_reading} 달러"


def try_parse_eur(text: str) -> str | None:
    if not text.startswith("€"):
        return None

    normalized = _normalize_number(text[1:])
    if normalized is None or normalized.startswith("-"):
        return None

    number_reading = _read_positive_number(normalized)
    if number_reading is None:
        return None

    return f"{number_reading} 유로"


def try_parse_jpy(text: str) -> str | None:
    if not (text.startswith("￥") or text.startswith("¥")):
        return None

    normalized = _normalize_number(text[1:])
    if normalized is None or "." in normalized or normalized.startswith("-"):
        return None

    return f"{read_integer_ko(normalized)} 엔"


def try_parse_gbp(text: str) -> str | None:
    if not text.startswith("£"):
        return None

    normalized = _normalize_number(text[1:])
    if normalized is None or "." in normalized or normalized.startswith("-"):
        return None

    return f"{read_integer_ko(normalized)} 파운드"
