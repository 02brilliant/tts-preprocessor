from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
_DIGIT_READINGS = {
    0: "공",
    1: "일",
    2: "이",
    3: "삼",
    4: "사",
    5: "오",
    6: "육",
    7: "칠",
    8: "팔",
    9: "구",
}

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


def digit_block_reading(block: str) -> str:
    if not isinstance(block, str):
        raise TypeError("block must be str")
    if not _is_ascii_digits(block):
        raise ValueError("block must be a digit-only string")
    return "".join(_DIGIT_READINGS[int(digit)] for digit in block)


def hyphen_digit_reading(raw: str) -> str | None:
    if not is_hyphen_digit_candidate(raw):
        return None
    blocks = raw.split("-")
    return " ".join(digit_block_reading(block) for block in blocks)


def is_hyphen_digit_candidate(raw: str) -> bool:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    blocks = raw.split("-")
    if len(blocks) < 3 or len(blocks) > 9:
        return False
    return all(_is_ascii_digits(block) for block in blocks)


def scan_hyphen_digit_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        if _is_blocked_start(raw_text, index):
            index += 1
            continue
        candidate = _scan_candidate_from(raw_text, index, excluded_ranges)
        if candidate is None:
            index += 1
            continue
        candidates.append(candidate)
        index = candidate.core_span.end
    return candidates


def _scan_candidate_from(
    raw_text: str, start: int, excluded_ranges: list[BracketRange]
) -> SurfaceCandidate | None:
    blocks: list[str] = []
    index = start
    while index < len(raw_text):
        digit_end = _consume_digits(raw_text, index)
        block = raw_text[index:digit_end]
        if not block:
            break
        blocks.append(block)
        index = digit_end
        if index >= len(raw_text) or raw_text[index] != "-":
            break
        index += 1
        if index >= len(raw_text) or not _is_ascii_digit(raw_text[index]):
            return None
        if raw_text[index - 1] != "-":
            return None

    if len(blocks) == 2 and [len(block) for block in blocks] == [4, 4]:
        owner = "phone"
        surface_type = "PHONE_SURFACE"
    elif len(blocks) >= 3 and len(blocks) <= 9:
        lengths = [len(block) for block in blocks]
        if len(blocks) == 3 and lengths == [4, 2, 2]:
            return None
        if len(blocks) == 3 and lengths[0] == 4 and lengths[1] == 1 and lengths[2] == 1:
            return None
        if len(blocks) == 3 and lengths[0] == 2 and any(
            block.startswith("0") for block in blocks[1:]
        ):
            return None
        owner = "hyphen_digit_blocks"
        surface_type = "HYPHEN_DIGIT_BLOCK_SURFACE"
    else:
        return None

    core_end = start + sum(len(block) for block in blocks) + (len(blocks) - 1)
    span = SourceSpan(start, core_end)
    if _span_overlaps_excluded_range(span, excluded_ranges):
        return None
    if not _valid_boundaries(raw_text, span):
        return None
    tail = raw_text[core_end:]
    if not _tail_is_allowed(tail):
        return None
    reading = " ".join(digit_block_reading(block) for block in blocks)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner=owner,
        surface_type=surface_type,
        reason="hyphen_digit_block_route" if owner == "hyphen_digit_blocks" else "phone_route",
        metadata={
            "blocks": blocks,
            "reading": reading,
            "tail": _tail_prefix(tail),
        },
    )


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_blocked_start(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return False
    return prev_char.isascii() and prev_char.isalnum() or prev_char in {"-", "_", "/"}


def _valid_boundaries(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if prev_char in {"-", "_", "/"}:
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in {"-", "_", "/"}:
        return False
    return True


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


def _tail_prefix(tail: str) -> str | None:
    for allowed in sorted(_ALLOWED_TAILS, key=len, reverse=True):
        if allowed and tail.startswith(allowed):
            return allowed
    return "" if tail == "" else None


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "digit_block_reading",
    "hyphen_digit_reading",
    "is_hyphen_digit_candidate",
    "scan_hyphen_digit_candidates",
]
