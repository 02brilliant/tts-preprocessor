from __future__ import annotations

import re

from engine.span_engine.arithmetic import (
    scan_basic_arithmetic_expression_candidates,
    scan_invalid_basic_arithmetic_preserve_candidates,
)
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
from engine.span_engine.contextual_number_unit import (
    scan_contextual_large_unit_collision_candidates,
    scan_contextual_large_unit_malformed_candidates,
    scan_contextual_non_large_unit_malformed_candidates,
    scan_contextual_number_unit_candidates,
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
from engine.span_engine.corporate_marker import scan_corporate_marker_candidates
from engine.span_engine.code_separator import (
    scan_mixed_alnum_code_separator_candidates,
    scan_spaced_hyphen_numeric_candidates,
    scan_single_letter_alnum_code_candidates,
    scan_two_block_hyphen_code_candidates,
)
from engine.span_engine.date_time import scan_date_candidates, scan_time_candidates
from engine.span_engine.decimal import (
    scan_decimal_candidates,
    scan_malformed_dotted_preserve_candidates,
)
from engine.span_engine.decimal_registered_suffix import (
    scan_decimal_registered_suffix_candidates,
)
from engine.span_engine.delimiters import (
    COLON_LIKE_DELIMITERS,
    RANGE_LIKE_DELIMITERS,
    TILDE_LIKE_DELIMITERS,
)
from engine.span_engine.duration import scan_duration_candidates
from engine.span_engine.emergency import scan_emergency_candidates
from engine.span_engine.event import scan_event_candidates
from engine.span_engine.fraction import (
    scan_fraction_candidates,
    scan_textual_fraction_candidates,
)
from engine.span_engine.middle_dot import (
    scan_middle_dot_candidates,
    scan_middle_dot_korean_suffix_candidates,
)
from engine.span_engine.mixed_integer import scan_mixed_integer_candidates
from engine.span_engine.multiplier import scan_multiplier_candidates
from engine.span_engine.numeric_dae import (
    scan_ambiguous_numeric_dae_preserve_candidates,
)
from engine.span_engine.numeric_suffix import scan_numeric_suffix_candidates
from engine.span_engine.ordinal import scan_ordinal_candidates
from engine.span_engine.parenthesized_hangul_alias import (
    scan_parenthesized_hangul_alias_candidates,
)
from engine.span_engine.ph import scan_ph_candidates
from engine.span_engine.percent_point import scan_percent_point_candidates
from engine.span_engine.protected import scan_protected_literal_candidates
from engine.span_engine.separator import scan_spaced_separator_preserve_candidates
from engine.span_engine.hyphen import scan_hyphen_digit_candidates
from engine.span_engine.jamo import scan_jamo_candidates
from engine.span_engine.korean_da_score_pair import scan_korean_da_score_pair_candidates
from engine.span_engine.korean_numeric_chain import scan_korean_numeric_chain_candidates
from engine.span_engine.large_unit import scan_large_unit_candidates
from engine.span_engine.lexicon import (
    DICTIONARY_READINGS,
    PHRASE_DICTIONARY_READINGS,
    scan_ampersand_acronym_candidates,
    scan_acronym_hangul_hyphen_candidates,
    scan_contextual_acronym_candidates,
    scan_k_hangul_lexical_candidates,
    scan_finance_index_numeric_suffix_candidates,
    scan_lexical_compound_candidates,
    scan_unsupported_ampersand_acronym_preserve_candidates,
)
from engine.span_engine.profile import uses_general_english_fallbacks
from engine.span_engine.managed_numeric_code import (
    scan_managed_acronym_numeric_code_candidates,
)
from engine.span_engine.models import ClaimedRange, SourceSpan, SpanToken, SurfaceCandidate
from engine.span_engine.numeric_reading import normalize_integer_text
from engine.span_engine.public_number import is_public_number, scan_public_number_candidates
from engine.span_engine.phone import scan_phone_candidates
from engine.span_engine.range import (
    scan_colon_semantic_pair_candidates,
    scan_compact_large_unit_range_candidates,
    scan_multi_colon_numeric_candidates,
    scan_numeric_delimited_hyphen_range_candidates,
    scan_range_candidates,
)
from engine.span_engine.signed import (
    scan_compound_signed_number_candidates,
    scan_invalid_signed_numeric_preserve_candidates,
    scan_signed_degree_candidates,
    scan_signed_temperature_candidates,
    scan_signed_number_candidates,
)
from engine.span_engine.span_guards import span_overlaps_excluded_ranges
from engine.span_engine.units import (
    scan_caret_power_unit_candidates,
    scan_caret_literal_unit_candidates,
    scan_simple_unit_candidates,
    scan_special_unit_candidates,
    scan_hangul_context_unit_candidates,
    scan_korean_numeric_unit_candidates,
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
    "척",
)

_NUMBER_BLOCKING_NEXT_CHARS = (
    frozenset(",-+/_") | COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS | TILDE_LIKE_DELIMITERS
)
_NUMBER_BLOCKING_PREV_CHARS = (
    frozenset(",+/_") | COLON_LIKE_DELIMITERS | RANGE_LIKE_DELIMITERS | TILDE_LIKE_DELIMITERS
)
_NUMBER_BLOCKING_PREV_SYMBOLS = frozenset("$€£¥₩")
_ATTACHED_MIDDLE_DOT_KOREAN_TEMPORAL_LITERAL_RE = re.compile(
    r"·[가-힣]+(?:분기|월|일)(?![A-Za-z0-9])"
)
_ACRONYM_FALLBACK_BLOCKLIST = frozenset(
    {
        "CM",
        "DB",
        "GB",
        "GHZ",
        "GPA",
        "G",
        "GW",
        "HPA",
        "HZ",
        "KB",
        "KG",
        "KHZ",
        "KM",
        "KPA",
        "L",
        "M",
        "MB",
        "MG",
        "MHZ",
        "ML",
        "MM",
        "MW",
        "PA",
        "PB",
        "TB",
        "THZ",
        "TW",
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
    "corporate_marker",
    "parenthesized_hangul_alias",
    "phrase_dictionary",
    "dictionary",
    "finance_index",
    "contextual_acronym",
    "ampersand_acronym",
    "unsupported_ampersand_acronym_preserve",
    "k_hangul_lexical",
    "lexical_compound",
    "acronym_hangul_hyphen",
    "single_letter_alnum_code",
    "managed_acronym_numeric_code",
    "two_block_hyphen_code",
    "mixed_alnum_code_separator",
    "acronym_fallback",
    "contextual_malformed_number_unit",
    "contextual_large_unit_collision",
    "large_unit_atomic",
    "currency",
    "date",
    "time",
    "phone",
    "colon_semantic_pair",
    "korean_da_score_pair",
    "numeric_dae_quantity_sequence",
    "multi_colon_numeric",
    "event",
    "emergency",
    "middle_dot_numeric",
    "spaced_separator_preserve",
    "spaced_hyphen_numeric_blocks",
    "numeric_delimited_hyphen_range",
    "range",
    "hyphen_digit_blocks",
    "percent_point",
    "duration",
    "multiplier",
    "caret_literal_unit",
    "unit_contamination_preserve",
    "caret_power_unit",
    "basic_arithmetic_expression",
    "invalid_basic_arithmetic_expression_preserve",
    "fraction",
    "signed_temperature",
    "signed_degree",
    "ph",
    "compound_signed_number",
    "signed_number",
    "compound_slash_unit",
    "compound_exact_unit",
    "special_unit",
    "simple_unit",
    "contextual_number_unit",
    "decimal_registered_suffix",
    "numeric_suffix",
    "contextual_numeric_dae",
    "ambiguous_numeric_dae_preserve",
    "invalid_signed_numeric_preserve",
    "invalid_mixed_decimal_preserve",
    "mixed_decimal_atomic",
    "decimal",
    "public_number",
    "counter_noun",
    "mixed_integer_atomic",
    "jamo",
    "administrative_suffix",
    "korean_numeric_chain",
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
    korean_chain_candidates = scan_korean_numeric_chain_candidates(raw_text)
    unsafe_korean_chain_candidates = [
        candidate for candidate in korean_chain_candidates if candidate.owner == "preserve"
    ]
    safe_korean_chain_candidates = [
        candidate
        for candidate in korean_chain_candidates
        if candidate.owner == "korean_numeric_chain"
    ]
    counter_candidates = scan_counter_candidates(raw_text)
    large_unit_counter_candidates = [
        candidate
        for candidate in counter_candidates
        if candidate.metadata.get("full_counter_claim") is True
    ]
    compound_slash_unit_candidates = scan_compound_slash_unit_candidates(
        raw_text, excluded_ranges
    )
    simple_unit_candidates = scan_simple_unit_candidates(raw_text)
    hangul_context_unit_candidates = scan_hangul_context_unit_candidates(raw_text)
    korean_numeric_unit_candidates = scan_korean_numeric_unit_candidates(raw_text)
    unit_guard_candidates = [
        *simple_unit_candidates,
        *hangul_context_unit_candidates,
        *korean_numeric_unit_candidates,
    ]
    unit_contamination_candidates = scan_unit_contamination_preserve_candidates(
        raw_text
    )
    contextual_acronym_unit_candidates = [
        *compound_slash_unit_candidates,
        *simple_unit_candidates,
        *unit_contamination_candidates,
    ]
    contextual_dae_counter_candidates = [
        candidate
        for candidate in counter_candidates
        if candidate.metadata.get("counter") == "대"
        and candidate.reason
        in {
            "dae_counter_sino_threshold_40_plus",
            "dae_counter_registered_noun_direct_context",
            "dae_counter_registered_noun_adjacent_continuation",
            "dae_counter_registered_noun_topic_quantity_context",
        }
    ]
    remaining_counter_candidates = [
        candidate
        for candidate in counter_candidates
        if candidate not in contextual_dae_counter_candidates
        and candidate not in large_unit_counter_candidates
    ]
    mixed_numeric_candidates = scan_mixed_integer_candidates(raw_text)
    mixed_decimal_candidates = [
        candidate
        for candidate in mixed_numeric_candidates
        if candidate.owner == "mixed_decimal_atomic"
    ]
    mixed_decimal_preserve_candidates = [
        candidate
        for candidate in mixed_numeric_candidates
        if candidate.surface_type == "INVALID_MIXED_DECIMAL_PRESERVE_SURFACE"
    ]
    mixed_integer_candidates = [
        candidate
        for candidate in mixed_numeric_candidates
        if candidate.owner == "mixed_integer_atomic"
    ]
    middle_dot_candidates = scan_middle_dot_candidates(raw_text, excluded_ranges)
    middle_dot_korean_suffix_candidates = scan_middle_dot_korean_suffix_candidates(
        raw_text, excluded_ranges
    )
    equipment_middle_dot_candidates = [
        candidate
        for candidate in middle_dot_candidates
        if candidate.metadata.get("equipment_sequence") is True
    ]
    remaining_middle_dot_candidates = [
        candidate
        for candidate in middle_dot_candidates
        if candidate not in equipment_middle_dot_candidates
        and candidate not in middle_dot_korean_suffix_candidates
    ]
    candidates.extend(_claim_scanned_candidates(scan_protected_literal_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_corporate_marker_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(
        _claim_scanned_candidates(
            scan_parenthesized_hangul_alias_candidates(raw_text),
            registry,
            excluded_ranges,
        )
    )
    candidates.extend(_claim_phrase_dictionary(raw_text, registry, excluded_ranges))
    candidates.extend(_claim_dictionary(raw_text, tokens, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_finance_index_numeric_suffix_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_contextual_acronym_candidates(raw_text, contextual_acronym_unit_candidates), registry, excluded_ranges))
    if uses_general_english_fallbacks():
        candidates.extend(_claim_scanned_candidates(scan_ampersand_acronym_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_unsupported_ampersand_acronym_preserve_candidates(raw_text), registry, excluded_ranges))
    if uses_general_english_fallbacks():
        candidates.extend(_claim_scanned_candidates(scan_k_hangul_lexical_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_lexical_compound_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(
        _claim_scanned_candidates(
            scan_acronym_hangul_hyphen_candidates(
                raw_text,
                allow_unregistered_fallback=uses_general_english_fallbacks(),
            ),
            registry,
            excluded_ranges,
        )
    )
    candidates.extend(_claim_scanned_candidates(scan_single_letter_alnum_code_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_managed_acronym_numeric_code_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_two_block_hyphen_code_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_mixed_alnum_code_separator_candidates(raw_text), registry, excluded_ranges))
    if uses_general_english_fallbacks():
        candidates.extend(
            _claim_uppercase_hangul_fallback(
                raw_text, registry, excluded_ranges, unit_guard_candidates
            )
        )
        candidates.extend(
            _claim_acronym_fallback(
                tokens,
                registry,
                excluded_ranges,
                unit_guard_candidates,
            )
        )
    candidates.extend(_claim_scanned_candidates(scan_compound_signed_number_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_contextual_large_unit_malformed_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_contextual_large_unit_collision_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(large_unit_counter_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_compact_large_unit_range_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(korean_numeric_unit_candidates, registry, excluded_ranges))
    candidates.extend(_claim_large_unit_candidates(raw_text, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_currency_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(middle_dot_korean_suffix_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_date_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_textual_fraction_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_time_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_phone_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_colon_semantic_pair_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_korean_da_score_pair_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_multi_colon_numeric_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_event_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_emergency_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(equipment_middle_dot_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_spaced_separator_preserve_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_spaced_hyphen_numeric_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_numeric_delimited_hyphen_range_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_range_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_hyphen_digit_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_percent_point_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_contextual_non_large_unit_malformed_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_duration_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_multiplier_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_caret_literal_unit_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(unit_contamination_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_caret_power_unit_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(
        _claim_scanned_candidates(
            scan_basic_arithmetic_expression_candidates(raw_text, excluded_ranges),
            registry,
            excluded_ranges,
        )
    )
    candidates.extend(
        _claim_scanned_candidates(
            scan_invalid_basic_arithmetic_preserve_candidates(raw_text, excluded_ranges),
            registry,
            excluded_ranges,
        )
    )

    # Priority: signed and unit owners must full-consume before generic decimals.
    candidates.extend(_claim_scanned_candidates(scan_fraction_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_signed_temperature_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_signed_degree_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_ph_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_signed_number_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(compound_slash_unit_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_compound_exact_unit_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_special_unit_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(simple_unit_candidates, registry, excluded_ranges))
    # After numeric simple/special units and after acronym owners, so
    # `3kg` and attached `GB그룹` keep their existing claims.
    candidates.extend(_claim_scanned_candidates(hangul_context_unit_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_contextual_number_unit_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_ordinal_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_decimal_registered_suffix_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_numeric_suffix_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(contextual_dae_counter_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_ambiguous_numeric_dae_preserve_candidates(raw_text), registry, excluded_ranges))
    candidates.extend(
        _claim_scanned_candidates(
            scan_invalid_signed_numeric_preserve_candidates(
                raw_text,
                excluded_ranges,
            ),
            registry,
            excluded_ranges,
        )
    )

    candidates.extend(_claim_scanned_candidates(mixed_decimal_preserve_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(mixed_decimal_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_decimal_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_malformed_dotted_preserve_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(remaining_middle_dot_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_public_number_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(remaining_counter_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(mixed_integer_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(unsafe_korean_chain_candidates, registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_jamo_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(scan_administrative_suffix_candidates(raw_text, excluded_ranges), registry, excluded_ranges))
    candidates.extend(_claim_scanned_candidates(safe_korean_chain_candidates, registry, excluded_ranges))

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
        if token.kind != "PLAIN" or span_overlaps_excluded_ranges(token.span, excluded_ranges):
            continue
        for surface in sorted(DICTIONARY_READINGS, key=len, reverse=True):
            start = token.raw.find(surface)
            while start != -1:
                end = start + len(surface)
                span = SourceSpan(token.span.start + start, token.span.start + end)
                if (
                    _safe_fixed_dictionary_boundary(token.raw, start, end)
                    and _safe_numeric_dictionary_boundary(raw_text, span, surface)
                    and not span_overlaps_excluded_ranges(span, excluded_ranges)
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


def _claim_phrase_dictionary(
    raw_text: str,
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for surface in sorted(PHRASE_DICTIONARY_READINGS, key=len, reverse=True):
        start = raw_text.find(surface)
        while start != -1:
            end = start + len(surface)
            span = SourceSpan(start, end)
            if (
                _safe_fixed_dictionary_boundary(raw_text, start, end)
                and not span_overlaps_excluded_ranges(span, excluded_ranges)
                and registry.can_claim(span, "phrase_dictionary")
            ):
                candidate = SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="phrase_dictionary",
                    surface_type="PHRASE_DICTIONARY_SURFACE",
                    reason="dictionary_fixed_phrase_match",
                )
                _claim_candidate(candidate, registry)
                candidates.append(candidate)
            start = raw_text.find(surface, start + 1)
    return candidates


def _claim_acronym_fallback(
    tokens: list[SpanToken],
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
    simple_unit_candidates: list[SurfaceCandidate],
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
                or span_overlaps_excluded_ranges(span, excluded_ranges)
                or any(
                    candidate.core_span.start <= span.start
                    and span.end <= candidate.core_span.end
                    for candidate in simple_unit_candidates
                )
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


def _claim_uppercase_hangul_fallback(
    raw_text: str,
    registry: SurfaceClaimRegistry,
    excluded_ranges: list[BracketRange],
    simple_unit_candidates: list[SurfaceCandidate],
) -> list[SurfaceCandidate]:
    """Spell an all-caps block directly attached to a Korean lexical tail.

    This is deliberately narrower than broad acronym fallback: it enables
    lexical forms such as ``KG그룹`` without reclassifying ASCII identifiers or
    numeric unit surfaces.
    """
    candidates: list[SurfaceCandidate] = []
    for match in _UPPERCASE_ACRONYM_RE.finditer(raw_text):
        start, end = match.span()
        if end >= len(raw_text) or not ("\uac00" <= raw_text[end] <= "\ud7a3"):
            continue
        previous = raw_text[start - 1] if start > 0 else None
        if previous is not None and (
            previous.isascii() and previous.isalnum() or previous in {"_", "-", "/"}
        ):
            continue
        span = SourceSpan(start, end)
        if (
            span_overlaps_excluded_ranges(span, excluded_ranges)
            or any(
                unit_candidate.core_span.start <= span.start
                and span.end <= unit_candidate.core_span.end
                for unit_candidate in simple_unit_candidates
            )
            or not registry.can_claim(span, "acronym_fallback")
        ):
            continue
        candidate = SurfaceCandidate(
            core_span=span,
            full_span=span,
            owner="acronym_fallback",
            surface_type="ACRONYM_FALLBACK_SURFACE",
            reason="uppercase_acronym_hangul_lexical_fallback",
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
        if span_overlaps_excluded_ranges(span, excluded_ranges):
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
        if span_overlaps_excluded_ranges(candidate.core_span, excluded_ranges):
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
        if span_overlaps_excluded_ranges(
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
            claim_type=(
                "preserve"
                if candidate.owner == "preserve"
                or candidate.metadata.get("claim_type") == "preserve"
                else "surface"
            ),
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
    return char in {"-", "_", "/", "+"}


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
    # The regex claims the complete uppercase block, so a shorter dictionary
    # entry embedded in it cannot be rendered separately.  Do not suppress a
    # safe fallback solely because of that overlap (for example, ``OS`` in
    # ``OSP`` or ``IP`` in ``IPS``).  Exact dictionary matches were already
    # claimed earlier in the pipeline.
    return True


def _safe_acronym_fallback_boundary(token_raw: str, start: int, end: int) -> bool:
    prev_char = token_raw[start - 1] if start > 0 else None
    next_char = token_raw[end] if end < len(token_raw) else None
    if prev_char is not None and _is_compatibility_jamo(prev_char):
        return False
    if prev_char is not None and prev_char.isascii() and prev_char.isalnum():
        return False
    if prev_char in {"_", "-", "/"}:
        return False
    if next_char is not None and _is_compatibility_jamo(next_char):
        return False
    if next_char is not None and next_char.isascii() and next_char.isalnum():
        return False
    if next_char in {"_", "-", "/"}:
        return False
    return True


def _has_spaced_owned_number_tail(next_char: str, next_non_space: str) -> bool:
    if not next_char.isspace():
        return False
    return (
        next_non_space[:1] in (RANGE_LIKE_DELIMITERS | {"∼"})
        or starts_with_supported_unit(next_non_space)
        or starts_with_supported_compound_exact_unit(next_non_space)
    )


def _has_supported_unit_slash_tail(raw_text: str, start: int) -> bool:
    unit_prefix_length = supported_unit_prefix_length(raw_text[start:])
    if unit_prefix_length is None:
        return False
    unit_suffix = raw_text[start + unit_prefix_length :].lstrip()
    return unit_suffix.startswith("/")


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

    if _starts_compact_mixed_korean_arabic_numeric(raw_text, span.end):
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
    if _has_spaced_owned_number_tail(next_char, next_non_space):
        return False
    if is_unsafe_admin_like_number_tail(raw_text, span.end):
        return False
    
    if _has_supported_unit_slash_tail(raw_text, span.end):
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
            # A right-side ASCII gap makes this a spaced middle-dot boundary.
            # Read the left operand only when a complete safe numeric operand
            # follows.  An attached Korean temporal literal is not a numeric
            # block, so it has no middle-dot owner to claim it; allow the
            # ordinary number fallback to read only the left operand.
            if (
                re.match(r"·[ ]+[0-9]+(?![A-Za-z0-9])", raw_text[span.end:])
                is None
                and _ATTACHED_MIDDLE_DOT_KOREAN_TEMPORAL_LITERAL_RE.match(
                    raw_text[span.end:]
                )
                is None
            ):
                return False

    if "\uac00" <= next_char <= "\ud7a3":
        if "," in raw and raw_text[span.end :].startswith("가"):
            return False
        suffix = raw_text[span.end :]
        if is_emergency_ambiguous_number(raw) or is_public_number(raw):
            return True
        return not suffix.startswith(_NUMBER_BLOCKING_KOREAN_SUFFIXES)

    return True


def _starts_compact_mixed_korean_arabic_numeric(raw_text: str, start: int) -> bool:
    if start >= len(raw_text) or raw_text[start] not in {"천", "백", "십"}:
        return False
    next_index = start + 1
    return next_index < len(raw_text) and raw_text[next_index].isascii() and raw_text[next_index].isdigit()


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
        if prev_char in {"_", "-", "/", ".", "="}:
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


def _is_compatibility_jamo(ch: str) -> bool:
    return "\u3130" <= ch <= "\u318f"


__all__ = ["CLAIM_ORDER_DOC", "claim_surfaces"]
