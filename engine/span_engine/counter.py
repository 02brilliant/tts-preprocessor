from __future__ import annotations

from engine.span_engine.models import RenderPiece, SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    read_sino_time_suffix_number_text,
    read_spaced_integer_value,
)
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.large_unit import (
    parse_large_unit_integer_core_at,
    parse_mixed_integer_core_at,
)
from engine.span_engine.mixed_integer import is_safe_mixed_integer_left_boundary
from engine.span_engine.numeric_dae import evaluate_numeric_dae_counter_context

# 사람/살 retain native-style readings through 99; 100+ uses Sino-Korean reading.
NATIVE_ONLY_1_TO_99_COUNTERS = frozenset({"사람", "살", "가지"})

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
        "자녀",
        "자리",
        "자릿수",
        "자매",
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
        "냥",
        "되",
        "섬",
        "돈",
        "말",
        "발",
        "푼",
    }
)

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
    {"년", "월", "일", "분", "초", "개월", "도", "학년", "학기", "냥"}
)
LEADING_ZERO_OVERRIDE_COUNTERS = frozenset({"월", "일"})
SINO_TIME_SUFFIX_COUNTERS = frozenset({"분", "초"})
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
_LARGE_UNIT_COUNTER_COLLISION_COUNTERS = frozenset({"개", "개월"})
_LONG_CHARACTER_COUNTERS = frozenset({"자녀", "자루", "자리", "자릿수", "자매"})
INTEGER_ONLY_SPECIAL_DETERMINER_UNITS = frozenset(
    {"냥", "되", "섬", "자", "돈", "말", "발", "푼"}
)
_SPECIAL_DETERMINER_COUNTER_READINGS = {
    "냥": {3: "석", 4: "넉"},
    "되": {3: "석", 4: "넉"},
    "섬": {3: "석", 4: "넉"},
    "자": {3: "석", 4: "넉"},
    "돈": {3: "서", 4: "너"},
    "말": {3: "서", 4: "너"},
    "발": {3: "서", 4: "너"},
    "푼": {3: "서", 4: "너"},
}
_STRICT_SPECIAL_DETERMINER_COUNTERS = (
    (INTEGER_ONLY_SPECIAL_DETERMINER_UNITS - {"냥"}) & SUPPORTED_COUNTERS
)
_SPECIAL_DETERMINER_CONTEXT_ANCHORS = {
    "냥": frozenset({"금", "은", "무게", "중량", "화폐", "가격"}),
    "되": frozenset({"쌀", "보리", "콩", "곡식", "곡물", "수확", "부피"}),
    "섬": frozenset({"쌀", "보리", "콩", "곡식", "곡물", "수확", "부피"}),
    "자": frozenset({"길이", "거리", "폭", "너비", "높이", "깊이", "천", "비단"}),
    "돈": frozenset({"금", "은", "무게", "중량", "화폐", "가격"}),
    "말": frozenset({"쌀", "보리", "콩", "곡식", "곡물", "수확", "부피"}),
    "발": frozenset({"길이", "거리", "폭", "너비", "높이", "깊이", "천", "비단"}),
    "푼": frozenset({"금", "은", "무게", "중량", "화폐", "가격"}),
}
_CHARACTER_COUNT_PREFIX_ANCHORS = frozenset(
    {"비밀번호", "아이디", "한글", "영문", "문자", "앞", "뒤", "입력", "제한"}
)
_CHARACTER_COUNT_SUFFIX_ANCHORS = frozenset({"이내", "이상", "입력", "제한"})
_CHARACTER_LENGTH_PREFIX_ANCHORS = frozenset(
    {"길이", "폭", "너비", "높이", "깊이", "천", "비단"}
)
_CHARACTER_CONTEXT_PARTICLES = (
    "으로",
    "에서",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "로",
)
_LARGE_UNIT_COUNTER_ATTACHED_TAILS = (
    "였습니다",
    "이었습니다",
    "였지만",
    "였고",
    "였다",
    "입니다",
    "이다",
    "이었",
    "이며",
    "이고",
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
    "마다",
    "다",
)


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
    if counter in SINO_TIME_SUFFIX_COUNTERS:
        reading = read_sino_time_suffix_number_text(raw_number)
        if reading is None:
            return None
        return reading
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
        special_reading = special_determiner_reading(value, counter)
        reading = special_reading or (
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
        large_unit_core = parse_large_unit_integer_core_at(raw_text, number_start)
        small_unit_core = parse_mixed_integer_core_at(raw_text, number_start)
        plain_number_end = _consume_integer(raw_text, number_start)
        if plain_number_end is not None:
            character_candidate = _character_ja_candidate(
                raw_text, number_start, plain_number_end
            )
            if character_candidate is not None:
                candidates.append(character_candidate)
                index = plain_number_end
                continue
        prefer_plain_counter = (
            plain_number_end is not None
            and _has_registered_counter_at(raw_text, plain_number_end)
        )
        mixed_core = (
            None if prefer_plain_counter else large_unit_core or small_unit_core
        )
        if prefer_plain_counter:
            large_unit_core = None
        number_end = (
            mixed_core.end
            if mixed_core is not None
            else plain_number_end
        )
        if number_end is None:
            index += 1
            continue
        raw_number = raw_text[number_start:number_end]
        counter_start = _consume_optional_ascii_space(raw_text, number_end)
        has_space_before_counter = counter_start != number_end
        for counter in COUNTERS_BY_LENGTH:
            if not raw_text.startswith(counter, counter_start):
                continue
            if counter == "시간" and has_space_before_counter:
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
            if not _valid_boundary(
                raw_text,
                number_span,
                counter_span,
                allow_attached_korean_left=mixed_core is not None,
            ):
                break
            if _has_supported_counter_prefix_tail(raw_text, counter_start, counter_end):
                break
            if _has_supported_counter_unsafe_tail(raw_text, counter_end):
                break
            if (
                counter in _STRICT_SPECIAL_DETERMINER_COUNTERS
                and not _has_clear_special_determiner_context(
                    raw_text, number_start, counter_end, counter
                )
            ):
                break
            if (
                counter in _STRICT_SPECIAL_DETERMINER_COUNTERS
                and _has_strict_special_determiner_tail(raw_text, counter_end)
            ):
                break
            if mixed_core is not None and _has_mixed_counter_path_tail(
                raw_text, counter_end
            ):
                break
            full_large_unit_counter_claim = (
                large_unit_core is not None
                and counter in _LARGE_UNIT_COUNTER_COLLISION_COUNTERS
            )
            if full_large_unit_counter_claim and _has_unsafe_large_unit_counter_tail(
                raw_text, counter_end
            ):
                break
            reason = "counter_policy_gate"
            if counter == "대" and not has_space_before_counter:
                decision = evaluate_numeric_dae_counter_context(raw_text, full_span)
                if decision.action != "DEFER_TO_COUNTER":
                    break
                reason = decision.reason
            claim_span = full_span if full_large_unit_counter_claim else number_span
            candidates.append(
                SurfaceCandidate(
                    core_span=claim_span,
                    full_span=full_span,
                    owner="counter_noun",
                    surface_type="COUNTER_SURFACE",
                    suffix_spans=[counter_span],
                    reason=(
                        "counter_large_unit_core_full_consume"
                        if full_large_unit_counter_claim
                        else reason
                    ),
                    metadata={
                        "raw_number": raw_number,
                        "counter": counter,
                        "counter_mode": counter_mode(counter),
                        "counter_span": counter_span,
                        "reading": reading,
                        "numeric_span": number_span,
                        "numeric_core_kind": (
                            "large_unit"
                            if large_unit_core is not None
                            else "mixed_small_unit"
                            if mixed_core is not None
                            else "arabic_integer"
                        ),
                        "full_counter_claim": full_large_unit_counter_claim,
                        "source_space_span": (
                            SourceSpan(number_end, counter_start)
                            if has_space_before_counter
                            else None
                        ),
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


def _has_registered_counter_at(raw_text: str, number_end: int) -> bool:
    counter_start = _consume_optional_ascii_space(raw_text, number_end)
    return any(
        raw_text.startswith(counter, counter_start)
        for counter in COUNTERS_BY_LENGTH
    )


def _has_supported_counter_unsafe_tail(raw_text: str, counter_end: int) -> bool:
    next_char = raw_text[counter_end] if counter_end < len(raw_text) else None
    if next_char is None:
        return False
    if next_char.isascii() and next_char.isalnum():
        return True
    return (
        next_char == "."
        and counter_end + 1 < len(raw_text)
        and raw_text[counter_end + 1].isascii()
        and raw_text[counter_end + 1].isalnum()
    )


def _has_strict_special_determiner_tail(raw_text: str, counter_end: int) -> bool:
    if counter_end >= len(raw_text):
        return False
    next_char = raw_text[counter_end]
    return not (next_char.isspace() or next_char in ",.!?)]};:")


def _character_ja_candidate(
    raw_text: str, number_start: int, number_end: int
) -> SurfaceCandidate | None:
    if number_end >= len(raw_text) or raw_text[number_end] != "자":
        return None
    if any(
        raw_text.startswith(counter, number_end)
        for counter in _LONG_CHARACTER_COUNTERS
    ):
        return None

    raw_number = raw_text[number_start:number_end]
    normalized_number = raw_number.replace(",", "")
    if (
        not _is_valid_integer(raw_number)
        or _has_unsupported_leading_zero(normalized_number, "자")
    ):
        return None
    value = int(normalized_number)
    counter_end = number_end + 1
    if _has_supported_counter_unsafe_tail(raw_text, counter_end):
        return None

    left = raw_text[:number_start]
    right = raw_text[counter_end:]
    je_prefix = _has_bounded_je_prefix(raw_text, number_start)
    if je_prefix:
        return None
    name_context = _has_name_context(left)
    count_context = _has_character_context(
        left,
        right,
        _CHARACTER_COUNT_PREFIX_ANCHORS,
        _CHARACTER_COUNT_SUFFIX_ANCHORS,
    )
    length_context = _has_character_context(
        left,
        right,
        _CHARACTER_LENGTH_PREFIX_ANCHORS,
        frozenset(),
    )
    if not (je_prefix or name_context or count_context or length_context):
        prev_char = raw_text[number_start - 1] if number_start > 0 else None
        if prev_char is not None and (
            prev_char.isascii() and prev_char.isalnum()
            or _is_complete_hangul(prev_char)
            or prev_char in _PREV_BLOCKERS
        ):
            return None

    if name_context:
        reading = _name_character_count_reading(value)
        reason = "name_character_count_context"
        if reading is not None and left.endswith("이름"):
            reading = f" {reading}"
    elif count_context:
        reading = _hybrid_character_count_reading(value)
        reason = "character_count_context"
        if reading is not None and _has_attached_character_prefix(
            left, _CHARACTER_COUNT_PREFIX_ANCHORS
        ):
            reading = f" {reading}"
    elif length_context:
        reading = _length_character_unit_reading(value)
        reason = "traditional_character_length_context"
        if reading is not None and _has_attached_character_prefix(
            left, _CHARACTER_LENGTH_PREFIX_ANCHORS
        ):
            reading = f" {reading}"
    else:
        reading = _sino_or_large_integer_reading(value)
        reason = "general_character_ja_sino"
    if reading is None:
        return None

    number_span = SourceSpan(number_start, number_end)
    counter_span = SourceSpan(number_end, counter_end)
    return SurfaceCandidate(
        core_span=number_span,
        full_span=SourceSpan(number_start, counter_end),
        owner="counter_noun",
        surface_type="COUNTER_SURFACE",
        suffix_spans=[counter_span],
        reason=reason,
        metadata={
            "raw_number": raw_number,
            "counter": "자",
            "counter_mode": (
                "sino_only"
                if reason == "general_character_ja_sino"
                else "hybrid"
            ),
            "counter_span": counter_span,
            "reading": reading,
            "numeric_span": number_span,
            "numeric_core_kind": "arabic_integer",
            "full_counter_claim": False,
        },
    )


def _has_name_context(left: str) -> bool:
    return left.endswith("이름") or left.endswith("이름 ")


def _has_character_context(
    left: str,
    right: str,
    prefix_anchors: frozenset[str],
    suffix_anchors: frozenset[str],
) -> bool:
    left_context = left.rstrip()
    for anchor in prefix_anchors:
        if left_context.endswith(anchor):
            return True
        if any(
            left_context.endswith(f"{anchor}{particle}")
            for particle in _CHARACTER_CONTEXT_PARTICLES
        ):
            return True
    right_context = right.lstrip()
    return any(right_context.startswith(anchor) for anchor in suffix_anchors)


def _has_attached_character_prefix(
    left: str, prefix_anchors: frozenset[str]
) -> bool:
    for anchor in prefix_anchors:
        if left.endswith(anchor):
            return True
        if any(
            left.endswith(f"{anchor}{particle}")
            for particle in _CHARACTER_CONTEXT_PARTICLES
        ):
            return True
    return False


def _has_clear_special_determiner_context(
    raw_text: str, number_start: int, counter_end: int, counter: str
) -> bool:
    anchors = _SPECIAL_DETERMINER_CONTEXT_ANCHORS[counter]
    return any(
        _has_bounded_context_anchor(
            raw_text,
            anchor,
            max(0, number_start - 12),
            number_start,
        )
        or _has_bounded_context_anchor(
            raw_text,
            anchor,
            counter_end,
            min(len(raw_text), counter_end + 12),
        )
        for anchor in anchors
    )


def _has_bounded_context_anchor(
    raw_text: str, anchor: str, window_start: int, window_end: int
) -> bool:
    position = raw_text.find(anchor, window_start, window_end)
    while position != -1:
        anchor_end = position + len(anchor)
        prev_char = raw_text[position - 1] if position > 0 else None
        left_boundary = prev_char is None or not _is_complete_hangul(prev_char)
        right_boundary = (
            anchor_end >= len(raw_text)
            or not _is_complete_hangul(raw_text[anchor_end])
            or any(
                raw_text.startswith(particle, anchor_end)
                and (
                    anchor_end + len(particle) >= len(raw_text)
                    or not _is_complete_hangul(
                        raw_text[anchor_end + len(particle)]
                    )
                )
                for particle in _CHARACTER_CONTEXT_PARTICLES
            )
        )
        if left_boundary and right_boundary:
            return True
        position = raw_text.find(anchor, position + 1, window_end)
    return False


def _name_character_count_reading(value: int) -> str | None:
    if value == 3:
        return "석 "
    if value == 4:
        return "넉 "
    return _hybrid_character_count_reading(value)


def _length_character_unit_reading(value: int) -> str | None:
    special_reading = special_determiner_reading(value, "자")
    if special_reading is not None:
        return f"{special_reading} "
    return _hybrid_character_count_reading(value)


def _hybrid_character_count_reading(value: int) -> str | None:
    reading = (
        native_number_under_100(value)
        if 1 <= value <= HYBRID_COUNTER_THRESHOLD
        else _sino_or_large_integer_reading(value)
    )
    return f"{reading} " if reading is not None else None


def _sino_or_large_integer_reading(value: int) -> str | None:
    if value < 100:
        return _sino(value)
    try:
        return read_spaced_integer_value(value)
    except ValueError:
        return None


def _has_bounded_je_prefix(raw_text: str, number_start: int) -> bool:
    if number_start > 0 and raw_text[number_start - 1] == "제":
        prefix_start = number_start - 1
    elif (
        number_start > 1
        and raw_text[number_start - 1] == " "
        and raw_text[number_start - 2] == "제"
    ):
        prefix_start = number_start - 2
    else:
        return False
    return prefix_start == 0 or raw_text[prefix_start - 1].isspace()


def special_determiner_reading(value: int, counter: str) -> str | None:
    if not isinstance(value, int):
        raise TypeError("value must be int")
    if not isinstance(counter, str):
        raise TypeError("counter must be str")
    return _SPECIAL_DETERMINER_COUNTER_READINGS.get(counter, {}).get(value)


def _has_mixed_counter_path_tail(raw_text: str, counter_end: int) -> bool:
    return counter_end < len(raw_text) and raw_text[counter_end] == "/"


def _has_unsafe_large_unit_counter_tail(raw_text: str, counter_end: int) -> bool:
    if counter_end >= len(raw_text):
        return False
    tail = raw_text[counter_end:]
    first = tail[0]
    if first.isspace() or first in ",.!?)]};:":
        return False
    if not _is_complete_hangul(first):
        return True
    return not tail.startswith(_LARGE_UNIT_COUNTER_ATTACHED_TAILS)


def parse_counter_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "counter_noun":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        if candidate.metadata.get("full_counter_claim") is True:
            counter_span = candidate.metadata.get("counter_span")
            numeric_span = candidate.metadata.get("numeric_span")
            if not isinstance(counter_span, SourceSpan) or not isinstance(
                numeric_span, SourceSpan
            ):
                return None
            source_gap = raw_text[numeric_span.end : counter_span.start]
            counter = raw_text[counter_span.start : counter_span.end]
            return f"{reading}{source_gap}{counter}"
        return reading
    raw_number = raw_text[candidate.core_span.start : candidate.core_span.end]
    counter = candidate.metadata.get("counter")
    if not isinstance(counter, str):
        return None
    return counter_number_reading(raw_number, counter)


def counter_render_pieces(
    raw_text: str, candidate: SurfaceCandidate
) -> list[RenderPiece] | None:
    if (
        candidate.owner != "counter_noun"
        or candidate.metadata.get("full_counter_claim") is not True
    ):
        return None
    reading = candidate.metadata.get("reading")
    numeric_span = candidate.metadata.get("numeric_span")
    counter_span = candidate.metadata.get("counter_span")
    source_space_span = candidate.metadata.get("source_space_span")
    if (
        not isinstance(reading, str)
        or not isinstance(numeric_span, SourceSpan)
        or not isinstance(counter_span, SourceSpan)
        or (
            source_space_span is not None
            and not isinstance(source_space_span, SourceSpan)
        )
    ):
        return None

    generated_space = reading.endswith(" ")
    numeric_reading = reading[:-1] if generated_space else reading
    metadata = {"surface_type": candidate.surface_type}
    pieces = [
        RenderPiece(
            text=numeric_reading,
            provenance="GENERATED_READING",
            source_span=numeric_span,
            owner=candidate.owner,
            metadata=metadata,
        )
    ]
    if isinstance(source_space_span, SourceSpan):
        pieces.append(
            RenderPiece(
                text=raw_text[source_space_span.start : source_space_span.end],
                provenance="ORIGINAL_SPACE",
                source_span=source_space_span,
                owner=candidate.owner,
                metadata=metadata,
            )
        )
    elif generated_space:
        pieces.append(
            RenderPiece(
                text=" ",
                provenance="GENERATED_READING",
                source_span=counter_span,
                owner=candidate.owner,
                metadata=metadata,
            )
        )
    pieces.append(
        RenderPiece(
            text=raw_text[counter_span.start : counter_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=counter_span,
            owner=candidate.owner,
            metadata=metadata,
        )
    )
    return pieces


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
    raw_text: str,
    number_span: SourceSpan,
    counter_span: SourceSpan,
    *,
    allow_attached_korean_left: bool = False,
) -> bool:
    prev_char = raw_text[number_span.start - 1] if number_span.start > 0 else None
    next_char = raw_text[counter_span.end] if counter_span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if _is_complete_hangul(prev_char):
            if not allow_attached_korean_left:
                return False
            if not is_safe_mixed_integer_left_boundary(raw_text, number_span.start):
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
    "INTEGER_ONLY_SPECIAL_DETERMINER_UNITS",
    "DEFAULT_HYBRID_COUNTER_THRESHOLD",
    "NATIVE_COUNTERS",
    "NATIVE_ONLY_1_TO_99_COUNTERS",
    "PUBLIC_NUMBER_AMBIGUOUS_NUMBERS",
    "SINO_COUNTERS",
    "SPACELESS_COUNTERS",
    "SUPPORTED_COUNTERS",
    "counter_mode",
    "counter_number_reading",
    "counter_render_pieces",
    "is_emergency_ambiguous_number",
    "is_supported_counter",
    "native_number_under_100",
    "parse_counter_candidate",
    "scan_counter_candidates",
    "special_determiner_reading",
]
