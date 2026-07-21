from __future__ import annotations

import re

from engine.span_engine.counter import SPACELESS_COUNTERS
from engine.span_engine.counter import native_number_under_100
from engine.span_engine.date_time import (
    TIME_POSTPOSITIONS,
    clock_hour_reading,
    is_strong_time_like_colon,
)
from engine.span_engine.delimiters import (
    COLON_LIKE_DELIMITERS,
    RANGE_LIKE_DELIMITERS,
    is_colon_like,
    is_range_like,
    is_tilde_like,
)
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_fraction_digits
from engine.span_engine.signed_numeric import (
    SignProfile,
    SignedNumericCore,
    parse_signed_numeric_core,
    render_signed_numeric,
)
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.units import (
    SIMPLE_UNIT_READINGS,
    SPECIAL_UNIT_READINGS,
    range_compatible_unit_reading,
    range_compatible_units_by_length,
)

RANGE_SEPARATORS = frozenset({"~", "∼", "～", "〜"})
DATE_TIME_SHARED_SUFFIXES = frozenset({"년", "월", "일", "시", "분", "초"})
DURATION_SHARED_SUFFIXES = frozenset({"시간"})
PAGE_DOCUMENT_SUFFIXES = frozenset({"쪽", "장"})
KOREAN_RANGE_SUFFIXES = frozenset(
    {"월", "일", "년", "층", "호", "동", "원", "도", "시", "분", "초", "시간", "쪽", "장"}
)
HYPHEN_RANGE_COMPATIBLE_KOREAN_SUFFIX_READINGS = {
    "장": "장",
    "페이지": "페이지",
    "개": "개",
    "명": "명",
    "분": "분",
    "원": "원",
}
_SPACED_KOREAN_SUFFIXES = KOREAN_RANGE_SUFFIXES - SPACELESS_COUNTERS
_UNITS_BY_LENGTH = sorted(
    {**SIMPLE_UNIT_READINGS, **SPECIAL_UNIT_READINGS}, key=len, reverse=True
)
_UNIT_READINGS = {**SIMPLE_UNIT_READINGS, **SPECIAL_UNIT_READINGS}
_HYPHEN_RANGE_COMPATIBLE_KOREAN_SUFFIXES_BY_LENGTH = sorted(
    HYPHEN_RANGE_COMPATIBLE_KOREAN_SUFFIX_READINGS, key=len, reverse=True
)
COLON_SEMANTIC_PAIR_KEYWORDS = (
    "비율",
    "화면비",
    "종횡비",
    "희석",
    "축척",
    "세트스코어",
    "스코어",
    "점수",
    "승리",
    "패배",
    "무승부",
    "동점",
    "이겼다",
    "졌다",
    "비겼다",
    "완승",
    "압승",
    "역전승",
    "배율",
    "스케일",
    "전적",
    "세트",
    "경기",
    "게임",
    "매치",
    "대결",
)
_COLON_SEMANTIC_PAIR_KEYWORDS_BY_LENGTH = sorted(
    COLON_SEMANTIC_PAIR_KEYWORDS, key=len, reverse=True
)
_PREV_BLOCKERS = frozenset("+-.,~:/")
_PREV_SYMBOL_BLOCKERS = frozenset("$€£¥₩")
_SENTENCE_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", "…", "。", "，", "！", "？"})
_BROAD_RANGE_SPACED_TAILS = ("숫자범위", "범위", "구간")
_BROAD_RANGE_ATTACHED_TAILS = (
    "였고",
    "였지만",
    "였다",
    "입니다",
    "이다",
    "이고",
    "까지",
    "부터",
    "으로",
    "로",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "에서",
)
_BASIC_TILDE_DEFERRED_SUFFIXES = tuple(KOREAN_RANGE_SUFFIXES | {"만", "억", "조", "경"})
_COLON_PAIR_ATTACHED_TAILS = (
    "였고",
    "였지만",
    "였다",
    "입니다",
    "이다",
    "이고",
    "까지",
    "부터",
    "에게",
    "처럼",
    "으로",
    "에서",
    "로",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "와",
    "과",
    "도",
    "만",
    "다",
)
_COLON_PAIR_BLOCKED_PREV_WORDS = (
    "line",
    "case",
    "ver",
    "file",
    "code",
    "log",
    "id",
    "model",
    "영상",
    "재생시간",
    "타임라인",
    "라인",
    "케이스",
    "버전",
    "파일",
    "코드",
    "로그",
    "모델",
)


NumericDelimitedNumber = SignedNumericCore


def is_range_separator(ch: str) -> bool:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return ch in RANGE_SEPARATORS


def scan_range_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        left_start = index
        left_end = _consume_numeric_like(raw_text, left_start)
        if left_end >= len(raw_text) or not is_range_separator(raw_text[left_end]):
            index = max(left_end, index + 1)
            continue
        sep_index = left_end
        right_start = sep_index + 1
        right_end = _consume_numeric_like(raw_text, right_start)
        if right_end == right_start:
            index = left_end
            continue
        left = raw_text[left_start:left_end]
        right = raw_text[right_start:right_end]
        if not _valid_numbers(raw_text, left_start, right_end, left, right):
            index = right_end
            continue

        unit_candidate = _unit_candidate(
            raw_text, left_start, right_end, left, right
        )
        if unit_candidate is not None:
            candidates.append(unit_candidate)
            index = unit_candidate.full_span.end
            continue

        korean_suffix_candidate = _korean_suffix_candidate(
            raw_text, left_start, right_end, left, right
        )
        if korean_suffix_candidate is not None:
            candidates.append(korean_suffix_candidate)
            index = korean_suffix_candidate.full_span.end
            continue

        basic_candidate = _basic_candidate(raw_text, left_start, right_end, left, right)
        if basic_candidate is not None:
            candidates.append(basic_candidate)
        elif _has_unsafe_ascii_tail(raw_text, right_end):
            candidates.append(
                _preserve_candidate(
                    SourceSpan(left_start, _range_like_token_end(raw_text, right_end)),
                    "range_unsupported_tail_preserve",
                )
            )
        index = right_end
    return candidates


