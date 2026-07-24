from __future__ import annotations

from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_spaced_integer_value
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.large_unit import parse_mixed_integer_core_at
from engine.span_engine.numeric_dae import evaluate_numeric_dae_counter_context

# 사람/살 retain native-style readings through 99; 100+ uses Sino-Korean reading.
NATIVE_ONLY_1_TO_99_COUNTERS = frozenset({"사람", "살"})

# 시간 follows the native counter reading path used by time/range policy.
_NATIVE_TIME_COUNTERS = frozenset({"시간"})
NATIVE_COUNTERS = NATIVE_ONLY_1_TO_99_COUNTERS | _NATIVE_TIME_COUNTERS

HYBRID_COUNTER_THRESHOLD = 39
DEFAULT_HYBRID_COUNTER_THRESHOLD = 30

HYBRID_THRESHOLD_39_COUNTERS = frozenset(
    {
        "개",
        "권",
        "장",
        "명",
        "마리",
        "그루",
        "송이",
        "자루",
        "알",
        "벌",
        "켤레",
        "그릇",
        "공기",
        "잔",
        "병",
        "조각",
        "차례",
        "건",
        "곳",
        "팀",
        "쌍",
        "상자",
        "봉지",
        "통",
        "묶음",
        "편",
        "판",
        "줄",
        "칸",
        "대",
        "석",
        "표",
        "매",
        "문항",
        "문제",
        "곡",
        "장면",
        "세트",
        "팩",
        "봉",
        "종류",
        "항목",
        "사례",
        "척",
    }
)

# Backward-compatible alias for existing imports/tests.
THRESHOLD_39_HYBRID_COUNTERS = HYBRID_THRESHOLD_39_COUNTERS
HYBRID_COUNTERS = HYBRID_THRESHOLD_39_COUNTERS
SINO_COUNTERS = frozenset(
    {
        "층",
        "호",
        "동",
        "년",
        "월",
        "일",
        "분",
        "초",
        "개월",
        "원",
        "도",
        "점",
        "미터",
        "킬로그램",
        "학년",
        "학기",
        "회",
    }
)
SUPPORTED_COUNTERS = NATIVE_COUNTERS | HYBRID_COUNTERS | SINO_COUNTERS
COUNTERS_BY_LENGTH = sorted(SUPPORTED_COUNTERS, key=len, reverse=True)

SPACELESS_COUNTERS = frozenset(
    {"년", "월", "일", "분", "초", "개월", "도", "학년", "학기"}
)
LEADING_ZERO_OVERRIDE_COUNTERS = frozenset({"월", "일", "분", "초"})
EMERGENCY_AMBIGUOUS_NUMBERS = frozenset({"112", "119"})
EMERGENCY_COUNTER_FALLBACKS = frozenset({("112", "명"), ("119", "건")})
PUBLIC_NUMBER_AMBIGUOUS_NUMBERS = frozenset(
    {"110", "120", "117", "118", "1339", "182", "125", "129", "1388", "1399"}
)

_NATIVE_ONES = {
    1: "한",
    2: "두",
    3: "세",
    4: "네",
    5: "다섯",
    6: "여섯",
    7: "일곱",
    8: "여덟",
    9: "아홉",
}
_NATIVE_TENS = {
    10: "열",
    20: "스물",
    30: "서른",
    40: "마흔",
    50: "쉰",
    60: "예순",
    70: "일흔",
    80: "여든",
    90: "아흔",
}
_PREV_BLOCKERS = frozenset("+-.,~:/")


def counter_mode(counter: str) -> str | None:
    if not isinstance(counter, str):
        raise TypeError("counter must be str")
    if counter in NATIVE_COUNTERS:
        return "native_only"
    if counter in HYBRID_COUNTERS:
        return "hybrid"
    if counter in SINO_COUNTERS:
        return "sino_only"
    return None


def is_supported_counter(counter: str) -> bool:
    if not isinstance(counter, str):
        raise TypeError("counter must be str")
    return counter in SUPPORTED_COUNTERS


