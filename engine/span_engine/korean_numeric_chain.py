from __future__ import annotations

import re

from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_spaced_integer_text
from engine.span_engine.numeric_suffix import NUMERIC_SUFFIXES

_TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣ㄱ-ㅎㅏ-ㅣ_./\\+=:-]+")
_SAFE_CHAIN_RE = re.compile(r"[가-힣0-9]+")
_DIGIT_RE = re.compile(r"[0-9]+")
_HANGUL_BLOCK_RE = re.compile(r"[가-힣]+")
_KOREAN_NUMERIC_UNIT_CHARS = frozenset("십백천만억조경")
_BOUNDARY_BLOCKERS = frozenset({"_", "-", "+", "/", "\\", "=", ".", ":"})


def scan_korean_numeric_chain_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    candidates: list[SurfaceCandidate] = []
    for match in _TOKEN_RE.finditer(raw_text):
        token_end = _trim_terminal_sentence_punctuation(raw_text, match.start(), match.end())
        if token_end <= match.start():
            continue
        raw = raw_text[match.start():token_end]
        if not any(_is_hangul(char) for char in raw):
            continue
        if not any(_is_ascii_digit(char) for char in raw):
            continue
        span = SourceSpan(match.start(), token_end)
        if _SAFE_CHAIN_RE.fullmatch(raw) is None:
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="preserve",
                    surface_type="KOREAN_NUMERIC_CHAIN_PRESERVE_SURFACE",
                    reason="korean_numeric_chain_unsafe_token_preserve",
                )
            )
            continue
        if token_end == match.end() and not _valid_chain_boundary(raw_text, span):
            continue
        if not _is_eligible_safe_chain(raw):
            continue

        numeric_spans: list[SourceSpan] = []
        valid = True
        for digit_match in _DIGIT_RE.finditer(raw):
            if read_spaced_integer_text(digit_match.group(0)) is None:
                valid = False
                break
            numeric_spans.append(
                SourceSpan(
                    span.start + digit_match.start(),
                    span.start + digit_match.end(),
                )
            )
        if not valid or not numeric_spans:
            continue

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="korean_numeric_chain",
                surface_type="KOREAN_NUMERIC_CHAIN_SURFACE",
                reason="korean_numeric_chain_full_consume",
                metadata={"numeric_spans": numeric_spans},
            )
        )
    return candidates


def parse_korean_numeric_chain_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "korean_numeric_chain":
        return None
    numeric_spans = candidate.metadata.get("numeric_spans")
    if not isinstance(numeric_spans, list) or not numeric_spans:
        return None
    if not all(isinstance(span, SourceSpan) for span in numeric_spans):
        return None

    pieces: list[RenderPiece] = []
    cursor = candidate.core_span.start
    for numeric_span in numeric_spans:
        if numeric_span.start < cursor or numeric_span.end > candidate.core_span.end:
            return None
        if cursor < numeric_span.start:
            pieces.append(
                RenderPiece(
                    text=raw_text[cursor:numeric_span.start],
                    provenance="ORIGINAL_KOREAN",
                    source_span=SourceSpan(cursor, numeric_span.start),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
        raw_number = raw_text[numeric_span.start:numeric_span.end]
        reading = read_spaced_integer_text(raw_number)
        if reading is None:
            return None
        pieces.append(
            RenderPiece(
                text=reading,
                provenance="GENERATED_READING",
                source_span=numeric_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        cursor = numeric_span.end

    if cursor < candidate.core_span.end:
        pieces.append(
            RenderPiece(
                text=raw_text[cursor:candidate.core_span.end],
                provenance="ORIGINAL_KOREAN",
                source_span=SourceSpan(cursor, candidate.core_span.end),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )

    raw = raw_text[candidate.core_span.start:candidate.core_span.end]
    return Surface(
        surface_type=candidate.surface_type or "KOREAN_NUMERIC_CHAIN_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading="".join(piece.text for piece in pieces),
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def _is_eligible_safe_chain(raw: str) -> bool:
    if any(char in _KOREAN_NUMERIC_UNIT_CHARS for char in raw):
        return False
    hangul_blocks = _HANGUL_BLOCK_RE.findall(raw)
    if any(block in NUMERIC_SUFFIXES for block in hangul_blocks):
        return False
    numeric_blocks = list(_DIGIT_RE.finditer(raw))
    if raw[0].isdigit() and len(numeric_blocks) == 1:
        tail = raw[numeric_blocks[0].end():]
        return len(tail) == 1 and _is_hangul(tail)
    return True


def _trim_terminal_sentence_punctuation(raw_text: str, start: int, end: int) -> int:
    while end > start and raw_text[end - 1] in {".", ":"}:
        end -= 1
    return end


def _valid_chain_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char == ",":
        return False
    return _valid_boundary_char(prev_char) and _valid_boundary_char(next_char)


def _valid_boundary_char(char: str | None) -> bool:
    if char is None:
        return True
    if char.isascii() and char.isalnum():
        return False
    if _is_compatibility_jamo(char):
        return False
    return char not in _BOUNDARY_BLOCKERS


def _is_hangul(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_compatibility_jamo(char: str) -> bool:
    return "\u3130" <= char <= "\u318f"


__all__ = [
    "parse_korean_numeric_chain_candidate",
    "scan_korean_numeric_chain_candidates",
]
