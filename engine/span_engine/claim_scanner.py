from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.claim_registry import SurfaceClaimRegistry
from engine.span_engine.currency import (
    is_currency_code_contaminated_token,
    is_currency_like_code,
    is_number_after_unsupported_currency_code,
    scan_currency_candidates,
)
from engine.span_engine.counter import (
    is_emergency_ambiguous_number,
    scan_counter_candidates,
)
from engine.span_engine.administrative import (
    is_unsafe_admin_like_number_tail,
    scan_administrative_suffix_candidates,
)
from engine.span_engine.compound_unit import (
    scan_compound_exact_unit_candidates,
    scan_compound_slash_unit_candidates,
    starts_with_supported_compound_exact_unit,
)
from engine.span_engine.code_separator import (
    scan_mixed_alnum_code_separator_candidates,
    scan_spaced_hyphen_numeric_candidates,
    scan_single_letter_alnum_code_candidates,
    scan_two_block_hyphen_code_candidates,
)
from engine.span_engine.date_time import scan_date_candidates, scan_time_candidates
from engine.span_engine.decimal import scan_decimal_candidates
from engine.span_engine.delimiters import (
    COLON_LIKE_DELIMITERS,
    RANGE_LIKE_DELIMITERS,
    TILDE_LIKE_DELIMITERS,
)
from engine.span_engine.duration import scan_duration_candidates
from engine.span_engine.emergency import scan_emergency_candidates
from engine.span_engine.event import scan_event_candidates
from engine.span_engine.fraction import scan_fraction_candidates
from engine.span_engine.middle_dot import scan_middle_dot_candidates
from engine.span_engine.numeric_suffix import scan_numeric_suffix_candidates
from engine.span_engine.ph import scan_ph_candidates
from engine.span_engine.percent_point import scan_percent_point_candidates
from engine.span_engine.protected import scan_protected_literal_candidates
from engine.span_engine.separator import scan_spaced_separator_preserve_candidates
from engine.span_engine.hyphen import scan_hyphen_digit_candidates
from engine.span_engine.jamo import scan_jamo_candidates
from engine.span_engine.large_unit import scan_large_unit_candidates
from engine.span_engine.lexicon import (
    DICTIONARY_READINGS,
    scan_acronym_hangul_hyphen_candidates,
    scan_k_hangul_lexical_candidates,
    scan_finance_index_numeric_suffix_candidates,
    scan_lexical_compound_candidates,
)
from engine.span_engine.models import ClaimedRange, SourceSpan, SpanToken, SurfaceCandidate
from engine.span_engine.numeric_reading import normalize_integer_text
from engine.span_engine.public_number import is_public_number, scan_public_number_candidates
from engine.span_engine.phone import scan_phone_candidates
from engine.span_engine.range import (
    scan_colon_semantic_pair_candidates,
    scan_multi_colon_numeric_candidates,
    scan_numeric_delimited_hyphen_range_candidates,
    scan_range_candidates,
)
from engine.span_engine.signed import (
    scan_signed_degree_candidates,
    scan_signed_temperature_candidates,
    scan_signed_number_candidates,
)
from engine.span_engine.units import (
    scan_simple_unit_candidates,
    scan_special_unit_candidates,
    scan_unit_contamination_preserve_candidates,
    supported_unit_prefix_length,
    starts_with_supported_unit,
)

_ASCII_INTEGER_RE = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+")
_UPPERCASE_ACRONYM_RE = re.compile(r"[A-Z]{2,}")

_NUMBER_BLOCKING_KOREAN_SUFFIXES = (
    "명",
    "개",
    "월",
    "일",
    "년",
    "원",
    "도",
    "만",
    "억",
    "조",
    "차례",
    "건",
    "곳",
    "팀",
    "쌍",
    "상자",
    "봉지",
    "통",
    "묶음",
    "편",
    "판",
    "줄",
    "칸",
    "대",
    "석",
    "표",
    "매",
    "문항",
    "문제",
    "곡",
    "장면",
    "세트",
    "팩",
    "봉",
    "종류",
    "항목",
    "사례",
)

