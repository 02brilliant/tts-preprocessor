from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate

JAMO_READINGS: dict[str, str] = {
    "ㄱ": "기역",
    "ㄲ": "쌍기역",
    "ㄴ": "니은",
    "ㄷ": "디귿",
    "ㄸ": "쌍디귿",
    "ㄹ": "리을",
    "ㅁ": "미음",
    "ㅂ": "비읍",
    "ㅃ": "쌍비읍",
    "ㅅ": "시옷",
    "ㅆ": "쌍시옷",
    "ㅇ": "이응",
    "ㅈ": "지읒",
    "ㅉ": "쌍지읒",
    "ㅊ": "치읓",
    "ㅋ": "키읔",
    "ㅌ": "티읕",
    "ㅍ": "피읖",
    "ㅎ": "히읗",
    "ㅏ": "아",
    "ㅑ": "야",
    "ㅓ": "어",
    "ㅕ": "여",
    "ㅗ": "오",
    "ㅛ": "요",
    "ㅜ": "우",
    "ㅠ": "유",
    "ㅡ": "으",
    "ㅣ": "이",
    "ㅐ": "애",
    "ㅔ": "에",
    "ㅚ": "외",
    "ㅟ": "위",
    "ㅢ": "의",
}

_JAMO_RUN_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", "·"})


def is_supported_jamo(ch: str) -> bool:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return ch in JAMO_READINGS


def jamo_reading(ch: str) -> str | None:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return JAMO_READINGS.get(ch)


def jamo_sequence_reading(text: str) -> str | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text or not all(is_supported_jamo(ch) for ch in text):
        return None
    return " ".join(JAMO_READINGS[ch] for ch in text)


def scan_jamo_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not is_supported_jamo(raw_text[index]):
            index += 1
            continue
        if _is_blocked_by_neighbors(raw_text, index):
            index += 1
            continue
        start = index
        end = index + 1
        while end < len(raw_text) and is_supported_jamo(raw_text[end]):
            end += 1
        span = SourceSpan(start, end)
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index = end
            continue
        if _is_invalid_boundaries(raw_text, span):
            index = end
            continue
        reading = jamo_sequence_reading(raw_text[start:end])
        if reading is None:
            index = end
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="jamo",
                surface_type="JAMO_SURFACE",
                reason="compatibility_jamo_surface",
                metadata={"reading": reading},
            )
        )
        index = end
    return candidates


def parse_jamo_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "jamo":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    return jamo_sequence_reading(raw)


def _is_blocked_by_neighbors(raw_text: str, index: int) -> bool:
    prev_char = raw_text[index - 1] if index > 0 else None
    next_char = raw_text[index + 1] if index + 1 < len(raw_text) else None
    if prev_char is not None and _is_unsafe_neighbor(prev_char):
        return True
    if next_char is not None and _is_unsafe_neighbor(next_char):
        return True
    return False


def _is_invalid_boundaries(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None and _is_unsafe_neighbor(prev_char):
        return True
    if next_char is not None and _is_unsafe_neighbor(next_char):
        return True
    return False


def _is_unsafe_neighbor(ch: str) -> bool:
    if ch.isspace():
        return False
    if ch in _JAMO_RUN_PUNCTUATION:
        return False
    if ch.isascii() and ch.isalnum():
        return True
    if ch in {"-", "_", "/"}:
        return True
    return False


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "JAMO_READINGS",
    "is_supported_jamo",
    "jamo_reading",
    "jamo_sequence_reading",
    "parse_jamo_candidate",
    "scan_jamo_candidates",
]
