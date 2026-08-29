from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import native_number_under_100
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    read_fraction_text,
    read_number_text,
    read_sino_time_suffix_number_text,
)
from engine.span_engine.sign_aliases import (
    MINUS_SIGN_ALIASES,
    PLUS_SIGN,
    is_signed_numeric_sign,
)
from engine.span_engine.numeric_suffix import has_ordinal_je_prefix
from engine.span_engine.signed_numeric import (
    SignProfile,
    apply_sign_profile,
    parse_sign_surface,
)
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY

_INTEGER_RE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_DECIMAL_RE = rf"{_INTEGER_RE}\.\d+"
_FRACTION_RE = rf"{_INTEGER_RE}/{_INTEGER_RE}"
_NUMBER_RE = rf"(?:{_FRACTION_RE}|{_DECIMAL_RE}|{_INTEGER_RE})"
_SIGN_RE = re.escape("".join(sorted({PLUS_SIGN, *MINUS_SIGN_ALIASES})))
_SIGNED_NUMBER_RE = rf"[{_SIGN_RE}]?{_NUMBER_RE}"
_DURATION_RE = re.compile(
    rf"(?P<hour>{_SIGNED_NUMBER_RE})시간(?P<space>\s*)(?P<minute>{_SIGNED_NUMBER_RE})분|"
    rf"(?P<hour_only>{_SIGNED_NUMBER_RE})시간|"
    rf"(?P<minute_only>{_SIGNED_NUMBER_RE})분"
)
_YEAR_PERIOD_RE = re.compile(rf"(?P<year>{_INTEGER_RE})년간")
_PREV_BLOCKERS = frozenset("+.,~:/_")
_MINUTE_DURATION_NEXT_ANCHORS = (
    "뒤",
    "전",
    "동안",
    "이내",
    "이상",
    "이하",
    "소요",
    "부터",
    "까지",
)
_MINUTE_DURATION_PREV_ANCHORS = (
    "소요 시간",
    "소요 시간은",
    "소요 시간는",
    "소요 시간의",
)


def scan_duration_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    candidates.extend(_scan_year_period_candidates(raw_text, excluded_ranges))
    for match in _DURATION_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if not _valid_boundary(raw_text, span):
            continue
        if _duration_has_je_prefix(match):
            continue
        if match.group("hour") is not None:
            hour = match.group("hour")
            minute = match.group("minute")
            if not _valid_unary_sign_left_boundary(raw_text, match.start("hour")):
                continue
            if not _valid_unary_sign_left_boundary(raw_text, match.start("minute")):
                hour_reading = _duration_amount_reading(hour, "시간")
                if hour_reading is None:
                    continue
                hour_full_end = match.end("hour") + len("시간")
                candidates.append(
                    _duration_candidate(
                        match.start("hour"),
                        match.end("hour"),
                        SourceSpan(match.start("hour"), hour_full_end),
                        f"{hour_reading}{SPOKEN_NUMERIC_BOUNDARY}",
                        "duration_hour_numeric_gate",
                    )
                )
                continue
            hour_reading = _duration_amount_reading(hour, "시간")
            minute_reading = _duration_amount_reading(minute, "분")
            if hour_reading is None or minute_reading is None:
                continue
            candidates.append(
                _duration_candidate(
                    match.start("hour"),
                    match.end("hour"),
                    span,
                    f"{hour_reading}{SPOKEN_NUMERIC_BOUNDARY}",
                    "duration_hour_numeric_gate",
                )
            )
            candidates.append(
                _duration_candidate(
                    match.start("minute"),
                    match.end("minute"),
                    span,
                    f"{' ' if match.group('space') == '' else ''}{minute_reading}",
                    "duration_minute_numeric_gate",
                )
            )
            continue
        elif match.group("hour_only") is not None:
            if not _valid_unary_sign_left_boundary(raw_text, match.start("hour_only")):
                continue
            hour = match.group("hour_only")
            hour_reading = _duration_amount_reading(hour, "시간")
            if hour_reading is None:
                continue
            candidates.append(
                _duration_candidate(
                    match.start("hour_only"),
                    match.end("hour_only"),
                    span,
                    f"{hour_reading}{SPOKEN_NUMERIC_BOUNDARY}",
                    "duration_hour_numeric_gate",
                )
            )
            continue
        else:
            if not _has_explicit_minute_duration_context(raw_text, span):
                continue
            if not _valid_unary_sign_left_boundary(raw_text, match.start("minute_only")):
                continue
            minute = match.group("minute_only")
            minute_reading = _duration_amount_reading(minute, "분")
            if minute_reading is None:
                continue
            candidates.append(
                _duration_candidate(
                    match.start("minute_only"),
                    match.end("minute_only"),
                    span,
                    minute_reading,
                    "duration_minute_numeric_gate",
                )
            )
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def _has_explicit_minute_duration_context(
    raw_text: str, span: SourceSpan
) -> bool:
    previous = raw_text[: span.start].rstrip()
    following = raw_text[span.end :].lstrip()
    return any(previous.endswith(anchor) for anchor in _MINUTE_DURATION_PREV_ANCHORS) or any(
        following.startswith(anchor) for anchor in _MINUTE_DURATION_NEXT_ANCHORS
    )


