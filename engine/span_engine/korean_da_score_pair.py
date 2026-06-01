from __future__ import annotations

import re

from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_spaced_integer_text
from engine.span_engine.range import COLON_SEMANTIC_PAIR_KEYWORDS

_DA_SCORE_PAIR_RE = re.compile(r"([1-9][0-9]*)(?: 대 ([1-9][0-9]*)|대 ?([1-9][0-9]*))")
_SENTENCE_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", "…", "。", "，", "！", "？"})
_LEFT_CONTEXT_PARTICLES = ("은", "는", "이", "가")
_BRIDGE_PARTICLES = ("으로", "로", "의")
_ATTACHED_TAILS = (
    "였고",
    "였지만",
    "이었다",
    "였습니다",
    "였다",
    "입니다",
    "이다",
    "이고",
    "으로",
    "에서",
    "에게",
    "처럼",
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
)
_SCORE_RESULT_KEYWORD_SET = frozenset(
    {
        "스코어",
        "세트스코어",
        "점수",
        "세트",
        "경기",
        "게임",
        "매치",
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
    }
)
KOREAN_DA_SCORE_PAIR_KEYWORDS = tuple(
    dict.fromkeys(
        keyword
        for keyword in ("세트스코어", *COLON_SEMANTIC_PAIR_KEYWORDS)
        if keyword in _SCORE_RESULT_KEYWORD_SET
    )
)
_KEYWORDS_BY_LENGTH = sorted(KOREAN_DA_SCORE_PAIR_KEYWORDS, key=len, reverse=True)


def scan_korean_da_score_pair_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for match in _DA_SCORE_PAIR_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if not _valid_left_boundary(raw_text, span.start):
            continue
        if not _valid_right_boundary(raw_text, span):
            continue
        if not _has_score_pair_context(raw_text, span):
            continue

        left = match.group(1)
        right = match.group(2) or match.group(3)
        if right is None:
            continue
        left_reading = read_spaced_integer_text(left)
        right_reading = read_spaced_integer_text(right)
        if left_reading is None or right_reading is None:
            continue

        left_span = SourceSpan(match.start(1), match.end(1))
        right_group_index = 2 if match.group(2) is not None else 3
        right_span = SourceSpan(match.start(right_group_index), match.end(right_group_index))
        delimiter_span = SourceSpan(left_span.end, right_span.start)
        reading = _reading_for_surface(raw_text, left_reading, right_reading, delimiter_span)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="korean_da_score_pair",
                surface_type="KOREAN_DA_SCORE_PAIR_SURFACE",
                reason="korean_da_score_pair_score_context_gate",
                metadata={
                    "left": left,
                    "right": right,
                    "left_span": left_span,
                    "right_span": right_span,
                    "delimiter_span": delimiter_span,
                    "left_reading": left_reading,
                    "right_reading": right_reading,
                    "reading": reading,
                },
            )
        )
    return candidates


