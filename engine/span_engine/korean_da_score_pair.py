from __future__ import annotations

import re

from engine.span_engine.counter import COUNTERS_BY_LENGTH, counter_number_reading
from engine.span_engine.currency import (
    CURRENCY_CODE_READINGS,
    CURRENCY_SYMBOL_READINGS,
    KOREAN_CURRENCY_SUFFIX_READINGS,
)
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY
from engine.span_engine.numeric_dae import (
    explicit_numeric_dae_counter_context_reason,
    is_sino_threshold_numeric_dae,
)
from engine.span_engine.multiplier import multiplier_number_reading
from engine.span_engine.numeric_reading import (
    normalize_integer_text,
    read_fraction_text,
    read_number_text,
)
from engine.span_engine.numeric_suffix import NUMERIC_SUFFIXES
from engine.span_engine.range import COLON_SEMANTIC_PAIR_KEYWORDS
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    parse_signed_numeric_core,
    render_signed_numeric,
)
from engine.span_engine.units import supported_unit_prefix_length

_INTEGER_PATTERN = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_DECIMAL_PATTERN = rf"(?:{_INTEGER_PATTERN})\.\d+"
_FRACTION_PATTERN = rf"{_INTEGER_PATTERN}/{_INTEGER_PATTERN}"
_SIGNED_NUMBER_PATTERN = rf"[+-](?:{_DECIMAL_PATTERN}|{_INTEGER_PATTERN})"
_NUMERIC_OPERAND_PATTERN = (
    rf"(?:{_SIGNED_NUMBER_PATTERN}|{_FRACTION_PATTERN}|"
    rf"{_DECIMAL_PATTERN}|{_INTEGER_PATTERN})"
)
_DA_SCORE_PAIR_RE = re.compile(
    rf"(?P<left>{_NUMERIC_OPERAND_PATTERN})"
    rf"(?: 대 (?P<right_spaced>{_NUMERIC_OPERAND_PATTERN})|"
    rf"대 ?(?P<right_compact>{_NUMERIC_OPERAND_PATTERN}))"
)
_SENTENCE_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", "…", "。", "，", "！", "？"})
_LEFT_CONTEXT_PARTICLES = ("은", "는", "이", "가")
_BRIDGE_PARTICLES = ("으로", "로", "의")
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
_OWNER_ATTACHED_HANGUL_TAILS = (
    "입니다",
    "였습니다",
    "이었다",
    "였다",
    "이다",
    "이고",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "부터",
    "까지",
    "으로",
    "로",
    "와",
    "과",
    "도",
    "만",
    "씩",
    "짜리",
)
_AMBIGUOUS_DATE_OWNER_PARTICLES = (
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "에게",
    "부터",
    "까지",
    "으로",
    "로",
    "와",
    "과",
    "도",
    "만",
)
_AMBIGUOUS_DATE_SUFFIXES = frozenset({"년", "월", "일"})
_RIGHT_NUMBER_COUNTER_SUFFIXES = tuple(
    sorted(set(COUNTERS_BY_LENGTH) | set(NUMERIC_SUFFIXES), key=len, reverse=True)
)
_RIGHT_NUMBER_CURRENCY_SUFFIXES = tuple(
    sorted(
        set(CURRENCY_SYMBOL_READINGS)
        | set(CURRENCY_CODE_READINGS)
        | set(KOREAN_CURRENCY_SUFFIX_READINGS),
        key=len,
        reverse=True,
    )
)
_RIGHT_NUMBER_DURATION_SUFFIXES = ("년간", "시간", "분")
_RIGHT_NUMBER_MULTIPLIER_SUFFIXES = ("배",)
_RIGHT_NUMBER_CLOCK_SUFFIXES = ("시",)
_RIGHT_NUMBER_BLOCKING_ASCII_CONTINUATIONS = frozenset("_")


