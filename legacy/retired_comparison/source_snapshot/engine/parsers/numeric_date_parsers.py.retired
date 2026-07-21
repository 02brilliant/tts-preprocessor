from __future__ import annotations

import re
from typing import Literal

from engine.dictionary.base_dictionary import DIGIT_KO, LARGE_UNITS, NATIVE_HOUR_KO, PHONE_DIGIT_KO, SMALL_UNITS

NUMERIC_INTEGER_PATTERN = r"(?:\d+|\d{1,3}(?:,\d{3})+)"
NUMERIC_DECIMAL_PATTERN = rf"{NUMERIC_INTEGER_PATTERN}\.\d+"
NUMERIC_FRACTION_PATTERN = r"\d+/\d+"
NUMERIC_RANGE_PATTERN = rf"{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?~{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?"

NumericPatternKind = Literal[
    "comma_integer",
    "comma_decimal",
    "fraction",
    "range",
    "plain_decimal",
    "plain_integer",
]
NumberReadingMode = Literal["NUMBER_MODE", "DIGIT_MODE"]

NUMBER_MODE: NumberReadingMode = "NUMBER_MODE"
DIGIT_MODE: NumberReadingMode = "DIGIT_MODE"
_NUMBER_MODE_OVERRIDE_CONTEXTS = {"date", "time", "currency", "unit", "counter_noun"}

STRICT_COMMA_NUMBER_PATTERN = re.compile(r"\b\d{1,3}(,\d{3})+(\.\d+)?\b")
_PLAIN_INTEGER_RE = re.compile(r"\d+")
_PLAIN_DECIMAL_RE = re.compile(r"\d+\.\d+")
_DECIMAL_PARTS_RE = re.compile(r"(\d+)\.(\d+)")


def determine_number_mode(
    token: str,
    context: str | dict[str, str] | None = None,
) -> NumberReadingMode:
    category: str | None = None
    preferred_mode: NumberReadingMode | None = None

    if isinstance(context, dict):
        category = context.get("category")
        preferred_value = context.get("preferred_mode")
        if preferred_value in {NUMBER_MODE, DIGIT_MODE}:
            preferred_mode = preferred_value
    elif isinstance(context, str):
        category = context

    if category in _NUMBER_MODE_OVERRIDE_CONTEXTS:
        return NUMBER_MODE
    if len(token) > 1 and token.startswith("0"):
        return DIGIT_MODE
    if preferred_mode is not None:
        return preferred_mode
    return NUMBER_MODE


def read_digit_sequence_ko(text: str) -> str:
    normalized_text = normalize_number_text(text)
    if normalized_text is None or not _PLAIN_INTEGER_RE.fullmatch(normalized_text):
        raise ValueError("read_digit_sequence_ko only supports unsigned integer text")
    return "".join(PHONE_DIGIT_KO[digit] for digit in normalized_text)


def read_number_token_ko(
    text: str,
    context: str | dict[str, str] | None = None,
) -> str | None:
    normalized_text = normalize_number_text(text)
    if normalized_text is None or not _PLAIN_INTEGER_RE.fullmatch(normalized_text):
        return None

    mode = determine_number_mode(normalized_text, context)
    if mode == DIGIT_MODE:
        return read_digit_sequence_ko(normalized_text)
    return read_integer_ko(normalized_text)


def classify_numeric_pattern(text: str) -> NumericPatternKind | None:
    if re.fullmatch(NUMERIC_FRACTION_PATTERN, text):
        return "fraction"
    if re.fullmatch(NUMERIC_RANGE_PATTERN, text):
        return "range"

    normalized = normalize_number_text(text)
    if normalized is None:
        return None

    if "." in normalized:
        return "comma_decimal" if "," in text else "plain_decimal"
    return "comma_integer" if "," in text else "plain_integer"


def normalize_number_text(text: str) -> str | None:
    if STRICT_COMMA_NUMBER_PATTERN.fullmatch(text):
        return text.replace(",", "")
    if _PLAIN_INTEGER_RE.fullmatch(text):
        return text
    if _PLAIN_DECIMAL_RE.fullmatch(text):
        return text
    return None


def _read_under_10000(text: str) -> str:
    value = int(text)
    if value == 0:
        return ""

    digits = f"{value:04d}"
    parts: list[str] = []

    for index, digit in enumerate(digits):
        if digit == "0":
            continue

        unit = SMALL_UNITS[3 - index]
        if digit == "1" and unit:
            parts.append(unit)
        else:
            parts.append(f"{DIGIT_KO[digit]}{unit}")

    return "".join(parts)


