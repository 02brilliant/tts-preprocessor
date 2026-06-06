from __future__ import annotations

from engine.span_engine.administrative import parse_administrative_suffix_candidate
from engine.span_engine.currency import parse_currency_candidate
from engine.span_engine.counter import parse_counter_candidate
from engine.span_engine.compound_unit import (
    parse_compound_exact_unit_candidate,
    parse_compound_slash_unit_candidate,
)
from engine.span_engine.code_separator import (
    parse_mixed_alnum_code_separator_candidate,
    parse_spaced_hyphen_numeric_candidate,
    parse_single_letter_alnum_code_candidate,
    parse_two_block_hyphen_code_candidate,
)
from engine.span_engine.date_time import parse_date_candidate, parse_time_candidate
from engine.span_engine.decimal import parse_decimal_candidate
from engine.span_engine.decimal_registered_suffix import (
    parse_decimal_registered_suffix_candidate,
)
from engine.span_engine.duration import parse_duration_candidate
from engine.span_engine.emergency import parse_emergency_candidate
from engine.span_engine.event import parse_event_candidate
from engine.span_engine.fraction import parse_fraction_candidate
from engine.span_engine.hyphen import hyphen_digit_reading
from engine.span_engine.jamo import parse_jamo_candidate
from engine.span_engine.korean_da_score_pair import parse_korean_da_score_pair_candidate
from engine.span_engine.large_unit import (
    large_unit_render_pieces,
    parse_large_unit_candidate,
)
from engine.span_engine.lexicon import (
    acronym_hangul_hyphen_render_pieces,
    dictionary_reading,
    k_hangul_lexical_reading,
    lexical_compound_reading,
    parse_finance_index_numeric_suffix_candidate,
    spell_uppercase_acronym,
)
from engine.span_engine.managed_numeric_code import (
    parse_managed_acronym_numeric_code_candidate,
)
from engine.span_engine.middle_dot import parse_middle_dot_candidate
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.multiplier import (
    multiplier_render_pieces,
    parse_multiplier_candidate,
)
from engine.span_engine.numeric_reading import read_spaced_integer_text
from engine.span_engine.numeric_suffix import parse_numeric_suffix_candidate
from engine.span_engine.ph import parse_ph_candidate
from engine.span_engine.percent_point import parse_percent_point_candidate
from engine.span_engine.public_number import parse_public_number_candidate
from engine.span_engine.phone import phone_reading
from engine.span_engine.range import parse_range_candidate
from engine.span_engine.signed import parse_signed_candidate
from engine.span_engine.units import parse_unit_candidate


def parse_candidates(raw_text: str, candidates: list[SurfaceCandidate]) -> list[Surface]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(candidates, list):
        raise TypeError("candidates must be list[SurfaceCandidate]")

    surfaces: list[Surface] = []
    for candidate in candidates:
        if not isinstance(candidate, SurfaceCandidate):
            raise TypeError("candidates must contain SurfaceCandidate")
        surface = _parse_candidate(raw_text, candidate)
        if surface is not None:
            surfaces.append(surface)
    return surfaces