def scan_numeric_delimited_hyphen_range_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = _scan_invalid_tilde_numeric_range_preserve_candidates(raw_text)
    index = 0
    while index < len(raw_text):
        if not _can_start_numeric_delimited_number(raw_text[index]):
            index += 1
            continue
        left_start = index
        left_end = _consume_numeric_delimited_number_like(
            raw_text, left_start, allow_sign=True
        )
        delimiter_start = _consume_optional_inline_whitespace(raw_text, left_end)
        if (
            delimiter_start >= len(raw_text)
            or not _is_numeric_delimited_range_delimiter(raw_text[delimiter_start])
            or (
                delimiter_start != left_end
                and not is_tilde_like(raw_text[delimiter_start])
            )
        ):
            index = max(left_end, index + 1)
            continue
        delimiter = raw_text[delimiter_start]
        right_start = delimiter_start + 1
        if is_tilde_like(delimiter):
            right_start = _consume_optional_inline_whitespace(raw_text, right_start)
        right_end = _consume_numeric_delimited_number_like(
            raw_text, right_start, allow_sign=True
        )
        if right_end == right_start:
            index = delimiter_start + 1
            continue
        if right_end < len(raw_text) and _is_numeric_delimited_range_delimiter(raw_text[right_end]):
            index = right_end
            continue
        left = raw_text[left_start:left_end]
        right = raw_text[right_start:right_end]
        signed_like_range = left.startswith(("+", "-")) or right.startswith(("+", "-"))
        if (
            not signed_like_range
            and not is_range_like(delimiter)
            and not is_tilde_like(delimiter)
        ):
            index = right_end
            continue
        left_number = parse_numeric_delimited_number(left)
        right_number = parse_numeric_delimited_number(right)
        suffix_start = _consume_optional_inline_whitespace(raw_text, right_end)
        if is_tilde_like(delimiter) and (left_number is None or right_number is None):
            candidates.append(
                _preserve_candidate(
                    SourceSpan(left_start, _range_like_token_end(raw_text, suffix_start)),
                    "tilde_numeric_range_invalid_number_preserve",
                )
            )
            index = suffix_start
            continue
        signed_range = _is_signed_numeric_delimited_pair(left_number, right_number)
        if signed_like_range and (left_number is None or right_number is None):
            if is_tilde_like(delimiter):
                candidates.append(
                    _preserve_candidate(
                        SourceSpan(left_start, _range_like_token_end(raw_text, suffix_start)),
                        "signed_tilde_numeric_range_invalid_number_preserve",
                    )
                )
                index = suffix_start
                continue
            preserve_candidate = _signed_range_preserve_candidate(
                raw_text,
                left_start,
                suffix_start,
                "signed_numeric_delimited_range_invalid_number_preserve",
            )
            if preserve_candidate is not None:
                candidates.append(preserve_candidate)
                index = preserve_candidate.full_span.end
                continue
            index = right_end
            continue
        if signed_range and not is_tilde_like(delimiter):
            preserve_candidate = _signed_range_preserve_candidate(
                raw_text,
                left_start,
                suffix_start,
                "signed_numeric_delimited_range_disallowed_delimiter_preserve",
            )
            if preserve_candidate is not None:
                candidates.append(preserve_candidate)
                index = preserve_candidate.full_span.end
                continue
            index = right_end
            continue
        if not _valid_hyphen_range_numbers(
            raw_text, left_start, left_number, right_number, delimiter
        ):
            index = right_end
            continue

        unit_candidate = _hyphen_unit_candidate(
            raw_text, left_start, suffix_start, left_number, right_number, delimiter
        )
        if unit_candidate is not None:
            candidates.append(unit_candidate)
            index = unit_candidate.core_span.end
            continue
        korean_candidate = _hyphen_korean_suffix_candidate(
            raw_text,
            left_start,
            right_end,
            suffix_start,
            left_number,
            right_number,
            delimiter,
        )
        if korean_candidate is not None:
            candidates.append(korean_candidate)
            index = korean_candidate.full_span.end
            continue
        basic_tilde_candidate = _basic_tilde_numeric_delimited_candidate(
            raw_text,
            left_start,
            right_end,
            left_number,
            right_number,
            delimiter,
        )
        if basic_tilde_candidate is not None:
            candidates.append(basic_tilde_candidate)
            index = basic_tilde_candidate.full_span.end
            continue
        index = right_end
    return candidates


