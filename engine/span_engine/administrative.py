from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY

SUPPORTED_ADMINISTRATIVE_ANCHORS: dict[str, dict[str, str | bool]] = {
    "종로": {"suffix": "가", "requires_space": False},
    "역삼동": {"suffix": "번지", "requires_space": True},
}
SUPPORTED_ADMINISTRATIVE_SUFFIXES = frozenset({"가", "번지"})
_UNSAFE_TAIL_PREFIXES = ("/", "_", ".", "-")


def has_address_anchor(raw_text: str, index: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(index, int):
        raise TypeError("index must be int")
    return any(raw_text.startswith(anchor, index) for anchor in SUPPORTED_ADMINISTRATIVE_ANCHORS)


def is_supported_admin_suffix(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return text in SUPPORTED_ADMINISTRATIVE_SUFFIXES


def is_unsafe_admin_tail(tail: str) -> bool:
    if not isinstance(tail, str):
        raise TypeError("tail must be str")
    if tail == "":
        return False
    first = tail[0]
    if first.isascii() and first.isalnum():
        return True
    if tail.startswith(_UNSAFE_TAIL_PREFIXES):
        return True
    return False


def scan_administrative_suffix_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for anchor, config in SUPPORTED_ADMINISTRATIVE_ANCHORS.items():
        search_start = 0
        while True:
            anchor_start = raw_text.find(anchor, search_start)
            if anchor_start < 0:
                break
            candidate = _build_candidate(
                raw_text,
                anchor_start,
                anchor,
                str(config["suffix"]),
                bool(config["requires_space"]),
                excluded_ranges,
            )
            if candidate is not None:
                candidates.append(candidate)
            search_start = anchor_start + 1
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def parse_administrative_suffix_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "administrative_suffix":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    raw_number = raw_text[candidate.core_span.start : candidate.core_span.end]
    if not _is_supported_number(raw_number):
        return None
    return number_to_korean_under_10000(int(raw_number))


def is_unsafe_admin_like_number_tail(raw_text: str, span_end: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(span_end, int):
        raise TypeError("span_end must be int")
    tail = raw_text[span_end:]
    if tail.startswith("가") and len(tail) > 1 and tail[1].isascii() and tail[1].isalnum():
        return True
    next_non_space = tail.lstrip()
    if tail[:1].isspace() and next_non_space.startswith("가"):
        return True
    return False


def _build_candidate(
    raw_text: str,
    anchor_start: int,
    anchor: str,
    suffix: str,
    requires_space: bool,
    excluded_ranges: list[BracketRange],
) -> SurfaceCandidate | None:
    if not _is_safe_anchor_boundary(raw_text, anchor_start):
        return None

    cursor = anchor_start + len(anchor)
    if requires_space:
        if cursor >= len(raw_text) or not raw_text[cursor].isspace():
            return None
        while cursor < len(raw_text) and raw_text[cursor].isspace():
            cursor += 1
    number_start = cursor
    number_end = _consume_digits(raw_text, number_start)
    if number_end == number_start:
        return None
    number = raw_text[number_start:number_end]
    if not _is_supported_number(number):
        return None
    if not raw_text.startswith(suffix, number_end):
        return None
    suffix_end = number_end + len(suffix)
    full_span = SourceSpan(anchor_start, suffix_end)
    if _span_overlaps_excluded_range(full_span, excluded_ranges):
        return None
    if is_unsafe_admin_tail(raw_text[suffix_end:]):
        return None
    number_reading = number_to_korean_under_10000(int(number))
    generated_prefix = "" if requires_space else " "
    return SurfaceCandidate(
        core_span=SourceSpan(number_start, number_end),
        full_span=full_span,
        owner="administrative_suffix",
        surface_type="ADMINISTRATIVE_SUFFIX_SURFACE",
        suffix_spans=[SourceSpan(number_end, suffix_end)],
        reason="administrative_suffix_anchor_gate",
        metadata={
            "anchor": anchor,
            "suffix": suffix,
            "reading": f"{generated_prefix}{number_reading}{SPOKEN_NUMERIC_BOUNDARY}",
            "generated_prefix": generated_prefix,
            "generated_suffix_separator": SPOKEN_NUMERIC_BOUNDARY,
        },
    )


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _is_supported_number(number: str) -> bool:
    if not _is_ascii_digits(number):
        return False
    if len(number) > 1 and number.startswith("0"):
        return False
    return int(number) <= 9999


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_safe_anchor_boundary(raw_text: str, anchor_start: int) -> bool:
    if anchor_start == 0:
        return True
    prev_char = raw_text[anchor_start - 1]
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if "\uac00" <= prev_char <= "\ud7a3":
        return False
    return True


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "SUPPORTED_ADMINISTRATIVE_ANCHORS",
    "SUPPORTED_ADMINISTRATIVE_SUFFIXES",
    "has_address_anchor",
    "is_supported_admin_suffix",
    "is_unsafe_admin_like_number_tail",
    "is_unsafe_admin_tail",
    "parse_administrative_suffix_candidate",
    "scan_administrative_suffix_candidates",
]