_NUMBER_BLOCKING_NEXT_CHARS = (
    frozenset(",-+/_") | COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS | TILDE_LIKE_DELIMITERS
)
_NUMBER_BLOCKING_PREV_CHARS = (
    frozenset(",+/_") | COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS | TILDE_LIKE_DELIMITERS
)
_NUMBER_BLOCKING_PREV_SYMBOLS = frozenset("$€£¥₩")
_ACRONYM_FALLBACK_BLOCKLIST = frozenset(
    {
        "CM",
        "DB",
        "GB",
        "GHZ",
        "G",
        "HZ",
        "KB",
        "KG",
        "KHZ",
        "KM",
        "L",
        "M",
        "MB",
        "MG",
        "MHZ",
        "ML",
        "MM",
        "AUD",
        "AM",
        "BTC",
        "CAD",
        "CHF",
        "CNY",
        "EUR",
        "GBP",
        "JPY",
        "KRW",
        "PM",
        "SGD",
        "USD",
        "US",
        "V",
        "W",
    }
)

# Documentation-only snapshot of the high-level claim precedence.
# Keep this in sync with the scanner calls in claim_surfaces() and policy section 9.1.
# "bracket" is applied before claim_surfaces() through excluded_ranges; the remaining
# entries follow the scanner call order below. This tuple is intentionally not used to
# drive execution, so refactors cannot change claim order by editing documentation.
CLAIM_ORDER_DOC = (
    "bracket",
    "protected_literal",
    "dictionary",
    "finance_index",
    "k_hangul_lexical",
    "lexical_compound",
    "acronym_hangul_hyphen",
    "single_letter_alnum_code",
    "two_block_hyphen_code",
    "mixed_alnum_code_separator",
    "acronym_fallback",
    "large_unit_atomic",
    "currency",
    "date",
    "time",
    "colon_semantic_pair",
    "multi_colon_numeric",
    "event",
    "emergency",
    "spaced_separator_preserve",
    "spaced_hyphen_numeric_blocks",
    "numeric_delimited_hyphen_range",
    "range",
    "percent_point",
    "duration",
    "unit_contamination_preserve",
    "fraction",
    "signed_temperature",
    "signed_degree",
    "signed_number",
    "ph",
    "compound_slash_unit",
    "compound_exact_unit",
    "special_unit",
    "simple_unit",
    "numeric_suffix",
    "decimal",
    "middle_dot_numeric",
    "public_number",
    "counter_noun",
    "phone",
    "hyphen_digit_blocks",
    "jamo",
    "administrative_suffix",
    "number",
)