def scan_colon_semantic_pair_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _can_start_numeric_delimited_number(raw_text[index]):
            index += 1
            continue
        left_start = index
        if not _valid_colon_semantic_pair_left_boundary(raw_text, left_start):
            index += 1
            continue
        left_end = _consume_numeric_delimited_number_like(
            raw_text, left_start, allow_sign=True
        )
        if (
            left_end >= len(raw_text)
            or not is_colon_like(raw_text[left_end])
        ):
            index = max(left_end, index + 1)
            continue
        right_start = left_end + 1
        right_end = _consume_numeric_delimited_number_like(
            raw_text, right_start, allow_sign=True
        )
        if right_end == right_start:
            index = left_end + 1
            continue
        if right_end < len(raw_text) and is_colon_like(raw_text[right_end]):
            index = right_end
            continue
        span = SourceSpan(left_start, right_end)
        if not _valid_colon_semantic_pair_right_boundary(raw_text, span):
            index = right_end
            continue
        left = raw_text[left_start:left_end]
        right = raw_text[right_start:right_end]
        has_semantic_context = _has_colon_semantic_pair_context(raw_text, span)
        if _has_colon_pair_blocked_context(raw_text, span):
            candidates.append(
                _preserve_candidate(span, "colon_semantic_pair_context_preserve")
            )
            index = right_end
            continue
        if _is_raw_time_like_colon_pair(left, right):
            if (
                not has_semantic_context
                or _is_raw_strong_time_like_colon_pair(left, right)
            ):
                index = right_end
                continue
        if _has_explicit_invalid_time_context(raw_text, span, left, right):
            index = right_end
            continue
        left_number = parse_numeric_delimited_number(left)
        right_number = parse_numeric_delimited_number(right)
        if (
            left_number is None
            or right_number is None
            or len(left_number.integer_digits) > 8
            or len(right_number.integer_digits) > 8
            or (_is_time_like_colon_pair(left_number, right_number) and not has_semantic_context)
        ):
            candidates.append(
                _preserve_candidate(
                    span,
                    "colon_semantic_pair_invalid_number_preserve",
                )
            )
            index = right_end
            continue
        reading = _colon_semantic_pair_reading(
            raw_text, span, left_number, right_number
        )
        if reading is None:
            candidates.append(
                _preserve_candidate(
                    span,
                    "colon_semantic_pair_render_failed_preserve",
                )
            )
            index = right_end
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="colon_semantic_pair",
                surface_type="COLON_SEMANTIC_PAIR_SURFACE",
                reason=(
                    "colon_semantic_pair_explicit_context_gate"
                    if has_semantic_context
                    else "colon_semantic_pair_broad_numeric_gate"
                ),
                metadata={
                    "left": left,
                    "right": right,
                    "reading": reading,
                },
            )
        )
        index = right_end
    return candidates


def scan_multi_colon_numeric_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _can_start_colon_numeric_like_fragment(raw_text[index]):
            index += 1
            continue
        surface = _scan_multi_colon_numeric_like_surface(raw_text, index)
        if surface is None:
            index += 1
            continue
        span, raw_blocks = surface
        if span.start != index:
            index += 1
            continue
        block_count = len(raw_blocks)
        if block_count < 3:
            index = max(span.end, index + 1)
            continue
        if not _valid_multi_colon_boundary(raw_text, span):
            index = max(span.end, index + 1)
            continue
        if _has_multi_colon_blocked_context(raw_text, span):
            candidates.append(
                _preserve_candidate(span, "multi_colon_numeric_context_preserve")
            )
            index = span.end
            continue
        if block_count == 3 and _is_timecode_like_three_block(raw_blocks):
            candidates.append(
                _preserve_candidate(span, "multi_colon_timecode_like_preserve")
            )
            index = span.end
            continue
        if block_count > 8:
            candidates.append(
                _preserve_candidate(span, "multi_colon_numeric_too_many_blocks_preserve")
            )
            index = span.end
            continue
        numbers = [parse_numeric_delimited_number(raw) for raw in raw_blocks]
        if any(number is None for number in numbers):
            candidates.append(
                _preserve_candidate(span, "multi_colon_numeric_invalid_block_preserve")
            )
            index = span.end
            continue
        rendered = [
            render_numeric_delimited_number(number)
            for number in numbers
            if number is not None
        ]
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="multi_colon_numeric",
                surface_type="MULTI_COLON_NUMERIC_SURFACE",
                reason="multi_colon_numeric_dae_gate",
                metadata={
                    "blocks": raw_blocks,
                    "reading": " 대 ".join(rendered),
                },
            )
        )
        index = span.end
    return candidates


def parse_range_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner not in {
        "range",
        "range_with_unit",
        "colon_semantic_pair",
        "multi_colon_numeric",
    }:
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def parse_range_with_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "range_with_unit":
        return None
    return parse_range_candidate(raw_text, candidate)


def parse_range_with_korean_suffix_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "range":
        return None
    return parse_range_candidate(raw_text, candidate)


def hyphen_range_compatible_korean_suffix_reading(suffix: str) -> str | None:
    if not isinstance(suffix, str):
        raise TypeError("suffix must be str")
    return HYPHEN_RANGE_COMPATIBLE_KOREAN_SUFFIX_READINGS.get(suffix)


def hyphen_range_compatible_korean_suffixes_by_length() -> list[str]:
    return list(_HYPHEN_RANGE_COMPATIBLE_KOREAN_SUFFIXES_BY_LENGTH)


def _unit_candidate(
    raw_text: str, left_start: int, right_end: int, left: str, right: str
) -> SurfaceCandidate | None:
    for unit in _UNITS_BY_LENGTH:
        if not raw_text.startswith(unit, right_end):
            continue
        full_end = right_end + len(unit)
        full_span = SourceSpan(left_start, full_end)
        if not _valid_after_surface(raw_text, full_span):
            return _preserve_candidate(
                SourceSpan(left_start, _range_like_token_end(raw_text, full_end)),
                "range_with_unit_invalid_tail_preserve",
            )
        unit_reading = _UNIT_READINGS[unit]
        return SurfaceCandidate(
            core_span=full_span,
            full_span=full_span,
            owner="range_with_unit",
            surface_type="RANGE_WITH_UNIT_SURFACE",
            reason="range_with_unit_full_consume_gate",
            metadata={
                "left": left,
                "right": right,
                "unit": unit,
                "unit_reading": unit_reading,
                "reading": _range_reading(left, right, unit_reading=unit_reading),
            },
        )
    return None