def read_integer_ko(text: str) -> str:
    normalized_text = normalize_number_text(text)
    if normalized_text is None or not _PLAIN_INTEGER_RE.fullmatch(normalized_text):
        raise ValueError("read_integer_ko only supports unsigned integer text")

    normalized = normalized_text.lstrip("0") or "0"
    if normalized == "0":
        return DIGIT_KO["0"]

    groups: list[str] = []
    while normalized:
        groups.append(normalized[-4:])
        normalized = normalized[:-4]

    parts: list[str] = []
    for index in range(len(groups) - 1, -1, -1):
        group_text = groups[index]
        group_reading = _read_under_10000(group_text)
        if not group_reading:
            continue

        large_unit = LARGE_UNITS[index]
        if large_unit:
            if large_unit == "만" and group_reading == "일":
                parts.append(large_unit)
            else:
                parts.append(f"{group_reading}{large_unit}" if group_reading != "" else large_unit)
        else:
            parts.append(group_reading)

    return " ".join(parts)


def read_decimal_ko(text: str) -> str:
    normalized_text = normalize_number_text(text)
    if normalized_text is None:
        raise ValueError("read_decimal_ko only supports unsigned decimal text")

    match = _DECIMAL_PARTS_RE.fullmatch(normalized_text)
    if not match:
        raise ValueError("read_decimal_ko only supports unsigned decimal text")

    integer_part, decimal_part = match.groups()
    decimal_reading = "".join(DIGIT_KO[digit] for digit in decimal_part)
    return f"{read_integer_ko(integer_part)}쩜{decimal_reading}"


def read_negative_ko(text: str) -> str | None:
    if not text.startswith("-") or len(text) == 1:
        return None

    body = normalize_number_text(text[1:])
    if body is None:
        return None
    if _PLAIN_INTEGER_RE.fullmatch(body):
        return f"마이너스 {read_integer_ko(body)}"
    if _PLAIN_DECIMAL_RE.fullmatch(body):
        return f"마이너스 {read_decimal_ko(body)}"
    return None


def read_number_ko(text: str) -> str | None:
    kind = classify_numeric_pattern(text)
    normalized = normalize_number_text(text)
    if kind in {"comma_integer", "plain_integer"} and normalized is not None:
        return read_number_token_ko(normalized)
    if kind in {"comma_decimal", "plain_decimal"} and normalized is not None:
        return read_decimal_ko(normalized)
    return None


def try_parse_comma_number_with_suffix(text: str) -> str | None:
    match = re.fullmatch(rf"({NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)([가-힣]+)", text)
    if not match:
        return None

    number_text, suffix = match.groups()
    kind = classify_numeric_pattern(number_text)
    if kind not in {"comma_integer", "comma_decimal", "plain_integer", "plain_decimal"}:
        return None
    if kind in {"plain_integer", "plain_decimal"}:
        normalized = normalize_number_text(number_text)
        if normalized is None or len(normalized.split(".", 1)[0]) < 4:
            return None

    number_reading = read_number_ko(number_text)
    if number_reading is None:
        return None

    return f"{number_reading} {suffix}"


def try_parse_fraction(text: str) -> str | None:
    if classify_numeric_pattern(text) != "fraction":
        return None

    match = re.fullmatch(r"(\d+)/(\d+)", text)
    if not match:
        return None

    numerator, denominator = match.groups()
    if int(denominator) == 0:
        return None

    return f"{read_integer_ko(denominator)}분의 {read_integer_ko(numerator)}"


def try_parse_number_range(text: str) -> str | None:
    if "~" in text:
        return None

    if classify_numeric_pattern(text) != "range":
        return None

    match = re.fullmatch(rf"({NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)~({NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)", text)
    if not match:
        return None

    start_text, end_text = match.groups()
    start_reading = read_number_ko(start_text)
    end_reading = read_number_ko(end_text)
    if start_reading is None or end_reading is None:
        return None

    return f"{start_reading}에서 {end_reading}"


def _read_hour_ko(hour: int) -> str:
    # HH 0-12 is Native, 13-24 is Sino.
    if 0 <= hour <= 12:
        # hour 0 is usually treated same as 12 (midnight/noon) in native context,
        # but policy says 0-12 is native. Native dictionary has 1-12.
        # If hour is 0, we can use 12's reading or handle as special.
        # Actually, 0시 is often '영 시' (Sino) but policy says 0-12 native.
        # Let's check dictionary for 0. It's missing.
        if hour == 0:
            return "영" # Fallback to Sino for 0 specifically as native 0 is rare.
        return NATIVE_HOUR_KO[hour]
    return read_integer_ko(str(hour))