def is_emergency_ambiguous_number(raw_number: str) -> bool:
    if not isinstance(raw_number, str):
        raise TypeError("raw_number must be str")
    return raw_number in EMERGENCY_AMBIGUOUS_NUMBERS


def native_number_under_100(value: int) -> str | None:
    if not isinstance(value, int):
        raise TypeError("value must be int")
    if value < 1 or value > 99:
        return None
    if value < 10:
        return _NATIVE_ONES[value]
    tens = (value // 10) * 10
    ones = value % 10
    if ones == 0:
        return "스무" if value == 20 else _NATIVE_TENS[tens]
    return f"{_NATIVE_TENS[tens]}{_NATIVE_ONES[ones]}"


def counter_number_reading(raw_number: str, counter: str) -> str | None:
    if not isinstance(raw_number, str):
        raise TypeError("raw_number must be str")
    if not isinstance(counter, str):
        raise TypeError("counter must be str")
    normalized_number = raw_number.replace(",", "")
    if not _is_valid_integer(raw_number) or not is_supported_counter(counter):
        return None
    if _has_unsupported_leading_zero(normalized_number, counter):
        return None

    value = int(normalized_number)
    dae_sino_threshold = counter == "대" and value >= 40

    if not dae_sino_threshold and is_emergency_ambiguous_number(normalized_number) and (
        normalized_number,
        counter,
    ) not in EMERGENCY_COUNTER_FALLBACKS:
        return None
    if (
        not dae_sino_threshold
        and normalized_number in PUBLIC_NUMBER_AMBIGUOUS_NUMBERS
        and counter not in {"점"}
    ):
        return None

    mode = counter_mode(counter)
    if value >= 100:
        try:
            reading = read_spaced_integer_value(value)
        except ValueError:
            return None
    elif mode == "native_only":
        reading = native_number_under_100(value)
    elif mode == "hybrid":
        threshold = (
            HYBRID_COUNTER_THRESHOLD
            if counter in HYBRID_THRESHOLD_39_COUNTERS
            else DEFAULT_HYBRID_COUNTER_THRESHOLD
        )
        reading = (
            native_number_under_100(value)
            if 1 <= value <= threshold
            else _sino(value)
        )
    elif mode == "sino_only":
        reading = _sino(value)
    else:
        reading = None
    if reading is None:
        return None
    return reading + ("" if counter in SPACELESS_COUNTERS else " ")


def scan_counter_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        number_start = index
        mixed_core = parse_mixed_integer_core_at(raw_text, number_start)
        number_end = (
            mixed_core.end
            if mixed_core is not None
            else _consume_integer(raw_text, number_start)
        )
        if number_end is None:
            index += 1
            continue
        raw_number = raw_text[number_start:number_end]
        if _has_invalid_spaced_ordinal_prefix(raw_text, number_start):
            index = number_end
            continue
        counter_start = _consume_optional_ascii_space(raw_text, number_end)
        has_space_before_counter = counter_start != number_end
        for counter in COUNTERS_BY_LENGTH:
            if not raw_text.startswith(counter, counter_start):
                continue
            counter_end = counter_start + len(counter)
            reading = (
                _mixed_counter_number_reading(mixed_core, counter)
                if mixed_core is not None
                else counter_number_reading(raw_number, counter)
            )
            if reading is None:
                continue
            if has_space_before_counter and reading.endswith(" "):
                reading = reading[:-1]
            number_span = SourceSpan(number_start, number_end)
            counter_span = SourceSpan(counter_start, counter_end)
            full_span = SourceSpan(number_start, counter_end)
            if not _valid_boundary(raw_text, number_span, counter_span):
                break
            if _has_supported_counter_prefix_tail(raw_text, counter_start, counter_end):
                break
            if _has_supported_counter_unsafe_tail(raw_text, counter_end):
                break
            if mixed_core is not None and _has_mixed_counter_path_tail(
                raw_text, counter_end
            ):
                break
            reason = "counter_policy_gate"
            if counter == "대" and not has_space_before_counter:
                decision = evaluate_numeric_dae_counter_context(raw_text, full_span)
                if decision.action != "DEFER_TO_COUNTER":
                    break
                reason = decision.reason
            candidates.append(
                SurfaceCandidate(
                    core_span=number_span,
                    full_span=full_span,
                    owner="counter_noun",
                    surface_type="COUNTER_SURFACE",
                    suffix_spans=[counter_span],
                    reason=reason,
                    metadata={
                        "raw_number": raw_number,
                        "counter": counter,
                        "counter_mode": counter_mode(counter),
                        "counter_span": counter_span,
                        "reading": reading,
                    },
                )
            )
            break
        index = number_end
    return candidates


def _mixed_counter_number_reading(
    mixed_core, counter: str
) -> str | None:
    if mixed_core is None or not is_supported_counter(counter):
        return None
    if mixed_core.value < 100:
        return None
    return mixed_core.reading + ("" if counter in SPACELESS_COUNTERS else " ")


def _has_supported_counter_prefix_tail(
    raw_text: str, counter_start: int, counter_end: int
) -> bool:
    for counter in COUNTERS_BY_LENGTH:
        full_counter_end = counter_start + len(counter)
        if full_counter_end <= counter_end:
            continue
        if raw_text.startswith(counter, counter_start):
            return True
    return False


def _has_supported_counter_unsafe_tail(raw_text: str, counter_end: int) -> bool:
    next_char = raw_text[counter_end] if counter_end < len(raw_text) else None
    return next_char is not None and next_char.isascii() and next_char.isalnum()


def _has_mixed_counter_path_tail(raw_text: str, counter_end: int) -> bool:
    return counter_end < len(raw_text) and raw_text[counter_end] == "/"


def parse_counter_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "counter_noun":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    raw_number = raw_text[candidate.core_span.start : candidate.core_span.end]
    counter = candidate.metadata.get("counter")
    if not isinstance(counter, str):
        return None
    return counter_number_reading(raw_number, counter)


def _sino(value: int) -> str | None:
    if value < 0 or value > 9999:
        return None
    return number_to_korean_under_10000(value)


def _has_unsupported_leading_zero(raw_number: str, counter: str) -> bool:
    if len(raw_number) <= 1 or not raw_number.startswith("0"):
        return False
    if (
        counter in LEADING_ZERO_OVERRIDE_COUNTERS
        and len(raw_number) == 2
        and int(raw_number) > 0
    ):
        return False
    return True


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
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


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _has_invalid_spaced_ordinal_prefix(raw_text: str, number_start: int) -> bool:
    if not (
        number_start > 1
        and raw_text[number_start - 1] == " "
        and raw_text[number_start - 2] == "제"
    ):
        return False
    prefix_start = number_start - 2
    return prefix_start > 0 and not raw_text[prefix_start - 1].isspace()


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


def _valid_boundary(
    raw_text: str, number_span: SourceSpan, counter_span: SourceSpan
) -> bool:
    prev_char = raw_text[number_span.start - 1] if number_span.start > 0 else None
    next_char = raw_text[counter_span.end] if counter_span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if _is_complete_hangul(prev_char):
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    return True


def _is_complete_hangul(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


__all__ = [
    "COUNTERS_BY_LENGTH",
    "EMERGENCY_AMBIGUOUS_NUMBERS",
    "HYBRID_THRESHOLD_39_COUNTERS",
    "HYBRID_COUNTERS",
    "HYBRID_COUNTER_THRESHOLD",
    "DEFAULT_HYBRID_COUNTER_THRESHOLD",
    "NATIVE_COUNTERS",
    "NATIVE_ONLY_1_TO_99_COUNTERS",
    "PUBLIC_NUMBER_AMBIGUOUS_NUMBERS",
    "SINO_COUNTERS",
    "SPACELESS_COUNTERS",
    "SUPPORTED_COUNTERS",
    "THRESHOLD_39_HYBRID_COUNTERS",
    "counter_mode",
    "counter_number_reading",
    "is_emergency_ambiguous_number",
    "is_supported_counter",
    "native_number_under_100",
    "parse_counter_candidate",
    "scan_counter_candidates",
]