def _hyphen_unit_candidate(
    raw_text: str,
    left_start: int,
    suffix_start: int,
    left: NumericDelimitedNumber,
    right: NumericDelimitedNumber,
    delimiter: str,
) -> SurfaceCandidate | None:
    for unit in range_compatible_units_by_length():
        if not raw_text.startswith(unit, suffix_start):
            continue
        full_end = suffix_start + len(unit)
        full_span = SourceSpan(left_start, full_end)
        if not _valid_after_surface(raw_text, full_span):
            return _preserve_candidate(
                SourceSpan(left_start, _range_like_token_end(raw_text, full_end)),
                "numeric_delimited_hyphen_range_with_unit_invalid_tail_preserve",
            )
        unit_reading = range_compatible_unit_reading(unit)
        if unit_reading is None:
            continue
        return SurfaceCandidate(
            core_span=full_span,
            full_span=full_span,
            owner="range_with_unit",
            surface_type="RANGE_WITH_UNIT_SURFACE",
            reason="numeric_delimited_hyphen_range_with_unit_gate",
            metadata={
                "left": left,
                "right": right,
                "unit": unit,
                "unit_reading": unit_reading,
                "reading": _range_reading(
                    left,
                    right,
                    unit_reading=unit_reading,
                    range_zero_style=is_tilde_like(delimiter),
                ),
            },
        )
    return None


def _hyphen_korean_suffix_candidate(
    raw_text: str,
    left_start: int,
    right_end: int,
    suffix_start: int,
    left: NumericDelimitedNumber,
    right: NumericDelimitedNumber,
    delimiter: str,
) -> SurfaceCandidate | None:
    for suffix in hyphen_range_compatible_korean_suffixes_by_length():
        if not raw_text.startswith(suffix, suffix_start):
            continue
        if delimiter in RANGE_SEPARATORS and (
            suffix in DATE_TIME_SHARED_SUFFIXES or suffix in DURATION_SHARED_SUFFIXES
        ):
            return None
        if delimiter in {"∼", "〜"} and suffix in PAGE_DOCUMENT_SUFFIXES:
            return None
        suffix_reading = hyphen_range_compatible_korean_suffix_reading(suffix)
        if suffix_reading is None:
            continue
        suffix_span = SourceSpan(suffix_start, suffix_start + len(suffix))
        if not _valid_after_korean_suffix(raw_text, suffix_span):
            return None
        core_end = suffix_start if suffix_start != right_end else right_end
        return SurfaceCandidate(
            core_span=SourceSpan(left_start, core_end),
            full_span=SourceSpan(left_start, suffix_span.end),
            owner="range",
            surface_type="RANGE_SURFACE",
            suffix_spans=[suffix_span],
            reason="numeric_delimited_hyphen_range_korean_suffix_gate",
            metadata={
                "left": left,
                "right": right,
                "suffix": suffix,
                "suffix_reading": suffix_reading,
                "suffix_span": suffix_span,
                "reading": _range_reading(
                    left, right, range_zero_style=is_tilde_like(delimiter)
                )
                + " ",
            },
        )
    return None


def _basic_tilde_numeric_delimited_candidate(
    raw_text: str,
    left_start: int,
    right_end: int,
    left: NumericDelimitedNumber,
    right: NumericDelimitedNumber,
    delimiter: str,
) -> SurfaceCandidate | None:
    if not is_tilde_like(delimiter):
        return None
    if raw_text.startswith(_BASIC_TILDE_DEFERRED_SUFFIXES, right_end):
        return None
    span = SourceSpan(left_start, right_end)
    if not _valid_after_basic_tilde_range(raw_text, span):
        return None
    reading = _range_reading(left, right, range_zero_style=True)
    if _needs_hangul_tail_space(raw_text, right_end, _BROAD_RANGE_ATTACHED_TAILS):
        reading += " "
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="range",
        surface_type="RANGE_SURFACE",
        reason="tilde_numeric_range_broad_gate",
        metadata={
            "left": left,
            "right": right,
            "reading": reading,
        },
    )


def _korean_suffix_candidate(
    raw_text: str, left_start: int, right_end: int, left: str, right: str
) -> SurfaceCandidate | None:
    for suffix in sorted(KOREAN_RANGE_SUFFIXES, key=len, reverse=True):
        if not raw_text.startswith(suffix, right_end):
            continue
        suffix_span = SourceSpan(right_end, right_end + len(suffix))
        if _is_unsupported_duration_range_suffix_tail(raw_text, suffix_span, suffix):
            return None
        if not _valid_after_korean_suffix(raw_text, suffix_span):
            return None
        core_span = SourceSpan(left_start, right_end)
        if suffix in DATE_TIME_SHARED_SUFFIXES:
            reading = _range_shared_suffix_reading(left, right, suffix)
        elif suffix in DURATION_SHARED_SUFFIXES:
            reading = _range_duration_suffix_reading(left, right, suffix)
        else:
            reading = _range_reading(left, right)
        if (
            suffix in _SPACED_KOREAN_SUFFIXES
            and suffix not in DATE_TIME_SHARED_SUFFIXES
            and suffix not in DURATION_SHARED_SUFFIXES
            and suffix not in PAGE_DOCUMENT_SUFFIXES
        ):
            reading += " "
        return SurfaceCandidate(
            core_span=core_span,
            full_span=SourceSpan(left_start, suffix_span.end),
            owner="range",
            surface_type="RANGE_SURFACE",
            suffix_spans=[suffix_span],
            reason="range_shared_korean_suffix_gate",
            metadata={
                "left": left,
                "right": right,
                "suffix": suffix,
                "suffix_span": suffix_span,
                "reading": reading,
            },
        )
    return None


def _basic_candidate(
    raw_text: str, left_start: int, right_end: int, left: str, right: str
) -> SurfaceCandidate | None:
    span = SourceSpan(left_start, right_end)
    if not _valid_after_basic_range(raw_text, span):
        return None
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="range",
        surface_type="RANGE_SURFACE",
        reason="range_full_consume_gate",
        metadata={"left": left, "right": right, "reading": _range_reading(left, right)},
    )