def _render_clock_time(
    hour: int,
    minute: int | None = None,
    second: int | None = None,
    *,
    force_minute: bool = False,
) -> str | None:
    if not 0 <= hour <= 24:
        return None
    if minute is not None and not 0 <= minute <= 59:
        return None
    if second is not None and not 0 <= second <= 59:
        return None
    # 24:00 is allowed, but 24:01+ is not.
    if hour == 24 and ((minute or 0) != 0 or (second or 0) != 0):
        return None

    parts = [f"{_read_hour_ko(hour)} 시"]
    if minute is not None:
        # Always Sino for minute.
        # If force_minute is True, we always add minute part.
        if force_minute or minute != 0 or second is not None:
            parts.append(f"{read_integer_ko(str(minute))} 분")
    if second is not None:
        # Always Sino for second.
        parts.append(f"{read_integer_ko(str(second))} 초")
    return " ".join(parts)


def _read_month_ko(month: int) -> str:
    if month == 10:
        return "시"
    return read_integer_ko(str(month))


def _read_day_ko(day: int) -> str:
    if day == 1:
        return "일일"
    reading = read_integer_ko(str(day))
    return reading if reading.endswith("일") else f"{reading}일"


def try_parse_independent_time(text: str) -> str | None:
    """
    Parses 'Safe' time patterns that don't need context:
    - H시, HH시, H시 M분, HH시 MM분, H시 M분 S초, HH시 MM분 SS초
    - H:MM:SS, HH:MM:SS
    """
    # H:MM:SS format
    colon_with_seconds = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", text)
    if colon_with_seconds:
        hour, minute, second = map(int, colon_with_seconds.groups())
        return _render_clock_time(hour, minute, second, force_minute=True)

    # Korean format: H시 [M분] [S초]
    korean = re.fullmatch(r"(\d{1,2})시(?:\s*(\d{1,2})분(?:\s*(\d{1,2})초)?|\s*(\d{1,2})초)?", text)
    if korean:
        hour_text, minute_text, second_text, second_only_text = korean.groups()
        hour = int(hour_text)
        if second_only_text is not None:
            return _render_clock_time(hour, None, int(second_only_text))
        if minute_text is not None:
            second = int(second_text) if second_text is not None else None
            return _render_clock_time(hour, int(minute_text), second)
        return _render_clock_time(hour)

    return None


def try_parse_conditional_time(text: str) -> str | None:
    """
    Parses 'Ambiguous' time patterns that require context:
    - H:MM, HH:MM
    """
    # Optional prefix like 오전/오후 might be captured by the regex in base_rules,
    # but the parser itself just handles the HH:MM part if passed here.
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if not match:
        return None

    prefix_text = ""
    prefix_match = re.match(r"(오전|오후|새벽|아침|정오|밤|저녁)\s*", text)
    if prefix_match:
        prefix_text = prefix_match.group(0)

    hour, minute = map(int, match.groups())
    rendered = _render_clock_time(hour, minute, force_minute=True)
    if rendered is None:
        return None

    return f"{prefix_text}{rendered}"


def try_parse_time(text: str) -> str | None:
    # Legacy wrapper for backward compatibility if needed,
    # though base_rules should switch to the specific ones.
    return try_parse_independent_time(text) or try_parse_conditional_time(text)


def _read_date(year: str | None, month_text: str, day_text: str) -> str | None:
    month = int(month_text)
    day = int(day_text)

    if not 1 <= month <= 12:
        return None
    if not 1 <= day <= 31:
        return None

    if year is None:
        return f"{_read_month_ko(month)}월 {_read_day_ko(day)}"
    return f"{read_integer_ko(year)}년 {_read_month_ko(month)}월 {_read_day_ko(day)}"


def try_parse_date(text: str) -> str | None:
    numeric = re.fullmatch(r"(\d{4})([-./])(\d{1,2})\2(\d{1,2})", text)
    if numeric:
        return _read_date(numeric.group(1), numeric.group(3), numeric.group(4))

    korean_full = re.fullmatch(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if korean_full:
        return _read_date(korean_full.group(1), korean_full.group(2), korean_full.group(3))

    korean_month_day = re.fullmatch(r"(\d{1,2})월\s*(\d{1,2})일", text)
    if korean_month_day:
        return _read_date(None, korean_month_day.group(1), korean_month_day.group(2))

    return None


def try_parse_date_range(text: str) -> str | None:
    match = re.fullmatch(r"(.+?)~(.+)", text)
    if not match:
        return None

    start_text, end_text = match.groups()
    start = try_parse_date(start_text.strip())
    end = try_parse_date(end_text.strip())
    if start is None or end is None:
        return None

    return f"{start}부터 {end}일까지"


def try_parse_year_range(text: str) -> str | None:
    match = re.fullmatch(r"(\d{4})\s*~\s*(\d{4})년", text)
    if not match:
        match = re.fullmatch(r"(\d{4})년\s*~\s*(\d{4})년", text)
    if not match:
        return None

    start_year, end_year = match.groups()
    return f"{read_integer_ko(start_year)}년에서 {read_integer_ko(end_year)}년까지"