def scan_korean_da_score_pair_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for match in _DA_SCORE_PAIR_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if not _valid_left_boundary(raw_text, span.start):
            continue

        left = match.group("left")
        right = match.group("right_spaced") or match.group("right_compact")
        if right is None:
            continue
        left_reading = _readable_numeric_operand_reading(left)
        right_reading = _readable_numeric_operand_reading(right)
        if left_reading is None or right_reading is None:
            continue

        left_span = SourceSpan(match.start("left"), match.end("left"))
        right_group_name = (
            "right_spaced"
            if match.group("right_spaced") is not None
            else "right_compact"
        )
        right_span = SourceSpan(match.start(right_group_name), match.end(right_group_name))
        delimiter_span = SourceSpan(left_span.end, right_span.start)
        gate_reason = _score_pair_gate_reason(
            raw_text,
            span,
            right,
            right_span,
            left_span,
            delimiter_span,
        )
        if gate_reason is None:
            continue
        is_quantity_sequence = (
            gate_reason == "numeric_dae_quantity_sequence_explicit_counter_context"
        )
        if is_quantity_sequence:
            counter_reading = counter_number_reading(left, "대")
            if counter_reading is not None:
                left_reading = counter_reading.removesuffix(
                    SPOKEN_NUMERIC_BOUNDARY
                )
        compact_integer_rendering = _uses_compact_integer_rendering(
            raw_text, left, right, delimiter_span
        )
        reading = _reading_for_surface(
            raw_text,
            left_reading,
            right_reading,
            delimiter_span,
            compact_integer_rendering=compact_integer_rendering,
        )
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner=(
                    "numeric_dae_quantity_sequence"
                    if is_quantity_sequence
                    else "korean_da_score_pair"
                ),
                surface_type=(
                    "NUMERIC_DAE_QUANTITY_SEQUENCE_SURFACE"
                    if is_quantity_sequence
                    else "KOREAN_DA_SCORE_PAIR_SURFACE"
                ),
                reason=gate_reason,
                metadata={
                    "left": left,
                    "right": right,
                    "left_span": left_span,
                    "right_span": right_span,
                    "delimiter_span": delimiter_span,
                    "left_reading": left_reading,
                    "right_reading": right_reading,
                    "reading": reading,
                    "compact_integer_rendering": compact_integer_rendering,
                },
            )
        )
    return candidates


def parse_korean_da_score_pair_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner not in {
        "korean_da_score_pair",
        "numeric_dae_quantity_sequence",
    }:
        return None
    reading = candidate.metadata.get("reading")
    left_reading = candidate.metadata.get("left_reading")
    right_reading = candidate.metadata.get("right_reading")
    left_span = candidate.metadata.get("left_span")
    right_span = candidate.metadata.get("right_span")
    delimiter_span = candidate.metadata.get("delimiter_span")
    compact_integer_rendering = candidate.metadata.get("compact_integer_rendering")
    if not (
        isinstance(reading, str)
        and isinstance(left_reading, str)
        and isinstance(right_reading, str)
        and isinstance(left_span, SourceSpan)
        and isinstance(right_span, SourceSpan)
        and isinstance(delimiter_span, SourceSpan)
        and isinstance(compact_integer_rendering, bool)
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
            *_delimiter_render_pieces(
                raw_text,
                delimiter_span,
                candidate,
                compact_integer_rendering=compact_integer_rendering,
            ),
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
    raw_text: str,
    left_reading: str,
    right_reading: str,
    delimiter_span: SourceSpan,
    *,
    compact_integer_rendering: bool,
) -> str:
    if compact_integer_rendering:
        return f"{left_reading}대{right_reading}"
    return f"{left_reading} 대 {right_reading}"