def _range_reading(
    left: str | NumericDelimitedNumber,
    right: str | NumericDelimitedNumber,
    unit_reading: str | None = None,
    *,
    range_zero_style: bool = False,
) -> str:
    reading = (
        f"{_numeric_delimited_or_numeric_like_reading(left, range_zero_style=range_zero_style)}"
        f"에서 {_numeric_delimited_or_numeric_like_reading(right, range_zero_style=range_zero_style)}"
    )
    if unit_reading is not None:
        reading += " " + unit_reading
    return reading


def _numeric_delimited_or_numeric_like_reading(
    raw: str | NumericDelimitedNumber,
    *,
    range_zero_style: bool = False,
) -> str:
    if isinstance(raw, NumericDelimitedNumber):
        if not range_zero_style:
            return render_numeric_delimited_number(raw)
        return _range_numeric_delimited_number_reading(raw)
    return _numeric_like_reading(raw)


def _range_numeric_delimited_number_reading(number: NumericDelimitedNumber) -> str:
    return render_numeric_delimited_number(number)


def _range_shared_suffix_reading(left: str, right: str, suffix: str) -> str:
    return (
        f"{_numeric_like_reading_with_suffix(left, suffix)}"
        f"에서 {_numeric_like_suffix_prefix_reading(right, suffix)}"
    )


def _range_duration_suffix_reading(left: str, right: str, suffix: str) -> str:
    left_reading = _duration_hour_prefix_reading(left)
    right_reading = _duration_hour_prefix_reading(right)
    return f"{left_reading} {suffix}에서 {right_reading} "


def _numeric_like_reading_with_suffix(raw: str, suffix: str) -> str:
    return _numeric_like_shared_suffix_part(raw, suffix, include_suffix=True)


def _numeric_like_suffix_prefix_reading(raw: str, suffix: str) -> str:
    return _numeric_like_shared_suffix_part(raw, suffix, include_suffix=False)


def _numeric_like_shared_suffix_part(
    raw: str, suffix: str, *, include_suffix: bool
) -> str:
    if suffix == "월":
        month_reading = _month_reading(raw)
        if month_reading is not None:
            return f"{month_reading}월" if include_suffix else month_reading
    if suffix == "시":
        hour = int(raw)
        reading = clock_hour_reading(hour)
        if reading is not None:
            return f"{reading} 시" if include_suffix else f"{reading} "
    reading = _numeric_like_reading(raw)
    return f"{reading}{suffix}" if include_suffix else reading


def _month_reading(raw: str) -> str | None:
    if raw == "6":
        return "유"
    if raw == "10":
        return "시"
    return None


def _duration_hour_prefix_reading(raw: str) -> str:
    integer_part, dot, fraction_part = raw.partition(".")
    if dot:
        return _numeric_like_reading(raw)
    value = int(integer_part)
    native = native_number_under_100(value) if 1 <= value <= 23 else None
    return native if native is not None else number_to_korean_under_10000(value)


