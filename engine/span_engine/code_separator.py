from __future__ import annotations

import re

from engine.span_engine.hyphen import digit_block_reading
from engine.span_engine.jamo import jamo_sequence_reading
from engine.span_engine.lexicon import LETTER_READINGS
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_number_text
from engine.span_engine.single_letter_code import (
    parse_single_letter_alnum_code_candidate,
    scan_single_letter_alnum_code_candidates,
)

# Spaced numeric chains: "1 - 2 - 3".
_SPACED_HYPHEN_NUMERIC_RE = re.compile(
    r"(?<![A-Za-z0-9가-힣])\d+(?:\.\d+)?(?: - \d+(?:\.\d+)?){2,}(?![A-Za-z0-9])"
)

# Mixed alpha/digit blocks separated by hyphen or middle dot: "A1·B2".
_MIXED_ALNUM_SEPARATOR_RE = re.compile(
    r"(?<![A-Za-z0-9가-힣])(?:[A-Za-z0-9]+(?:[-·][A-Za-z0-9]+)+)(?![A-Za-z0-9가-힣])"
)

# Two-block decimal/hyphen codes: "B-2.5", "x-3".
_TWO_BLOCK_HYPHEN_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9가-힣ㄱ-ㅎㅏ-ㅣ])"
    r"([A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ]+)-(\d+(?:\.\d+)?)"
    r"(?![A-Za-z0-9가-힣ㄱ-ㅎㅏ-ㅣ℃℉°º._/-])"
)


def scan_spaced_hyphen_numeric_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for match in _SPACED_HYPHEN_NUMERIC_RE.finditer(raw_text):
        raw = match.group(0)
        blocks = raw.split(" - ")
        readings = [_numeric_block_reading(block) for block in blocks]
        if any(reading is None for reading in readings):
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="spaced_hyphen_numeric_blocks",
                surface_type="SPACED_HYPHEN_NUMERIC_BLOCK_SURFACE",
                reason="spaced_hyphen_numeric_multiblock",
                metadata={"blocks": blocks, "reading": " ".join(readings)},  # type: ignore[arg-type]
            )
        )
    return candidates


def scan_mixed_alnum_code_separator_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for match in _MIXED_ALNUM_SEPARATOR_RE.finditer(raw_text):
        raw = match.group(0)
        blocks = re.split("[-·]", raw)
        if not all(_has_alpha_and_digit(block) for block in blocks):
            continue
        compact = raw.replace("-", "").replace("·", "")
        reading = _mixed_alnum_reading(compact)
        if reading is None:
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="mixed_alnum_code_separator",
                surface_type="MIXED_ALNUM_CODE_SEPARATOR_SURFACE",
                reason="mixed_alnum_code_separator_fallback",
                metadata={"reading": reading},
            )
        )
    return candidates


def scan_two_block_hyphen_code_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for match in _TWO_BLOCK_HYPHEN_CODE_RE.finditer(raw_text):
        left = match.group(1)
        number = match.group(2)
        if left == "K":
            continue
        if len(left) > 1 and all(char.isascii() and char.isalpha() for char in left):
            continue
        left_reading = _left_block_reading(left)
        number_reading = read_number_text(number)
        if left_reading is None or number_reading is None:
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="two_block_hyphen_code",
                surface_type="CODE_SEPARATOR_BLOCK_SURFACE",
                reason="two_block_hyphen_decimal_code_policy",
                metadata={"reading": f"{left_reading} {number_reading}"},
            )
        )
    return candidates


def parse_spaced_hyphen_numeric_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "spaced_hyphen_numeric_blocks":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def parse_mixed_alnum_code_separator_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "mixed_alnum_code_separator":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def parse_two_block_hyphen_code_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "two_block_hyphen_code":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _numeric_block_reading(block: str) -> str | None:
    integer_part = block.split(".", 1)[0]
    if (
        "." not in block
        and len(integer_part) > 1
        and integer_part.startswith("0")
    ):
        return digit_block_reading(block)
    return read_number_text(block)


def _mixed_alnum_reading(compact: str) -> str | None:
    parts: list[str] = []
    for char in compact:
        if char.isascii() and char.isalpha():
            parts.append(LETTER_READINGS[char.upper()])
            continue
        if char.isascii() and char.isdigit():
            parts.append(digit_block_reading(char))
            continue
        return None
    return " ".join(parts)


def _left_block_reading(left: str) -> str | None:
    if all(char.isascii() and char.isalpha() for char in left):
        return " ".join(LETTER_READINGS[char.upper()] for char in left)
    if all("\uac00" <= char <= "\ud7a3" for char in left):
        return left
    if all("\u3130" <= char <= "\u318f" for char in left):
        return jamo_sequence_reading(left)
    return None


def _has_alpha_and_digit(block: str) -> bool:
    return (
        bool(block)
        and block[0].isascii()
        and block[0].isalpha()
        and any(char.isascii() and char.isalpha() for char in block)
        and any(char.isascii() and char.isdigit() for char in block)
    )


__all__ = [
    "parse_mixed_alnum_code_separator_candidate",
    "parse_single_letter_alnum_code_candidate",
    "parse_spaced_hyphen_numeric_candidate",
    "parse_two_block_hyphen_code_candidate",
    "scan_mixed_alnum_code_separator_candidates",
    "scan_single_letter_alnum_code_candidates",
    "scan_spaced_hyphen_numeric_candidates",
    "scan_two_block_hyphen_code_candidates",
]
