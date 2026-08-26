from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import (
    INTEGER_ONLY_SPECIAL_DETERMINER_UNITS,
    SUPPORTED_COUNTERS,
)
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    read_decimal_text,
    read_sino_time_suffix_number_text,
)
from engine.span_engine.sign_aliases import (
    SIGNED_NUMERIC_SIGN_ALIASES,
    is_signed_numeric_sign,
)
from engine.span_engine.signed_numeric import (
    apply_sign_profile,
    parse_signed_numeric_core,
    render_signed_numeric,
)
from engine.span_engine.numeric_suffix import NUMERIC_SUFFIXES, has_ordinal_je_prefix
from engine.span_engine.numeric_dae import evaluate_numeric_dae_counter_context
from engine.span_engine.span_guards import (
    is_decimal_like_url_or_path_context,
    span_overlaps_excluded_ranges,
)

_SIGN_PATTERN = re.escape("".join(sorted(SIGNED_NUMERIC_SIGN_ALIASES)))
_DECIMAL_RE = re.compile(
    rf"[{_SIGN_PATTERN}]?(?:\d{{1,3}}(?:,\d{{3}})+|\d+)\.\d+"
)
_APPROVED_DURATION_SUFFIXES = frozenset({"주"})
REGISTERED_DECIMAL_SUFFIXES = (
    frozenset(SUPPORTED_COUNTERS)
    | frozenset(NUMERIC_SUFFIXES)
    | _APPROVED_DURATION_SUFFIXES
) - INTEGER_ONLY_SPECIAL_DETERMINER_UNITS
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
    "의",
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
    "쯤",
    "정도",
    "꼴",
    "당",
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
        candidate = _candidate_at_suffix(raw_text, decimal_span)
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
    raw_text: str, decimal_span: SourceSpan
) -> SurfaceCandidate | None:
    suffix_start = decimal_span.end
    for suffix in _ORDERED_SUFFIXES:
        if not raw_text.startswith(suffix, suffix_start):
            continue
        raw_number = raw_text[decimal_span.start : decimal_span.end]
        reading = _signed_decimal_reading(raw_number, suffix)
        if reading is None:
            return None
        suffix_end = suffix_start + len(suffix)
        if not _suffix_boundary_is_safe(raw_text, suffix_end):
            return _preserve_candidate(
                SourceSpan(
                    decimal_span.start,
                    _registered_suffix_like_token_end(raw_text, suffix_end),
                ),
                "decimal_registered_suffix_unsafe_tail_preserve",
            )
        reason = "decimal_registered_suffix_gate"
        if suffix == "대":
            decision = evaluate_numeric_dae_counter_context(
                raw_text, SourceSpan(decimal_span.start, suffix_end)
            )
            if decision.action != "DEFER_TO_COUNTER":
                return None
            reason = decision.reason
        return SurfaceCandidate(
            core_span=decimal_span,
            full_span=SourceSpan(decimal_span.start, suffix_end),
            owner="decimal_registered_suffix",
            surface_type="DECIMAL_REGISTERED_SUFFIX_SURFACE",
            suffix_spans=[SourceSpan(suffix_start, suffix_end)],
            reason=reason,
            metadata={
                "number": raw_text[decimal_span.start : decimal_span.end],
                "suffix": suffix,
                "suffix_span": SourceSpan(suffix_start, suffix_end),
                "reading": f"{reading} ",
                **_signed_contract_metadata(raw_number),
            },
        )
    return None


def _scan_malformed_decimal_suffix_preserves(
    raw_text: str, excluded_ranges: list[BracketRange]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (
            _is_ascii_digit(raw_text[index])
            or raw_text[index] == "."
            or is_signed_numeric_sign(raw_text[index])
        ):
            index += 1
            continue
        numeric_start = index
        unsigned_start = (
            numeric_start + 1
            if is_signed_numeric_sign(raw_text[numeric_start])
            else numeric_start
        )
        numeric_end = _consume_decimal_like_surface(raw_text, unsigned_start)
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
        reading = _signed_decimal_reading(
            raw_number, raw_text[suffix_start:suffix_end]
        )
        if reading is not None and _suffix_boundary_is_safe(raw_text, suffix_end):
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
    if has_ordinal_je_prefix(raw_text, start):
        return False
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


def _signed_decimal_reading(raw_number: str, suffix: str) -> str | None:
    if suffix in {"분", "초"} and not is_signed_numeric_sign(raw_number[0]):
        return read_sino_time_suffix_number_text(raw_number)
    core = parse_signed_numeric_core(raw_number)
    if core is None or not core.has_decimal:
        return None
    if suffix not in {"분", "초"}:
        return render_signed_numeric(core)
    reading = read_sino_time_suffix_number_text(core.number.raw)
    if reading is None:
        return None
    return apply_sign_profile(reading, core.sign_kind)


def _signed_contract_metadata(raw_number: str) -> dict[str, object]:
    core = parse_signed_numeric_core(raw_number)
    if core is None:
        return {}
    return {
        "sign_profile": "default",
        "numeric_form": core.numeric_form,
        "sign_surface": core.sign_surface,
    }


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