def _delimiter_render_pieces(
    raw_text: str,
    delimiter_span: SourceSpan,
    candidate: SurfaceCandidate,
    *,
    compact_integer_rendering: bool,
) -> list[RenderPiece]:
    pieces: list[RenderPiece] = []
    delimiter = raw_text[delimiter_span.start : delimiter_span.end]
    if not compact_integer_rendering and not delimiter.startswith(" "):
        generated_separator = (
            SPOKEN_NUMERIC_BOUNDARY
            if candidate.owner == "numeric_dae_quantity_sequence"
            else " "
        )
        pieces.append(
            RenderPiece(
                text=generated_separator,
                provenance=(
                    "GENERATED_PUNCT"
                    if generated_separator == SPOKEN_NUMERIC_BOUNDARY
                    else "GENERATED_READING"
                ),
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
    if not compact_integer_rendering and not delimiter.endswith(" "):
        pieces.append(
            RenderPiece(
                text=" ",
                provenance="GENERATED_READING",
                source_span=None,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    return pieces


def _readable_numeric_operand_reading(raw_operand: str) -> str | None:
    if not isinstance(raw_operand, str):
        raise TypeError("raw_operand must be str")
    if not raw_operand:
        return None
    if raw_operand[0] in {"+", "-"}:
        if "/" in raw_operand:
            return None
        policy = SIGNED_OWNER_POLICIES["colon_semantic_pair"]
        core = parse_signed_numeric_core(
            raw_operand,
            allow_plus=policy.accepts_plus,
            allow_minus=policy.accepts_minus,
            minus_aliases=policy.minus_aliases,
            require_sign=True,
            numeric_forms=policy.numeric_forms,
        )
        if core is None:
            return None
        return render_signed_numeric(
            core,
            sign_profile=policy.sign_profile,
        )
    if "/" in raw_operand:
        if raw_operand.count("/") != 1:
            return None
        numerator, denominator = raw_operand.split("/", 1)
        return read_fraction_text(numerator, denominator)
    return read_number_text(raw_operand)


def _uses_compact_integer_rendering(
    raw_text: str, left: str, right: str, delimiter_span: SourceSpan
) -> bool:
    delimiter = raw_text[delimiter_span.start : delimiter_span.end]
    return (
        delimiter == "대"
        and _is_plain_unsigned_integer_operand(left)
        and _is_plain_unsigned_integer_operand(right)
    )


def _is_plain_unsigned_integer_operand(raw_operand: str) -> bool:
    return (
        raw_operand.isascii()
        and raw_operand.isdigit()
        and normalize_integer_text(raw_operand) is not None
    )


def _valid_left_boundary(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if _is_complete_hangul(prev_char):
        return False
    return prev_char not in {"_", "+", "-", "/", ".", ",", ":", "~", "∼", "="}


def _score_pair_gate_reason(
    raw_text: str,
    span: SourceSpan,
    right: str,
    right_span: SourceSpan,
    left_span: SourceSpan,
    delimiter_span: SourceSpan,
) -> str | None:
    if not _valid_right_boundary(raw_text, span):
        return None
    if right_number_blocks_registered_owner_suffix(raw_text, right, right_span):
        return None
    if _has_score_pair_context(raw_text, span):
        return "korean_da_score_pair_score_context_gate"
    if (
        raw_text[delimiter_span.start : delimiter_span.end].startswith("대")
        and explicit_numeric_dae_counter_context_reason(
            raw_text, SourceSpan(left_span.start, left_span.end + 1)
        )
        is not None
    ):
        return "numeric_dae_quantity_sequence_explicit_counter_context"
    if (
        raw_text[delimiter_span.start : delimiter_span.end] == "대 "
        and is_sino_threshold_numeric_dae(
            raw_text, SourceSpan(left_span.start, left_span.end + 1)
        )
    ):
        return None
    if is_independent_right_number_for_da_pair(raw_text, right, right_span):
        return "korean_da_score_pair_independent_right_number_gate"
    return None


def _valid_right_boundary(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if (
        next_char in {",", "."}
        and span.end + 1 < len(raw_text)
        and raw_text[span.end + 1].isascii()
        and raw_text[span.end + 1].isdigit()
    ):
        return False
    if next_char in _SENTENCE_PUNCTUATION:
        return True
    if _is_complete_hangul(next_char):
        return True
    return False


def is_independent_right_number_for_da_pair(
    raw_text: str, right_number: str, right_span: SourceSpan
) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(right_number, str):
        raise TypeError("right_number must be str")
    if not isinstance(right_span, SourceSpan):
        raise TypeError("right_span must be SourceSpan")
    if _readable_numeric_operand_reading(right_number) is None:
        return False

    next_char = raw_text[right_span.end] if right_span.end < len(raw_text) else None
    if next_char is not None:
        if next_char in _RIGHT_NUMBER_BLOCKING_ASCII_CONTINUATIONS:
            return False
        if next_char.isascii() and next_char.isalnum():
            return False
        if (
            next_char in {",", "."}
            and right_span.end + 1 < len(raw_text)
            and raw_text[right_span.end + 1].isascii()
            and raw_text[right_span.end + 1].isdigit()
        ):
            return False
        if next_char in {"/"}:
            return False

    return not right_number_blocks_registered_owner_suffix(
        raw_text, right_number, right_span
    )


def right_number_blocks_registered_owner_suffix(
    raw_text: str, right_number: str, right_span: SourceSpan
) -> bool:
    suffix_start = _consume_optional_ascii_space(raw_text, right_span.end)
    suffix_gap = raw_text[right_span.end : suffix_start]
    suffix_text = raw_text[suffix_start:]
    if not suffix_text:
        return False
    if suffix_gap not in {"", " "}:
        return False

    if _blocks_unit_suffix(suffix_text):
        return True
    if _blocks_currency_suffix(raw_text, right_number, right_span.start, suffix_start):
        return True
    if _blocks_counter_or_numeric_suffix(raw_text, right_number, suffix_start):
        return True
    if _blocks_registered_suffixes(
        raw_text,
        suffix_start,
        right_number,
        _RIGHT_NUMBER_DURATION_SUFFIXES,
        numeric_reader=lambda number, suffix: _readable_unsigned_number_or_fraction(
            number
        ),
    ):
        return True
    if _blocks_registered_suffixes(
        raw_text,
        suffix_start,
        right_number,
        _RIGHT_NUMBER_MULTIPLIER_SUFFIXES,
        numeric_reader=lambda number, suffix: multiplier_number_reading(number),
    ):
        return True
    if _blocks_clock_suffix(raw_text, right_number, suffix_start):
        return True
    return False


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _blocks_unit_suffix(suffix_text: str) -> bool:
    return supported_unit_prefix_length(suffix_text) is not None


def _blocks_currency_suffix(
    raw_text: str, right_number: str, right_start: int, suffix_start: int
) -> bool:
    if _readable_numeric_operand_reading(right_number) is None:
        return False
    for suffix in _RIGHT_NUMBER_CURRENCY_SUFFIXES:
        if not raw_text.startswith(suffix, suffix_start):
            continue
        suffix_end = suffix_start + len(suffix)
        if not _registered_suffix_boundary(raw_text, suffix, suffix_end):
            continue
        if suffix in KOREAN_CURRENCY_SUFFIX_READINGS or suffix in CURRENCY_SYMBOL_READINGS:
            return True
        return right_start < suffix_start
    return False


def _blocks_counter_or_numeric_suffix(
    raw_text: str, right_number: str, suffix_start: int
) -> bool:
    for suffix in _RIGHT_NUMBER_COUNTER_SUFFIXES:
        if not raw_text.startswith(suffix, suffix_start):
            continue
        suffix_end = suffix_start + len(suffix)
        if not _registered_suffix_boundary(raw_text, suffix, suffix_end):
            continue
        if suffix in COUNTERS_BY_LENGTH:
            if counter_number_reading(right_number, suffix) is None:
                continue
            return True
        return read_number_text(right_number) is not None
    return False


def _blocks_registered_suffixes(
    raw_text: str,
    suffix_start: int,
    right_number: str,
    suffixes: tuple[str, ...],
    *,
    numeric_reader,
) -> bool:
    for suffix in suffixes:
        if not raw_text.startswith(suffix, suffix_start):
            continue
        suffix_end = suffix_start + len(suffix)
        if not _registered_suffix_boundary(raw_text, suffix, suffix_end):
            continue
        if numeric_reader(right_number, suffix) is None:
            continue
        return True
    return False


def _blocks_clock_suffix(raw_text: str, right_number: str, suffix_start: int) -> bool:
    normalized = normalize_integer_text(right_number)
    if normalized is None:
        return False
    for suffix in _RIGHT_NUMBER_CLOCK_SUFFIXES:
        if not raw_text.startswith(suffix, suffix_start):
            continue
        suffix_end = suffix_start + len(suffix)
        if not _registered_suffix_boundary(raw_text, suffix, suffix_end):
            continue
        hour = int(normalized)
        return 1 <= hour <= 24
    return False


def _readable_unsigned_number_or_fraction(raw_number: str) -> str | None:
    if "/" in raw_number:
        if raw_number.count("/") != 1:
            return None
        numerator, denominator = raw_number.split("/", 1)
        return read_fraction_text(numerator, denominator)
    if raw_number.startswith(("+", "-")):
        return None
    return read_number_text(raw_number)


def _registered_suffix_boundary(raw_text: str, suffix: str, suffix_end: int) -> bool:
    next_char = raw_text[suffix_end] if suffix_end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isspace():
        return True
    if next_char in _SENTENCE_PUNCTUATION or next_char in {")", "]", "}"}:
        return True
    if next_char.isascii():
        return True
    if not _is_complete_hangul(next_char):
        return True
    if suffix not in _AMBIGUOUS_DATE_SUFFIXES:
        return raw_text.startswith(_OWNER_ATTACHED_HANGUL_TAILS, suffix_end)
    return raw_text.startswith(_AMBIGUOUS_DATE_OWNER_PARTICLES, suffix_end)


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