def parse_duration_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "duration":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _scan_year_period_candidates(
    raw_text: str, excluded_ranges: list[BracketRange]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _YEAR_PERIOD_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if not _valid_year_period_left_boundary(raw_text, span):
            continue
        if _has_year_period_unsafe_tail(raw_text, span.end):
            candidates.append(
                SurfaceCandidate(
                    core_span=SourceSpan(match.start(), _year_period_token_end(raw_text, span.end)),
                    full_span=SourceSpan(match.start(), _year_period_token_end(raw_text, span.end)),
                    owner="preserve",
                    surface_type="DURATION_PRESERVE_SURFACE",
                    reason="year_period_unsafe_tail_preserve",
                )
            )
            continue
        year = match.group("year")
        year_reading = _duration_amount_reading(year, "년")
        if year_reading is None:
            continue
        candidates.append(
            _duration_candidate(
                match.start("year"),
                match.end("year"),
                span,
                f"{year_reading}{SPOKEN_NUMERIC_BOUNDARY}",
                "duration_year_period_numeric_gate",
            )
        )
    return candidates


def _valid_year_period_left_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if "\uac00" <= prev_char <= "\ud7a3":
        return False
    if prev_char in _PREV_BLOCKERS:
        return False
    if prev_char == "-" and raw_text[span.start] != "-":
        return False
    return True


def _has_year_period_unsafe_tail(raw_text: str, end: int) -> bool:
    next_char = raw_text[end] if end < len(raw_text) else None
    if next_char is None:
        return False
    if next_char.isspace():
        return False
    if next_char in {",", ".", "!", "?", ")", "]", "}", ";", ":"}:
        return False
    return True


def _year_period_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if char.isspace() or char in {",", ".", "!", "?", ")", "]", "}", ";", ":"}:
            break
        index += 1
    return index


def _duration_candidate(
    start: int,
    end: int,
    full_span: SourceSpan,
    reading: str,
    reason: str,
) -> SurfaceCandidate:
    number_span = SourceSpan(start, end)
    return SurfaceCandidate(
        core_span=number_span,
        full_span=full_span,
        owner="duration",
        surface_type="DURATION_SURFACE",
        reason=reason,
        metadata={"reading": reading},
    )


def _duration_has_je_prefix(match: re.Match[str]) -> bool:
    for name in ("hour", "hour_only", "minute_only"):
        start = match.start(name)
        if start == -1:
            continue
        if has_ordinal_je_prefix(match.string, start):
            return True
    return False


def _valid_unary_sign_left_boundary(raw_text: str, start: int) -> bool:
    if start < 0 or start >= len(raw_text):
        return False
    if not is_signed_numeric_sign(raw_text[start]):
        return True
    if start == 0:
        return True
    prev_char = raw_text[start - 1]
    return prev_char.isspace() or prev_char in {"(", "[", "{", '"', "'"}


def _duration_amount_reading(raw: str, unit: str) -> str | None:
    if raw and is_signed_numeric_sign(raw[0]):
        sign = parse_sign_surface(raw[0])
        unsigned = raw[1:]
        if sign is None or not unsigned:
            return None
        unsigned_reading = _duration_amount_reading(unsigned, unit)
        if unsigned_reading is None:
            return None
        return apply_sign_profile(
            unsigned_reading.removesuffix(SPOKEN_NUMERIC_BOUNDARY),
            sign,
            sign_profile=SignProfile.DEFAULT,
        )
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        return read_fraction_text(numerator, denominator)
    if unit == "분":
        reading = read_sino_time_suffix_number_text(raw)
        if reading is not None and "." in raw:
            return f"{reading}{SPOKEN_NUMERIC_BOUNDARY}"
        return reading
    if "." in raw or "," in raw:
        reading = read_number_text(raw)
        return reading
    if len(raw) > 1 and raw.startswith("0"):
        if len(raw) == 2 and int(raw) > 0:
            return read_number_text(str(int(raw)))
        return None
    value = int(raw)
    if unit == "시간":
        native = native_number_under_100(value) if 1 <= value <= 23 else None
        if native is not None:
            return native
    return read_number_text(raw)


def _valid_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
        if prev_char == "-" and raw_text[span.start] != "-":
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    return True


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = ["parse_duration_candidate", "scan_duration_candidates"]
