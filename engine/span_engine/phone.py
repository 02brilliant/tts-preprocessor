from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.hyphen import (
    digit_block_reading,
    scan_hyphen_digit_candidates,
)
from engine.span_engine.models import SourceSpan, SurfaceCandidate

_ALLOWED_TAILS = (
    "",
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
    "입니다",
)


def is_exact_4_4_phone(raw: str) -> bool:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    blocks = raw.split("-")
    return len(blocks) == 2 and [len(block) for block in blocks] == [4, 4]


def phone_reading(raw: str) -> str | None:
    if is_international_phone(raw):
        blocks = raw[1:].split("-")
        return "플러스 " + " ".join(digit_block_reading(block) for block in blocks)
    if not is_exact_4_4_phone(raw):
        return None
    left, right = raw.split("-")
    return f"{digit_block_reading(left)} {digit_block_reading(right)}"


def is_international_phone(raw: str) -> bool:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    if not raw.startswith("+"):
        return False
    blocks = raw[1:].split("-")
    if len(blocks) < 3 or len(blocks) > 5:
        return False
    country, *rest = blocks
    if not (1 <= len(country) <= 3 and country.isascii() and country.isdigit()):
        return False
    return all(2 <= len(block) <= 4 and block.isascii() and block.isdigit() for block in rest)


def scan_phone_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []
    candidates = _scan_international_phone_candidates(raw_text, excluded_ranges)
    for candidate in scan_hyphen_digit_candidates(raw_text, excluded_ranges):
        if candidate.owner != "phone":
            continue
        candidates.append(candidate)
    return candidates


def _scan_international_phone_candidates(
    raw_text: str, excluded_ranges: list[BracketRange]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] != "+":
            index += 1
            continue
        span = _scan_international_phone_span(raw_text, index)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        if not _valid_boundaries(raw_text, span):
            index += 1
            continue
        raw = raw_text[span.start : span.end]
        reading = phone_reading(raw)
        if reading is None:
            index += 1
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="phone",
                surface_type="PHONE_SURFACE",
                reason="international_phone_plus_route",
                metadata={"reading": reading},
            )
        )
        index = span.end
    return candidates


def _scan_international_phone_span(raw_text: str, start: int) -> SourceSpan | None:
    index = start + 1
    first_end = _consume_digits(raw_text, index)
    if first_end == index or first_end - index > 3:
        return None
    blocks = [raw_text[index:first_end]]
    index = first_end
    while index < len(raw_text) and raw_text[index] == "-":
        block_start = index + 1
        block_end = _consume_digits(raw_text, block_start)
        if block_end == block_start:
            return None
        blocks.append(raw_text[block_start:block_end])
        index = block_end
    span = SourceSpan(start, index)
    return span if is_international_phone(raw_text[start:index]) else None


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isascii() and raw_text[index].isdigit():
        index += 1
    return index


def _valid_boundaries(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if prev_char in {"_", "/", ".", "-", "+"}:
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in {"_", "/", "-"}:
        return False
    return _tail_is_allowed(raw_text[span.end :])


def _tail_is_allowed(tail: str) -> bool:
    if tail == "":
        return True
    if tail[0].isspace():
        return True
    if tail[0] in {".", ",", "!", "?"}:
        return True
    for allowed in (value for value in _ALLOWED_TAILS if value):
        if tail.startswith(allowed):
            return True
    if "\uac00" <= tail[0] <= "\ud7a3":
        return any(tail.startswith(allowed) for allowed in _ALLOWED_TAILS if allowed)
    return False


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "digit_block_reading",
    "is_exact_4_4_phone",
    "is_international_phone",
    "phone_reading",
    "scan_phone_candidates",
]