def parse_korean_da_score_pair_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "korean_da_score_pair":
        return None
    reading = candidate.metadata.get("reading")
    left_reading = candidate.metadata.get("left_reading")
    right_reading = candidate.metadata.get("right_reading")
    left_span = candidate.metadata.get("left_span")
    right_span = candidate.metadata.get("right_span")
    delimiter_span = candidate.metadata.get("delimiter_span")
    if not (
        isinstance(reading, str)
        and isinstance(left_reading, str)
        and isinstance(right_reading, str)
        and isinstance(left_span, SourceSpan)
        and isinstance(right_span, SourceSpan)
        and isinstance(delimiter_span, SourceSpan)
    ):
        return None
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    return Surface(
        surface_type=candidate.surface_type or "KOREAN_DA_SCORE_PAIR_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=[
            RenderPiece(
                text=left_reading,
                provenance="GENERATED_READING",
                source_span=left_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
            *_delimiter_render_pieces(raw_text, delimiter_span, candidate),
            RenderPiece(
                text=right_reading,
                provenance="GENERATED_READING",
                source_span=right_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
        ],
        metadata={"reason": candidate.reason},
    )


def _reading_for_surface(
    raw_text: str, left_reading: str, right_reading: str, delimiter_span: SourceSpan
) -> str:
    delimiter = raw_text[delimiter_span.start : delimiter_span.end]
    if delimiter == "대":
        return f"{left_reading}대{right_reading}"
    return f"{left_reading} 대 {right_reading}"


def _delimiter_render_pieces(
    raw_text: str, delimiter_span: SourceSpan, candidate: SurfaceCandidate
) -> list[RenderPiece]:
    pieces: list[RenderPiece] = []
    delimiter = raw_text[delimiter_span.start : delimiter_span.end]
    if delimiter == "대 ":
        pieces.append(
            RenderPiece(
                text=" ",
                provenance="GENERATED_READING",
                source_span=None,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    for index in range(delimiter_span.start, delimiter_span.end):
        char = raw_text[index]
        pieces.append(
            RenderPiece(
                text=char,
                provenance="ORIGINAL_SPACE" if char.isspace() else "ORIGINAL_KOREAN",
                source_span=SourceSpan(index, index + 1),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    return pieces


def _valid_left_boundary(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if _is_complete_hangul(prev_char):
        return False
    return prev_char not in {"_", "+", "-", "/", ".", ",", ":", "~", "∼"}


def _valid_right_boundary(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        return True
    if _is_complete_hangul(next_char):
        return _has_attached_tail(raw_text, span.end)
    return False


def _has_attached_tail(raw_text: str, tail_start: int) -> bool:
    for tail in _ATTACHED_TAILS:
        if not raw_text.startswith(tail, tail_start):
            continue
        if len(tail) > 1:
            return True
        after = tail_start + len(tail)
        return after == len(raw_text) or not _is_complete_hangul(raw_text[after])
    return False


def _has_score_pair_context(raw_text: str, span: SourceSpan) -> bool:
    prev_text = raw_text[: span.start].rstrip()
    next_text = raw_text[span.end :]
    if _text_endswith_score_keyword(prev_text):
        return True
    compact_next = next_text.lstrip()
    if _text_startswith_score_keyword(compact_next):
        return True
    for particle in _BRIDGE_PARTICLES:
        if compact_next.startswith(particle):
            after_particle = compact_next[len(particle) :].lstrip()
            return _text_startswith_score_keyword(after_particle)
    return False


def _text_endswith_score_keyword(text: str) -> bool:
    for keyword in _KEYWORDS_BY_LENGTH:
        if _endswith_keyword_at_boundary(text, keyword):
            return True
        for particle in _LEFT_CONTEXT_PARTICLES:
            if _endswith_keyword_at_boundary(text, keyword + particle, keyword_len=len(keyword)):
                return True
    return False


def _endswith_keyword_at_boundary(
    text: str, suffix: str, *, keyword_len: int | None = None
) -> bool:
    if not text.endswith(suffix):
        return False
    boundary_len = len(suffix) if keyword_len is None else keyword_len
    before_index = len(text) - len(suffix)
    prev_char = text[before_index - 1] if before_index > 0 else None
    return _valid_keyword_left_boundary(prev_char) and boundary_len > 0


def _text_startswith_score_keyword(text: str) -> bool:
    for keyword in _KEYWORDS_BY_LENGTH:
        if not text.startswith(keyword):
            continue
        next_char = text[len(keyword)] if len(keyword) < len(text) else None
        return _valid_keyword_right_boundary(next_char)
    return False


def _valid_keyword_left_boundary(prev_char: str | None) -> bool:
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    return not _is_complete_hangul(prev_char)


def _valid_keyword_right_boundary(next_char: str | None) -> bool:
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION:
        return True
    return not (next_char.isascii() and next_char.isalnum())


def _is_complete_hangul(char: str | None) -> bool:
    return isinstance(char, str) and "\uac00" <= char <= "\ud7a3"


__all__ = [
    "KOREAN_DA_SCORE_PAIR_KEYWORDS",
    "parse_korean_da_score_pair_candidate",
    "scan_korean_da_score_pair_candidates",
]