def _consume_numeric_like(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    if (
        index < len(raw_text)
        and raw_text[index] == "."
        and index + 1 < len(raw_text)
        and _is_ascii_digit(raw_text[index + 1])
    ):
        index += 1
        while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
            index += 1
    return index


def _consume_numeric_delimited_number_like(
    raw_text: str, start: int, *, allow_sign: bool = False
) -> int:
    index = start
    if allow_sign and index < len(raw_text) and raw_text[index] in {"+", "-"}:
        index += 1
    while index < len(raw_text):
        if _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        if (
            raw_text[index] == ","
            and index + 1 < len(raw_text)
            and _is_ascii_digit(raw_text[index + 1])
        ):
            index += 1
            continue
        break
    if (
        index < len(raw_text)
        and raw_text[index] == "."
        and index + 1 < len(raw_text)
        and _is_ascii_digit(raw_text[index + 1])
    ):
        index += 1
        while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
            index += 1
    return index


def _can_start_numeric_delimited_number(ch: str) -> bool:
    return _is_ascii_digit(ch) or ch in {"+", "-"}


def _can_start_colon_numeric_like_fragment(ch: str) -> bool:
    return _is_ascii_digit(ch) or ch in {"+", "-", "."}


def _scan_multi_colon_numeric_like_surface(
    raw_text: str, start: int
) -> tuple[SourceSpan, list[str]] | None:
    blocks: list[str] = []
    index = start
    while True:
        block_start = index
        block_end = _consume_colon_numeric_like_fragment(raw_text, block_start)
        if block_end == block_start:
            return None
        blocks.append(raw_text[block_start:block_end])
        if block_end >= len(raw_text) or not is_colon_like(raw_text[block_end]):
            return SourceSpan(start, block_end), blocks
        index = block_end + 1
        if index >= len(raw_text):
            return SourceSpan(start, block_end + 1), blocks + [""]


def _consume_colon_numeric_like_fragment(raw_text: str, start: int) -> int:
    index = start
    if index < len(raw_text) and raw_text[index] in {"+", "-"}:
        index += 1
    while index < len(raw_text):
        char = raw_text[index]
        if _is_ascii_digit(char):
            index += 1
            continue
        if (
            char == ","
            and index + 1 < len(raw_text)
            and _is_ascii_digit(raw_text[index + 1])
        ):
            index += 1
            continue
        if char == "." and (
            (index + 1 < len(raw_text) and _is_ascii_digit(raw_text[index + 1]))
            or (index + 1 < len(raw_text) and is_colon_like(raw_text[index + 1]))
        ):
            index += 1
            continue
        break
    return index


def _is_numeric_delimited_range_delimiter(ch: str) -> bool:
    return is_range_like(ch) or is_tilde_like(ch)


def _consume_optional_inline_whitespace(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index] in {" ", "\t"}:
        index += 1
    return index


def _scan_invalid_tilde_numeric_range_preserve_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in {"+", "-", "."} and not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        if _is_inside_numeric_like_fragment(raw_text, index):
            index += 1
            continue
        end = index
        seen_tilde = False
        while end < len(raw_text):
            char = raw_text[end]
            if char in {"+", "-", ".", ","} or _is_ascii_digit(char):
                end += 1
                continue
            if char in {" ", "\t"}:
                whitespace_end = _consume_optional_inline_whitespace(raw_text, end)
                if whitespace_end < len(raw_text) and (
                    is_tilde_like(raw_text[whitespace_end])
                    or raw_text[whitespace_end] in {"+", "-"}
                    or _is_ascii_digit(raw_text[whitespace_end])
                ):
                    end = whitespace_end
                    continue
                break
            if is_tilde_like(char):
                seen_tilde = True
                end += 1
                continue
            if char == "?" and seen_tilde:
                end += 1
                continue
            break
        if not seen_tilde:
            index += 1
            continue
        end = _trim_valid_sentence_punctuation_from_invalid_tilde_raw(
            raw_text, index, end
        )
        raw = raw_text[index:end]
        if raw.count("~") + raw.count("～") + raw.count("∼") + raw.count("〜") != 1:
            index = end
            continue
        delimiter_index = next(
            offset for offset, char in enumerate(raw) if is_tilde_like(char)
        )
        left = raw[:delimiter_index].strip(" \t")
        right = raw[delimiter_index + 1 :].strip(" \t")
        if parse_numeric_delimited_number(left) is not None and parse_numeric_delimited_number(right) is not None:
            index += 1
            continue
        span = SourceSpan(index, end)
        if _valid_invalid_tilde_preserve_boundary(raw_text, span):
            candidates.append(
                _preserve_candidate(span, "tilde_numeric_range_invalid_number_preserve")
            )
        index = end
    return candidates


def _is_inside_numeric_like_fragment(raw_text: str, index: int) -> bool:
    if index <= 0:
        return False
    prev_char = raw_text[index - 1]
    return prev_char in {"+", "-", ".", ","} or _is_ascii_digit(prev_char)


def _trim_valid_sentence_punctuation_from_invalid_tilde_raw(
    raw_text: str, start: int, end: int
) -> int:
    if end <= start or raw_text[end - 1] != ".":
        return end
    trimmed = raw_text[start : end - 1]
    delimiter_count = sum(1 for char in trimmed if is_tilde_like(char))
    if delimiter_count != 1:
        return end
    delimiter_index = next(
        offset for offset, char in enumerate(trimmed) if is_tilde_like(char)
    )
    left = trimmed[:delimiter_index].strip(" \t")
    right = trimmed[delimiter_index + 1 :].strip(" \t")
    if (
        parse_numeric_delimited_number(left) is not None
        and parse_numeric_delimited_number(right) is not None
    ):
        return end - 1
    return end


def _valid_invalid_tilde_preserve_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in {"_", "/", ":"}:
            return False
    if next_char is None:
        return True
    if next_char.isspace() or next_char in _SENTENCE_PUNCTUATION:
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return raw_text.startswith(_BROAD_RANGE_ATTACHED_TAILS + _BROAD_RANGE_SPACED_TAILS, span.end)
    return not (next_char.isascii() and next_char.isalnum())


def _valid_numbers(
    raw_text: str, left_start: int, right_end: int, left: str, right: str
) -> bool:
    if not _valid_numeric_like(left) or not _valid_numeric_like(right):
        return False
    if int(left.split(".", 1)[0]) > 9999 or int(right.split(".", 1)[0]) > 9999:
        return False
    prev_char = raw_text[left_start - 1] if left_start > 0 else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
        if prev_char in _PREV_SYMBOL_BLOCKERS:
            return False
    if right_end < len(raw_text) and raw_text[right_end] in RANGE_SEPARATORS:
        return False
    return True


def _valid_hyphen_range_numbers(
    raw_text: str,
    left_start: int,
    left: NumericDelimitedNumber | None,
    right: NumericDelimitedNumber | None,
    delimiter: str,
) -> bool:
    if left is None or right is None:
        return False
    if _is_signed_numeric_delimited_pair(left, right) and not is_tilde_like(delimiter):
        return False
    prev_char = raw_text[left_start - 1] if left_start > 0 else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in (
            {"_", "/", ".", "∼"} | COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS
        ):
            return False
        if prev_char in _PREV_SYMBOL_BLOCKERS:
            return False
    return True


def _is_signed_numeric_delimited_pair(
    left: NumericDelimitedNumber | None, right: NumericDelimitedNumber | None
) -> bool:
    return (left is not None and left.sign is not None) or (
        right is not None and right.sign is not None
    )


def _signed_range_preserve_candidate(
    raw_text: str,
    left_start: int,
    suffix_start: int,
    reason: str,
) -> SurfaceCandidate | None:
    for unit in range_compatible_units_by_length():
        if raw_text.startswith(unit, suffix_start):
            return _preserve_candidate(
                SourceSpan(left_start, suffix_start + len(unit)),
                reason,
            )
    for suffix in hyphen_range_compatible_korean_suffixes_by_length():
        if raw_text.startswith(suffix, suffix_start):
            return _preserve_candidate(
                SourceSpan(left_start, suffix_start + len(suffix)),
                reason,
            )
    return None


def _valid_colon_semantic_pair_left_boundary(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if "\uac00" <= prev_char <= "\ud7a3":
        return False
    return prev_char not in (
        {"_", "+", "/", ".", ",", "∼"} | COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS
    )


def _valid_colon_semantic_pair_right_boundary(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        if next_char == "." and next_next is not None and is_colon_like(next_next):
            return False
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    return False


def _valid_multi_colon_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in {"_", "/", ".", "∼"}:
            return False
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in {".", ",", "!", "?", ";"}:
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    return False


def _has_multi_colon_blocked_context(raw_text: str, span: SourceSpan) -> bool:
    prev_text = raw_text[: span.start].rstrip()
    if not prev_text:
        return False
    lowered = prev_text.lower()
    blocked_ascii = (
        "version",
        "ver",
        "line",
        "case",
        "code",
        "log",
        "id",
        "model",
    )
    if any(_text_endswith_ascii_word(lowered, word) for word in blocked_ascii):
        return True
    blocked_korean = (
        "버전",
        "라인",
        "케이스",
        "코드",
        "로그",
        "모델",
        "문서",
        "참조",
        "요한복음",
        "창세기",
        "시편",
    )
    return any(prev_text.endswith(word) for word in blocked_korean)


def _text_endswith_ascii_word(text: str, word: str) -> bool:
    if not text.endswith(word):
        return False
    before_index = len(text) - len(word)
    prev_char = text[before_index - 1] if before_index > 0 else None
    return prev_char is None or not (prev_char.isascii() and prev_char.isalnum())


def _is_timecode_like_three_block(raw_blocks: list[str]) -> bool:
    if len(raw_blocks) != 3:
        return False
    hour, minute, second = raw_blocks
    if hour.startswith(("+", "-")):
        hour = hour[1:]
    if not hour.isdigit() or not (1 <= len(hour) <= 2):
        return False
    if not _is_two_digit_00_to_59(minute):
        return False
    second_integer, dot, fraction = second.partition(".")
    if not _is_two_digit_00_to_59(second_integer):
        return False
    if dot and (not fraction or not _is_ascii_digits(fraction)):
        return False
    return True


def _is_two_digit_00_to_59(raw: str) -> bool:
    return len(raw) == 2 and raw.isdigit() and int(raw) <= 59


def parse_numeric_delimited_number(raw: str) -> NumericDelimitedNumber | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return parse_signed_numeric_core(
        raw,
        minus_aliases=frozenset({"-"}),
    )


def render_numeric_delimited_number(number: NumericDelimitedNumber) -> str:
    if not isinstance(number, NumericDelimitedNumber):
        raise TypeError("number must be NumericDelimitedNumber")
    reading = render_signed_numeric(
        number,
        sign_profile=SignProfile.DEFAULT,
        spaced_integer=True,
    )
    if reading is None:
        raise ValueError("invalid numeric-delimited number")
    return reading


def _is_time_like_colon_pair(
    left: NumericDelimitedNumber, right: NumericDelimitedNumber
) -> bool:
    if left.has_decimal or right.has_decimal:
        return False
    if "," in left.raw or "," in right.raw:
        return False
    if right.sign is not None:
        return False
    if len(right.raw) != 2 or not right.raw.isdigit():
        return False
    return 0 <= int(left.integer_digits) <= 24 and int(right.raw) <= 59


def _is_raw_time_like_colon_pair(left: str, right: str) -> bool:
    left_unsigned = left[1:] if left.startswith(("+", "-")) else left
    if "." in left_unsigned or "." in right or "," in left_unsigned or "," in right:
        return False
    if not left_unsigned.isdigit() or not right.isdigit():
        return False
    if not (1 <= len(left_unsigned) <= 2):
        return False
    if len(right) != 2:
        return False
    return 0 <= int(left_unsigned) <= 24 and 0 <= int(right) <= 59


def _is_raw_strong_time_like_colon_pair(left: str, right: str) -> bool:
    left_unsigned = left[1:] if left.startswith(("+", "-")) else left
    return is_strong_time_like_colon(left_unsigned, right)


def _has_explicit_invalid_time_context(
    raw_text: str, span: SourceSpan, left: str, right: str
) -> bool:
    left_unsigned = left[1:] if left.startswith(("+", "-")) else left
    if "." in left_unsigned or "." in right or "," in left_unsigned or "," in right:
        return False
    if not left_unsigned.isdigit() or not right.isdigit() or len(right) != 2:
        return False
    next_text = raw_text[span.end :]
    return next_text.startswith(TIME_POSTPOSITIONS)


def _has_colon_pair_blocked_context(raw_text: str, span: SourceSpan) -> bool:
    prev_text = raw_text[: span.start].rstrip()
    if not prev_text:
        return False
    lowered = prev_text.lower()
    for word in _COLON_PAIR_BLOCKED_PREV_WORDS:
        haystack = lowered if word.isascii() else prev_text
        needle = word.lower() if word.isascii() else word
        if _text_endswith_ascii_word(haystack, needle) if word.isascii() else haystack.endswith(needle):
            return True
    return False


def _has_colon_semantic_pair_context(raw_text: str, span: SourceSpan) -> bool:
    prev_text = raw_text[: span.start].rstrip()
    next_text = raw_text[span.end :]
    if _text_endswith_semantic_pair_keyword(prev_text):
        return True
    compact_next = next_text.lstrip()
    if _text_startswith_semantic_pair_keyword(compact_next):
        return True
    for particle in ("으로", "로", "의"):
        if compact_next.startswith(particle):
            after_particle = compact_next[len(particle) :].lstrip()
            return _text_startswith_semantic_pair_keyword(after_particle)
    return False


def _text_endswith_semantic_pair_keyword(text: str) -> bool:
    for keyword in _COLON_SEMANTIC_PAIR_KEYWORDS_BY_LENGTH:
        if not text.endswith(keyword):
            continue
        before_index = len(text) - len(keyword)
        prev_char = text[before_index - 1] if before_index > 0 else None
        return _valid_semantic_pair_keyword_left_boundary(prev_char)
    return False


def _text_startswith_semantic_pair_keyword(text: str) -> bool:
    for keyword in _COLON_SEMANTIC_PAIR_KEYWORDS_BY_LENGTH:
        if not text.startswith(keyword):
            continue
        next_char = text[len(keyword)] if len(keyword) < len(text) else None
        return _valid_semantic_pair_keyword_right_boundary(next_char)
    return False


def _valid_semantic_pair_keyword_left_boundary(prev_char: str | None) -> bool:
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    return not ("\uac00" <= prev_char <= "\ud7a3")


def _valid_semantic_pair_keyword_right_boundary(next_char: str | None) -> bool:
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in {".", ",", "!", "?", ";"}:
        return True
    return not (next_char.isascii() and next_char.isalnum())


def _colon_semantic_pair_reading(
    raw_text: str,
    span: SourceSpan,
    left: NumericDelimitedNumber,
    right: NumericDelimitedNumber,
) -> str:
    reading = (
        f"{render_numeric_delimited_number(left)} 대 "
        f"{render_numeric_delimited_number(right)}"
    )
    if _needs_hangul_tail_space(raw_text, span.end, _COLON_PAIR_ATTACHED_TAILS):
        reading += " "
    return reading


def _needs_hangul_tail_space(
    raw_text: str, tail_start: int, attached_tails: tuple[str, ...]
) -> bool:
    next_char = raw_text[tail_start] if tail_start < len(raw_text) else None
    if next_char is None or not ("가" <= next_char <= "힣"):
        return False
    return not _has_attached_tail(raw_text, tail_start, attached_tails)


def _has_attached_tail(
    raw_text: str, tail_start: int, attached_tails: tuple[str, ...]
) -> bool:
    for tail in attached_tails:
        if not raw_text.startswith(tail, tail_start):
            continue
        if len(tail) > 1:
            return True
        after = tail_start + len(tail)
        return after == len(raw_text) or not (
            "가" <= raw_text[after] <= "힣"
        )
    return False


def _has_leading_zero(raw: str) -> bool:
    return len(raw) > 1 and raw.startswith("0")


def _valid_numeric_like(raw: str) -> bool:
    if raw.count(".") > 1:
        return False
    integer_part, dot, fraction_part = raw.partition(".")
    if not _is_ascii_digits(integer_part):
        return False
    if _has_leading_zero(integer_part) and integer_part != "0":
        return False
    if dot and not _is_ascii_digits(fraction_part):
        return False
    return True


def _numeric_like_reading(raw: str) -> str:
    integer_part, dot, fraction_part = raw.partition(".")
    reading = number_to_korean_under_10000(int(integer_part))
    if dot:
        reading += "쩜" + read_decimal_fraction_digits(fraction_part)
    return reading


def _valid_after_surface(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        if next_char == "." and next_next is not None and _is_ascii_digit(next_next):
            return False
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    if next_char in {"은", "는", "을", "를", "이", "가", "로", "과", "와", "도"}:
        return True
    return False


def _has_unsafe_ascii_tail(raw_text: str, start: int) -> bool:
    return start < len(raw_text) and raw_text[start].isascii() and raw_text[start].isalpha()


def _range_like_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if char.isascii() and char.isalnum():
            index += 1
            continue
        if char in {".", "_"}:
            index += 1
            continue
        break
    return index


def _preserve_candidate(span: SourceSpan, reason: str) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="RANGE_PRESERVE_SURFACE",
        reason=reason,
    )


def _valid_after_basic_range(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        if next_char == ".":
            next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
            if next_next is not None and _is_ascii_digit(next_next):
                return False
        return True
    if raw_text.startswith("이다", span.end):
        after = span.end + len("이다")
        return after == len(raw_text) or not ("\uac00" <= raw_text[after] <= "\ud7a3")
    if next_char in {"은", "는", "을", "를", "이", "가", "로", "과", "와", "도"}:
        after = span.end + len(next_char)
        return after == len(raw_text) or not ("\uac00" <= raw_text[after] <= "\ud7a3")
    return False


def _valid_after_basic_tilde_range(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        if next_char == ".":
            next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
            if next_next is not None and _is_ascii_digit(next_next):
                return False
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    return False


def _valid_after_korean_suffix(raw_text: str, suffix_span: SourceSpan) -> bool:
    next_char = raw_text[suffix_span.end] if suffix_span.end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    return False


def _is_unsupported_duration_range_suffix_tail(
    raw_text: str, suffix_span: SourceSpan, suffix: str
) -> bool:
    next_char = raw_text[suffix_span.end] if suffix_span.end < len(raw_text) else None
    return suffix in {"시", "분", "초"} and next_char == "간"


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


__all__ = [
    "COLON_SEMANTIC_PAIR_KEYWORDS",
    "HYPHEN_RANGE_COMPATIBLE_KOREAN_SUFFIX_READINGS",
    "KOREAN_RANGE_SUFFIXES",
    "DATE_TIME_SHARED_SUFFIXES",
    "NumericDelimitedNumber",
    "PAGE_DOCUMENT_SUFFIXES",
    "RANGE_SEPARATORS",
    "hyphen_range_compatible_korean_suffix_reading",
    "hyphen_range_compatible_korean_suffixes_by_length",
    "is_range_separator",
    "parse_numeric_delimited_number",
    "parse_range_candidate",
    "parse_range_with_korean_suffix_candidate",
    "parse_range_with_unit_candidate",
    "render_numeric_delimited_number",
    "scan_colon_semantic_pair_candidates",
    "scan_multi_colon_numeric_candidates",
    "scan_numeric_delimited_hyphen_range_candidates",
    "scan_range_candidates",
]