def _parse_candidate(raw_text: str, candidate: SurfaceCandidate) -> Surface | None:
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    reading: str | None = None

    if candidate.owner == "dictionary":
        reading = dictionary_reading(raw)
    elif candidate.owner == "finance_index":
        reading = parse_finance_index_numeric_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "k_hangul_lexical":
        return _make_k_hangul_lexical_surface(raw_text, candidate, raw)
    elif candidate.owner == "lexical_compound":
        reading = lexical_compound_reading(raw)
    elif candidate.owner == "acronym_hangul_hyphen":
        return _make_acronym_hangul_hyphen_surface(raw_text, candidate, raw)
    elif candidate.owner == "acronym_fallback":
        reading = spell_uppercase_acronym(raw)
    elif candidate.owner == "mixed_alnum_code_separator":
        reading = parse_mixed_alnum_code_separator_candidate(raw_text, candidate)
    elif candidate.owner == "single_letter_alnum_code":
        reading = parse_single_letter_alnum_code_candidate(raw_text, candidate)
    elif candidate.owner == "managed_acronym_numeric_code":
        reading = parse_managed_acronym_numeric_code_candidate(raw_text, candidate)
    elif candidate.owner == "two_block_hyphen_code":
        reading = parse_two_block_hyphen_code_candidate(raw_text, candidate)
    elif candidate.owner == "number":
        reading = read_spaced_integer_text(raw)
    elif candidate.owner == "decimal":
        reading = parse_decimal_candidate(raw_text, candidate)
    elif candidate.owner == "decimal_registered_suffix":
        reading = parse_decimal_registered_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "currency":
        reading = parse_currency_candidate(raw_text, candidate)
    elif candidate.owner == "date":
        reading = parse_date_candidate(raw_text, candidate)
    elif candidate.owner == "time":
        reading = parse_time_candidate(raw_text, candidate)
    elif candidate.owner == "duration":
        reading = parse_duration_candidate(raw_text, candidate)
    elif candidate.owner == "multiplier":
        return _make_multiplier_surface(raw_text, candidate, raw)
    elif candidate.owner == "event":
        reading = parse_event_candidate(raw_text, candidate)
    elif candidate.owner == "middle_dot_numeric":
        reading = parse_middle_dot_candidate(raw_text, candidate)
    elif candidate.owner == "ph":
        reading = parse_ph_candidate(raw_text, candidate)
    elif candidate.owner == "percent_point":
        reading = parse_percent_point_candidate(raw_text, candidate)
    elif candidate.owner == "fraction":
        reading = parse_fraction_candidate(raw_text, candidate)
    elif candidate.owner == "emergency":
        reading = parse_emergency_candidate(raw_text, candidate)
    elif candidate.owner == "public_number":
        reading = parse_public_number_candidate(raw_text, candidate)
    elif candidate.owner in {"signed_temperature", "signed_degree", "signed_number"}:
        reading = parse_signed_candidate(raw_text, candidate)
    elif candidate.owner == "phone":
        reading = phone_reading(raw)
    elif candidate.owner == "hyphen_digit_blocks":
        reading = hyphen_digit_reading(raw)
    elif candidate.owner == "spaced_hyphen_numeric_blocks":
        reading = parse_spaced_hyphen_numeric_candidate(raw_text, candidate)
    elif candidate.owner in {"simple_unit", "special_unit"}:
        reading = parse_unit_candidate(raw_text, candidate)
    elif candidate.owner == "numeric_suffix":
        reading = parse_numeric_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "counter_noun":
        reading = parse_counter_candidate(raw_text, candidate)
    elif candidate.owner in {
        "range",
        "range_with_unit",
        "colon_semantic_pair",
        "multi_colon_numeric",
    }:
        reading = parse_range_candidate(raw_text, candidate)
    elif candidate.owner == "compound_slash_unit":
        reading = parse_compound_slash_unit_candidate(raw_text, candidate)
    elif candidate.owner == "compound_exact_unit":
        reading = parse_compound_exact_unit_candidate(raw_text, candidate)
    elif candidate.owner == "jamo":
        reading = parse_jamo_candidate(raw_text, candidate)
    elif candidate.owner == "large_unit_atomic":
        return _make_large_unit_surface(raw_text, candidate, raw)
    elif candidate.owner == "administrative_suffix":
        reading = parse_administrative_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "korean_da_score_pair":
        return parse_korean_da_score_pair_candidate(raw_text, candidate)

    if reading is None:
        return None
    return Surface(
        surface_type=candidate.surface_type or "SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        metadata={"reason": candidate.reason},
    )


def _make_k_hangul_lexical_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = k_hangul_lexical_reading(raw)
    if reading is None:
        return None
    hangul_start = candidate.core_span.start + 2
    return Surface(
        surface_type=candidate.surface_type or "K_HANGUL_LEXICAL_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=[
            RenderPiece(
                text="케이",
                provenance="GENERATED_READING",
                source_span=SourceSpan(candidate.core_span.start, hangul_start),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
            RenderPiece(
                text=raw_text[hangul_start : candidate.core_span.end],
                provenance="ORIGINAL_KOREAN",
                source_span=SourceSpan(hangul_start, candidate.core_span.end),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
        ],
        metadata={"reason": candidate.reason},
    )


def _make_acronym_hangul_hyphen_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    pieces = acronym_hangul_hyphen_render_pieces(raw_text, candidate)
    if pieces is None:
        return None
    reading = "".join(piece.text for piece in pieces)
    return Surface(
        surface_type=candidate.surface_type or "ACRONYM_HANGUL_HYPHEN_LEXICAL_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def _make_large_unit_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = parse_large_unit_candidate(raw_text, candidate)
    if reading is None:
        return None
    render_pieces = large_unit_render_pieces(raw_text, candidate)
    return Surface(
        surface_type=candidate.surface_type or "LARGE_UNIT_ATOMIC_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=render_pieces,
        metadata={"reason": candidate.reason},
    )


def _make_multiplier_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = parse_multiplier_candidate(raw_text, candidate)
    if reading is None:
        return None
    render_pieces = multiplier_render_pieces(raw_text, candidate)
    if render_pieces is None:
        return None
    return Surface(
        surface_type=candidate.surface_type or "MULTIPLIER_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.full_span.start : candidate.full_span.end],
        span=candidate.full_span,
        reading=reading,
        render_pieces=render_pieces,
        metadata={"reason": candidate.reason},
    )


__all__ = ["parse_candidates"]