def claim_surfaces(
    raw_text: str,
    tokens: list[SpanToken],
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange] | None = None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(tokens, list):
        raise TypeError("tokens must be list[SpanToken]")
    if not isinstance(registry, SurfaceClaimRegistry):
        raise TypeError("registry must be SurfaceClaimRegistry")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    candidates.extend(_claim_scanned_candidates(scan_protected_literal_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_dictionary(raw_text, tokens, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_finance_index_numeric_suffix_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_k_hangul_lexical_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_lexical_compound_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_acronym_hangul_hyphen_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_single_letter_alnum_code_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_two_block_hyphen_code_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_mixed_alnum_code_separator_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_acronym_fallback(tokens, registry, excluded_ranges))
    candidates.extend(_claim_large_unit_candidates(raw_text, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_currency_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_date_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_time_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_colon_semantic_pair_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_multi_colon_numeric_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_event_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_emergency_candidates(raw_text, excluded_ranges), registry, excluded_ranges))

    candidates.extend(_claim_scanned_candidates(scan_spaced_separator_preserve_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_spaced_hyphen_numeric_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_numeric_delimited_hyphen_range_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_range_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_percent_point_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_duration_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_unit_contamination_preserve_candidates(raw_text), registry, excluded_ranges))

    # Priority: signed and unit owners must full-consume before generic decimals.
    candidates.extend(_claim_scanned_candidates(scan_fraction_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_signed_temperature_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_signed_degree_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_signed_number_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_ph_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_compound_slash_unit_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_compound_exact_unit_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_special_unit_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_simple_unit_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_numeric_suffix_candidates(raw_text), registry, excluded_ranges))

    candidates.extend(_claim_scanned_candidates(scan_decimal_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_middle_dot_candidates(raw_text, excluded_ranges), registry, excluded_ranges))

    candidates.extend(_claim_scanned_candidates(scan_public_number_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_counter_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_phone_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_hyphen_digit_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_jamo_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_administrative_suffix_candidates(raw_text, excluded_ranges), registry, excluded_ranges))

    candidates.extend(_claim_numbers(raw_text, registry, excluded_ranges))
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def _claim_dictionary(
    raw_text: str,
    tokens: list[SpanToken],
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for token in tokens:
        if not isinstance(token, SpanToken):
            raise TypeError("tokens must contain SpanToken")
        if token.kind != "PLAIN" or _span_overlaps_excluded_range(token.span, excluded_ranges):
            continue
        for surface in sorted(DICTIONARY_READINGS, key=len, reverse=True):
            start = token.raw.find(surface)
            while start != -1:
                end = start + len(surface)
                span = SourceSpan(token.span.start + start, token.span.start + end)
                if (
                    _safe_fixed_dictionary_boundary(token.raw, start, end)
                    and _safe_numeric_dictionary_boundary(raw_text, span, surface)
                    and not _span_overlaps_excluded_range(span, excluded_ranges)
                    and registry.can_claim(span, "dictionary")
                ):
                    candidate = SurfaceCandidate(
                        core_span=span,
                        full_span=span,
                        owner="dictionary",
                        surface_type="ACRONYM_SURFACE",
                        reason="dictionary_fixed_lexical_match",
                    )
                    _claim_candidate(candidate, registry)
                    candidates.append(candidate)
                start = token.raw.find(surface, start + 1)
    return candidates


def _claim_acronym_fallback(
    tokens: list[SpanToken],
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for token in tokens:
        if token.kind != "PLAIN":
            continue
        for match in _UPPERCASE_ACRONYM_RE.finditer(token.raw):
            raw = match.group(0)
            span = SourceSpan(
                token.span.start + match.start(),
                token.span.start + match.end(),
            )
            if (
                not _is_safe_acronym_fallback_token(raw)
                or not _safe_acronym_fallback_boundary(
                    token.raw, match.start(), match.end()
                )
                or _span_overlaps_excluded_range(span, excluded_ranges)
                or not registry.can_claim(span, "acronym_fallback")
            ):
                continue
            candidate = SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="acronym_fallback",
                surface_type="ACRONYM_FALLBACK_SURFACE",
                reason="safe_uppercase_acronym_fallback",
            )
            _claim_candidate(candidate, registry)
            candidates.append(candidate)
    return candidates


def _claim_numbers(
    raw_text: str,
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _ASCII_INTEGER_RE.finditer(raw_text):
        raw = match.group(0)
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if not _is_supported_number(raw_text, span, raw):
            continue
        if not registry.can_claim(span, "number"):
            continue
        candidate = SurfaceCandidate(
            core_span=span,
            full_span=span,
            owner="number",
            surface_type="NUMBER_SURFACE",
            reason="phase7_minimal_ascii_number",
        )
        _claim_candidate(candidate, registry)
        candidates.append(candidate)
    return candidates


def _claim_scanned_candidates(
    scanned_candidates: list[SurfaceCandidate],
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for candidate in scanned_candidates:
        if _span_overlaps_excluded_range(candidate.core_span, excluded_ranges):
            continue
        if not registry.can_claim(candidate.core_span, candidate.owner):
            continue
        _claim_candidate(candidate, registry)
        candidates.append(candidate)
    return candidates


def _claim_large_unit_candidates(
    raw_text: str,
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for candidate in scan_large_unit_candidates(raw_text):
        if _span_overlaps_excluded_range(
            candidate.core_span, excluded_ranges
        ) and not _large_unit_span_allowed_by_trailing_incomplete_bracket(
            candidate.core_span, excluded_ranges
        ):
            continue
        if not registry.can_claim(candidate.core_span, candidate.owner):
            continue
        _claim_candidate(candidate, registry)
        candidates.append(candidate)
    return candidates


def _large_unit_span_allowed_by_trailing_incomplete_bracket(
    span: SourceSpan,
    excluded_ranges: list[BracketRange],
) -> bool:
    return any(
        bracket_range.complete is False
        and bracket_range.raw.endswith((")", "]"))
        and span == bracket_range.inner_span
        for bracket_range in excluded_ranges
    )


def _claim_candidate(
    candidate: SurfaceCandidate, registry: SurfaceClaimRegistry
) -> None:
    registry.claim(
        ClaimedRange(
            span=candidate.core_span,
            owner=candidate.owner,
            claim_type="preserve" if candidate.owner == "preserve" else "surface",
            surface_type=candidate.surface_type,
            reason=candidate.reason,
        )
    )


def _safe_fixed_dictionary_boundary(raw: str, start: int, end: int) -> bool:
    prev_char = raw[start - 1] if start > 0 else None
    next_char = raw[end] if end < len(raw) else None
    if prev_char is not None and _is_fixed_dictionary_identifier_neighbor(prev_char):
        return False
    if next_char is not None and _is_fixed_dictionary_identifier_neighbor(next_char):
        return False
    return True


def _safe_numeric_dictionary_boundary(
    raw_text: str, span: SourceSpan, surface: str
) -> bool:
    if not surface[:1].isdigit():
        return True
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None and _is_fixed_dictionary_identifier_neighbor(prev_char):
        return False
    if next_char is not None and _is_fixed_dictionary_identifier_neighbor(next_char):
        return False
    return True


def _is_fixed_dictionary_identifier_neighbor(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\uac00" <= char <= "\ud7a3" or "\u3130" <= char <= "\u318f":
        return True
    return char in {"-", "_", "/"}


def _is_safe_acronym_fallback_token(raw: str) -> bool:
    if _UPPERCASE_ACRONYM_RE.fullmatch(raw) is None:
        return False
    if raw in DICTIONARY_READINGS:
        return False
    if is_currency_like_code(raw):
        return False
    if is_currency_code_contaminated_token(raw):
        return False
    if raw in _ACRONYM_FALLBACK_BLOCKLIST:
        return False
    # Avoid ambiguous partial dictionary/fallback splits such as AIP or AIA.
    return not any(dictionary_key in raw for dictionary_key in DICTIONARY_READINGS)


def _safe_acronym_fallback_boundary(token_raw: str, start: int, end: int) -> bool:
    prev_char = token_raw[start - 1] if start > 0 else None
    next_char = token_raw[end] if end < len(token_raw) else None
    if prev_char is not None and prev_char.isascii() and prev_char.isalnum():
        return False
    if prev_char in {"_", "-", "/"}:
        return False
    if next_char is not None and next_char.isascii() and next_char.isalnum():
        return False
    if next_char in {"_", "-", "/"}:
        return False
    return True


def _is_supported_number(raw_text: str, span: SourceSpan, raw: str) -> bool:
    if normalize_integer_text(raw) is None:
        return False

    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_next_char = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
    next_non_space = raw_text[span.end :].lstrip()
    prev_non_space = raw_text[: span.start].rstrip()

    # Pre-checks (context that applies even if next_char is None)
    if prev_char in {".", "·"}:
        digit_before = raw_text[span.start - 2].isdigit() if span.start > 1 else False
        sign_before = raw_text[span.start - 2] in {"+", "-"} if span.start > 1 else False
        if digit_before:
            return False
        if sign_before:
            return False
        if prev_char == "." and next_char in (COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS):
            return False

    if _is_url_or_path_context(raw_text, span):
        return False

    if _has_invalid_spaced_ordinal_prefix(raw_text, span.start):
        return False

    if raw_text.startswith("대", span.end) and _consume_ascii_digits(raw_text, span.end + 1) > span.end + 1:
        return _is_first_number_in_compact_dae_relation(raw_text, span)
    if _is_hangul_embedded_number_context(raw_text, span):
        return True

    if prev_char is not None:
        if _is_compatibility_jamo(prev_char):
            return False
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3" and not _is_second_number_in_compact_dae_relation(raw_text, span):
            return False
        if prev_char in _NUMBER_BLOCKING_PREV_CHARS:
            return False
        if prev_char in _NUMBER_BLOCKING_PREV_SYMBOLS:
            return False
    
    if prev_non_space and prev_non_space[-1] in (RANGE_LIKE_DELIMITERS | {"∼"}):
        return False
    if is_number_after_unsupported_currency_code(raw_text, span.start):
        return False

    # Next-char checks
    if next_char is None:
        return True
    
    if _is_compatibility_jamo(next_char):
        return False
    if next_char.isspace() and next_non_space[:1] in (RANGE_LIKE_DELIMITERS | {"∼"}):
        return False
    if next_char.isspace() and starts_with_supported_unit(next_non_space):
        return False
    if next_char.isspace() and starts_with_supported_compound_exact_unit(next_non_space):
        return False
    if is_unsafe_admin_like_number_tail(raw_text, span.end):
        return False
    
    unit_prefix_length = supported_unit_prefix_length(raw_text[span.end :])
    if unit_prefix_length is not None:
        unit_suffix = raw_text[span.end + unit_prefix_length :].lstrip()
        if unit_suffix.startswith("/"):
            return False
            
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char == ",":
        return next_next_char is None or next_next_char.isspace()
    if next_char in _NUMBER_BLOCKING_NEXT_CHARS:
        return False

    if next_char in {".", "·"}:
        if next_char == "." and next_next_char in (COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS):
            return False
        if raw_text[span.end + 1 : span.end + 2].isdigit():
            return False
        if next_char == "." and not (next_next_char is not None and next_next_char.isdigit()):
            # This is 12. followed by non-digit. Allowed.
            pass
        elif next_char == "·":
            # 12· followed by non-digit. Blocked.
            return False

    if "\uac00" <= next_char <= "\ud7a3":
        if "," in raw and raw_text[span.end :].startswith("가"):
            return False
        suffix = raw_text[span.end :]
        if is_emergency_ambiguous_number(raw) or is_public_number(raw):
            return True
        return not suffix.startswith(_NUMBER_BLOCKING_KOREAN_SUFFIXES)

    return True


def _is_first_number_in_compact_dae_relation(
    raw_text: str, span: SourceSpan
) -> bool:
    if not raw_text.startswith("대", span.end):
        return False
    right_start = span.end + 1
    right_end = _consume_ascii_digits(raw_text, right_start)
    if right_end == right_start:
        return False
    return _valid_compact_dae_relation(raw_text, span.start, span.end, right_start, right_end)


def _is_second_number_in_compact_dae_relation(
    raw_text: str, span: SourceSpan
) -> bool:
    if span.start < 2 or raw_text[span.start - 1] != "대":
        return False
    left_end = span.start - 1
    left_start = left_end
    while left_start > 0 and raw_text[left_start - 1].isdigit():
        left_start -= 1
    if left_start == left_end:
        return False
    return _valid_compact_dae_relation(raw_text, left_start, left_end, span.start, span.end)


def _valid_compact_dae_relation(
    raw_text: str,
    left_start: int,
    left_end: int,
    right_start: int,
    right_end: int,
) -> bool:
    left = raw_text[left_start:left_end]
    right = raw_text[right_start:right_end]
    if normalize_integer_text(left) is None or normalize_integer_text(right) is None:
        return False
    prev_char = raw_text[left_start - 1] if left_start > 0 else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3" or "\u3130" <= prev_char <= "\u318f":
            return False
        if prev_char in {"_", "-", "/", "."}:
            return False
    next_char = raw_text[right_end] if right_end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char == "_":
        return False
    if "\uac00" <= next_char <= "\ud7a3":
        return raw_text.startswith(("은", "는", "이", "가", "을", "를", "로", "도"), right_end)
    return True


def _is_hangul_embedded_number_context(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if not (_is_complete_hangul(prev_char) and _is_complete_hangul(next_char)):
        return False
    if next_char == "대" and _consume_ascii_digits(raw_text, span.end + 1) > span.end + 1:
        return False
    prefix_start = span.start - 1
    while prefix_start > 0 and _is_complete_hangul(raw_text[prefix_start - 1]):
        prefix_start -= 1
    prefix_prev = raw_text[prefix_start - 1] if prefix_start > 0 else None
    if prefix_prev is None:
        return True
    if prefix_prev.isascii() and prefix_prev.isalnum():
        return False
    return prefix_prev not in {"_", "-", "/", "."}


def _consume_ascii_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isdigit():
        index += 1
    return index


def _has_invalid_spaced_ordinal_prefix(raw_text: str, number_start: int) -> bool:
    if not (
        number_start > 1
        and raw_text[number_start - 1] == " "
        and raw_text[number_start - 2] == "제"
    ):
        return False
    prefix_start = number_start - 2
    return prefix_start > 0 and not raw_text[prefix_start - 1].isspace()


def _is_complete_hangul(char: str | None) -> bool:
    return isinstance(char, str) and "\uac00" <= char <= "\ud7a3"


def _is_url_or_path_context(raw_text: str, span: SourceSpan) -> bool:
    # Check for :// before the number
    left_context = raw_text[max(0, span.start - 10) : span.start]
    if "://" in left_context:
        return True
    # Check if part of a path-like structure (e.g., /2025/01/03)
    # If immediately preceded by /, it's likely a path.
    if span.start > 0 and raw_text[span.start - 1] == "/":
        return True
    # If preceded by / and some digits/dots/dashes (e.g., /12.3)
    prev_non_space = raw_text[: span.start].rstrip()
    if "/" in prev_non_space:
        last_slash = prev_non_space.rfind("/")
        between = prev_non_space[last_slash + 1 :]
        if all(c.isdigit() or c in ".-·" for c in between):
            # If there's a slash and only numeric-like chars between it and us
            # and no space after the slash, it's likely a path.
            if last_slash < len(raw_text) - 1 and not raw_text[last_slash + 1].isspace():
                 return True
    return False


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


def _is_compatibility_jamo(ch: str) -> bool:
    return "\u3130" <= ch <= "\u318f"


__all__ = ["CLAIM_ORDER_DOC", "claim_surfaces"]
