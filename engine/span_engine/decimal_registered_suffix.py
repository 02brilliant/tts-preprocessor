from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import SUPPORTED_COUNTERS
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_text
from engine.span_engine.numeric_suffix import NUMERIC_SUFFIXES
from engine.span_engine.span_guards import (
    is_decimal_like_url_or_path_context,
    span_overlaps_excluded_ranges,
)

_DECIMAL_RE = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)\.\d+")
_APPROVED_DURATION_SUFFIXES = frozenset({"주"})
REGISTERED_DECIMAL_SUFFIXES = (
    frozenset(SUPPORTED_COUNTERS)
    | frozenset(NUMERIC_SUFFIXES)
    | _APPROVED_DURATION_SUFFIXES
)
_ORDERED_SUFFIXES = sorted(REGISTERED_DECIMAL_SUFFIXES, key=len, reverse=True)
_PREV_BLOCKERS = frozenset("+-.,~:/_")
_SAFE_RIGHT_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", ")", "]", "}"})
_ATTACHED_KOREAN_TAILS = (
    "였습니다",
    "이었습니다",
    "이었고",
    "였지만",
    "였으며",
    "였고",
    "였다",
    "입니다",
    "이다",
    "이고",
    "간",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "에게",
    "으로",
    "로",
    "와",
    "과",
    "도",
    "만",
    "부터",
    "까지",
    "처럼",
    "마다",
    "씩",
    "짜리",
)


def scan_decimal_registered_suffix_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = _scan_malformed_decimal_suffix_preserves(
        raw_text, excluded_ranges
    )
    for match in _DECIMAL_RE.finditer(raw_text):
        decimal_span = SourceSpan(match.start(), match.end())
        if span_overlaps_excluded_ranges(decimal_span, excluded_ranges):
            continue
        if is_decimal_like_url_or_path_context(raw_text, decimal_span):
            continue
        if not _valid_left_boundary(raw_text, decimal_span.start):
            continue
        reading = read_decimal_text(match.group(0))
        if reading is None:
            continue
        candidate = _candidate_at_suffix(raw_text, decimal_span, reading)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def parse_decimal_registered_suffix_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "decimal_registered_suffix":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _candidate_at_suffix(
    raw_text: str, decimal_span: SourceSpan, reading: str
) -> SurfaceCandidate | None:
    suffix_start = decimal_span.end
    for suffix in _ORDERED_SUFFIXES:
        if not raw_text.startswith(suffix, suffix_start):
            continue
        suffix_end = suffix_start + len(suffix)
        if not _suffix_boundary_is_safe(raw_text, suffix_end):
            return _preserve_candidate(
                SourceSpan(
                    decimal_span.start,
                    _registered_suffix_like_token_end(raw_text, suffix_end),
                ),
                "decimal_registered_suffix_unsafe_tail_preserve",
            )
        return SurfaceCandidate(
            core_span=decimal_span,
            full_span=SourceSpan(decimal_span.start, suffix_end),
            owner="decimal_registered_suffix",
            surface_type="DECIMAL_REGISTERED_SUFFIX_SURFACE",
            suffix_spans=[SourceSpan(suffix_start, suffix_end)],
            reason="decimal_registered_suffix_gate",
            metadata={
                "number": raw_text[decimal_span.start : decimal_span.end],
                "suffix": suffix,
                "suffix_span": SourceSpan(suffix_start, suffix_end),
                "reading": f"{reading} ",
            },
        )
    return None


def _scan_malformed_decimal_suffix_preserves(
    raw_text: str, excluded_ranges: list[BracketRange]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (_is_ascii_digit(raw_text[index]) or raw_text[index] == "."):
            index += 1
            continue
        numeric_start = index
        numeric_end = _consume_decimal_like_surface(raw_text, numeric_start)
        if numeric_end == numeric_start:
            index += 1
            continue
        raw_number = raw_text[numeric_start:numeric_end]
        if "." not in raw_number:
            index = numeric_end
            continue
        number_span = SourceSpan(numeric_start, numeric_end)
        if span_overlaps_excluded_ranges(number_span, excluded_ranges):
            index = numeric_end
            continue
        if is_decimal_like_url_or_path_context(raw_text, number_span):
            index = numeric_end
            continue
        if not _valid_left_boundary(raw_text, numeric_start):
            index = numeric_end
            continue
        suffix = _registered_suffix_at(raw_text, numeric_end)
        if suffix is None:
            index = numeric_end
            continue
        suffix_start, suffix_end = suffix
        if read_decimal_text(raw_number) is not None and _suffix_boundary_is_safe(
            raw_text, suffix_end
        ):
            index = numeric_end
            continue
        candidates.append(
            _preserve_candidate(
                SourceSpan(
                    numeric_start,
                    _registered_suffix_like_token_end(raw_text, suffix_end),
                ),
                "malformed_decimal_registered_suffix_preserve",
            )
        )
        index = suffix_end
    return candidates


def _registered_suffix_at(raw_text: str, numeric_end: int) -> tuple[int, int] | None:
    suffix_start = numeric_end
    for suffix in _ORDERED_SUFFIXES:
        if raw_text.startswith(suffix, suffix_start):
            return suffix_start, suffix_start + len(suffix)
    return None


def _valid_left_boundary(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if "\uac00" <= prev_char <= "\ud7a3":
        return False
    return prev_char not in _PREV_BLOCKERS


def _suffix_boundary_is_safe(raw_text: str, suffix_end: int) -> bool:
    next_char = raw_text[suffix_end] if suffix_end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace() or next_char in _SAFE_RIGHT_PUNCTUATION:
        return True
    if next_char.isascii():
        return False
    if "\uac00" <= next_char <= "\ud7a3":
        return raw_text.startswith(_ATTACHED_KOREAN_TAILS, suffix_end)
    return True


def _registered_suffix_like_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if char.isspace() or char in _SAFE_RIGHT_PUNCTUATION:
            break
        if char in {"/", "_"}:
            index += 1
            while index < len(raw_text):
                tail_char = raw_text[index]
                if tail_char.isspace() or tail_char in _SAFE_RIGHT_PUNCTUATION:
                    break
                index += 1
            break
        index += 1
    return index


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _consume_decimal_like_surface(raw_text: str, start: int) -> int:
    index = start
    saw_digit = False
    while index < len(raw_text):
        char = raw_text[index]
        if _is_ascii_digit(char):
            saw_digit = True
            index += 1
            continue
        if char in {",", "."}:
            index += 1
            continue
        break
    return index if saw_digit else start


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _preserve_candidate(span: SourceSpan, reason: str) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="DECIMAL_REGISTERED_SUFFIX_PRESERVE_SURFACE",
        reason=reason,
    )


__all__ = [
    "REGISTERED_DECIMAL_SUFFIXES",
    "parse_decimal_registered_suffix_candidate",
    "scan_decimal_registered_suffix_candidates",
]
