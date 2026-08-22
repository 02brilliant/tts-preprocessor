from __future__ import annotations

from engine.span_engine.administrative import parse_administrative_suffix_candidate
from engine.span_engine.arithmetic import parse_basic_arithmetic_candidate
from engine.span_engine.currency import parse_currency_candidate
from engine.span_engine.counter import counter_render_pieces, parse_counter_candidate
from engine.span_engine.compound_unit import (
    parse_compound_exact_unit_candidate,
    parse_compound_slash_unit_candidate,
)
from engine.span_engine.corporate_marker import parse_corporate_marker_candidate
from engine.span_engine.contextual_number_unit import (
    parse_contextual_number_unit_candidate,
)
from engine.span_engine.code_separator import (
    parse_mixed_alnum_code_separator_candidate,
    parse_spaced_hyphen_numeric_candidate,
)
from engine.span_engine.date_time import (
    parse_clock_hour_direction_surface,
    parse_date_candidate,
    parse_time_candidate,
)
from engine.span_engine.decimal import parse_decimal_candidate
from engine.span_engine.decimal_registered_suffix import (
    parse_decimal_registered_suffix_candidate,
)
from engine.span_engine.duration import parse_duration_candidate
from engine.span_engine.emergency import parse_emergency_candidate
from engine.span_engine.event import parse_event_candidate
from engine.span_engine.fraction import (
    parse_fraction_candidate,
    parse_textual_fraction_candidate,
)
from engine.span_engine.hyphen import hyphen_digit_reading
from engine.span_engine.jamo import parse_jamo_candidate
from engine.span_engine.korean_da_score_pair import parse_korean_da_score_pair_candidate
from engine.span_engine.korean_numeric_chain import parse_korean_numeric_chain_candidate
from engine.span_engine.large_unit import (
    large_unit_render_pieces,
    parse_large_unit_candidate,
)
from engine.span_engine.lexicon import (
    acronym_hangul_hyphen_render_pieces,
    contextual_acronym_reading,
    dictionary_reading,
    phrase_dictionary_reading,
    k_hangul_lexical_reading,
    lexical_compound_reading,
    parse_ampersand_acronym_candidate,
    parse_finance_index_numeric_suffix_candidate,
    spell_uppercase_acronym,
)
from engine.span_engine.managed_numeric_code import (
    parse_managed_acronym_numeric_code_surface,
)
from engine.span_engine.middle_dot import parse_middle_dot_candidate
from engine.span_engine.mixed_integer import parse_mixed_integer_candidate
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.multiplier import (
    multiplier_render_pieces,
    parse_multiplier_candidate,
)
from engine.span_engine.numeric_reading import read_spaced_integer_text
from engine.span_engine.numeric_dae import (
    parse_ambiguous_numeric_dae_preserve_candidate,
)
from engine.span_engine.residual_spacing import needs_residual_hangul_space
from engine.span_engine.numeric_suffix import parse_numeric_suffix_candidate
from engine.span_engine.ordinal import parse_ordinal_candidate
from engine.span_engine.parenthesized_hangul_alias import (
    parse_parenthesized_hangul_alias_candidate,
)
from engine.span_engine.ph import parse_ph_candidate
from engine.span_engine.percent_point import parse_percent_point_candidate
from engine.span_engine.public_number import parse_public_number_candidate
from engine.span_engine.phone import phone_reading
from engine.span_engine.range import parse_range_candidate
from engine.span_engine.signed import parse_signed_candidate
from engine.span_engine.single_letter_code import parse_single_letter_alnum_code_surface
from engine.span_engine.units import (
    parse_caret_literal_unit_candidate,
    parse_korean_numeric_unit_candidate,
    parse_unit_candidate,
)


_SURFACE_TRACE_METADATA_KEYS = (
    "sign_profile",
    "numeric_form",
    "sign_surface",
    "operand_kinds",
    "operator_kinds",
    "has_equality",
)


def _surface_metadata(candidate: SurfaceCandidate) -> dict[str, object]:
    metadata: dict[str, object] = {"reason": candidate.reason}
    for key in _SURFACE_TRACE_METADATA_KEYS:
        if key in candidate.metadata:
            metadata[key] = candidate.metadata[key]
    return metadata


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

    if candidate.owner == "corporate_marker":
        reading = parse_corporate_marker_candidate(raw_text, candidate)
    elif candidate.owner == "parenthesized_hangul_alias":
        return parse_parenthesized_hangul_alias_candidate(raw_text, candidate)
    elif candidate.owner == "phrase_dictionary":
        reading = phrase_dictionary_reading(raw)
    elif candidate.owner == "dictionary":
        reading = dictionary_reading(raw)
    elif candidate.owner == "finance_index":
        reading = parse_finance_index_numeric_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "contextual_acronym":
        reading = contextual_acronym_reading(raw)
    elif candidate.owner == "ampersand_acronym":
        return parse_ampersand_acronym_candidate(raw_text, candidate)
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
        return parse_single_letter_alnum_code_surface(raw_text, candidate)
    elif candidate.owner == "managed_acronym_numeric_code":
        return parse_managed_acronym_numeric_code_surface(raw_text, candidate)
    elif candidate.owner == "two_block_hyphen_code":
        return _make_two_block_hyphen_code_surface(raw_text, candidate, raw)
    elif candidate.owner == "number":
        reading = read_spaced_integer_text(raw)
        if reading is not None and needs_residual_hangul_space(
            raw_text, candidate.core_span.end
        ):
            reading = f"{reading} "
    elif candidate.owner == "decimal":
        reading = parse_decimal_candidate(raw_text, candidate)
    elif candidate.owner == "decimal_registered_suffix":
        reading = parse_decimal_registered_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "currency":
        reading = parse_currency_candidate(raw_text, candidate)
    elif candidate.owner == "date":
        reading = parse_date_candidate(raw_text, candidate)
    elif candidate.owner == "time":
        direction_surface = parse_clock_hour_direction_surface(raw_text, candidate)
        if direction_surface is not None:
            return direction_surface
        reading = parse_time_candidate(raw_text, candidate)
    elif candidate.owner == "duration":
        reading = parse_duration_candidate(raw_text, candidate)
    elif candidate.owner == "multiplier":
        return _make_multiplier_surface(raw_text, candidate, raw)
    elif candidate.owner == "event":
        reading = parse_event_candidate(raw_text, candidate)
    elif candidate.owner == "middle_dot_numeric":
        reading = parse_middle_dot_candidate(raw_text, candidate)
    elif candidate.owner in {"mixed_integer_atomic", "mixed_decimal_atomic"}:
        return parse_mixed_integer_candidate(raw_text, candidate)
    elif candidate.owner == "ph":
        reading = parse_ph_candidate(raw_text, candidate)
    elif candidate.owner == "percent_point":
        reading = parse_percent_point_candidate(raw_text, candidate)
    elif candidate.owner == "fraction":
        reading = parse_fraction_candidate(raw_text, candidate)
    elif candidate.owner == "textual_fraction":
        return parse_textual_fraction_candidate(raw_text, candidate)
    elif candidate.owner == "basic_arithmetic_expression":
        return parse_basic_arithmetic_candidate(raw_text, candidate)
    elif candidate.owner == "emergency":
        reading = parse_emergency_candidate(raw_text, candidate)
    elif candidate.owner == "public_number":
        reading = parse_public_number_candidate(raw_text, candidate)
    elif candidate.owner in {"signed_temperature", "signed_degree", "signed_number"}:
        reading = parse_signed_candidate(raw_text, candidate)
    elif candidate.owner == "phone":
        reading = phone_reading(raw)
    elif candidate.owner == "hyphen_digit_blocks":
        metadata_reading = candidate.metadata.get("reading")
        reading = (
            metadata_reading
            if isinstance(metadata_reading, str)
            else hyphen_digit_reading(raw)
        )
    elif candidate.owner == "spaced_hyphen_numeric_blocks":
        reading = parse_spaced_hyphen_numeric_candidate(raw_text, candidate)
    elif candidate.owner in {"caret_power_unit", "simple_unit", "special_unit"}:
        reading = parse_unit_candidate(raw_text, candidate)
    elif candidate.owner == "korean_numeric_unit":
        return parse_korean_numeric_unit_candidate(raw_text, candidate)
    elif candidate.owner == "caret_literal_unit":
        return parse_caret_literal_unit_candidate(raw_text, candidate)
    elif candidate.owner == "numeric_suffix":
        reading = parse_numeric_suffix_candidate(raw_text, candidate)
    elif candidate.owner == "ordinal":
        return parse_ordinal_candidate(raw_text, candidate)
    elif candidate.owner == "contextual_number_unit":
        return parse_contextual_number_unit_candidate(raw_text, candidate)
    elif candidate.owner == "counter_noun":
        if candidate.metadata.get("full_counter_claim") is True:
            return _make_counter_surface(raw_text, candidate, raw)
        reading = parse_counter_candidate(raw_text, candidate)
    elif candidate.owner == "range" and candidate.reason == "range_compact_large_unit_suffix_gate":
        return _make_compact_large_unit_range_surface(raw_text, candidate, raw)
    elif candidate.reason == "range_compact_large_unit_with_unit_gate":
        return _make_compact_large_unit_range_with_unit_surface(raw_text, candidate, raw)
    elif candidate.reason == "range_paired_large_unit_with_unit_gate":
        return _make_paired_large_unit_range_with_unit_surface(raw_text, candidate, raw)
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
    elif candidate.owner == "korean_numeric_chain":
        return parse_korean_numeric_chain_candidate(raw_text, candidate)
    elif candidate.owner in {
        "korean_da_score_pair",
        "numeric_dae_quantity_sequence",
    }:
        return parse_korean_da_score_pair_candidate(raw_text, candidate)
    elif candidate.owner == "ambiguous_numeric_dae_preserve":
        return parse_ambiguous_numeric_dae_preserve_candidate(raw_text, candidate)

    if reading is None:
        return None
    return Surface(
        surface_type=candidate.surface_type or "SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        metadata=_surface_metadata(candidate),
    )


def _make_compact_large_unit_range_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = candidate.metadata.get("reading")
    suffix = candidate.metadata.get("suffix")
    suffix_span = candidate.metadata.get("suffix_span")
    if not (
        isinstance(reading, str)
        and isinstance(suffix, str)
        and isinstance(suffix_span, SourceSpan)
        and reading.endswith(suffix)
        and candidate.core_span.start < suffix_span.start < suffix_span.end == candidate.core_span.end
    ):
        return None
    prefix_span = SourceSpan(candidate.core_span.start, suffix_span.start)
    pieces = [
        RenderPiece(
            text=reading[: -len(suffix)],
            provenance="GENERATED_READING",
            source_span=prefix_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=suffix,
            provenance="ORIGINAL_KOREAN",
            source_span=suffix_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]
    return Surface(
        surface_type=candidate.surface_type or "RANGE_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata=_surface_metadata(candidate),
    )


def _make_compact_large_unit_range_with_unit_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = candidate.metadata.get("reading")
    prefix_reading = candidate.metadata.get("prefix_reading")
    suffix = candidate.metadata.get("suffix")
    suffix_span = candidate.metadata.get("suffix_span")
    unit_reading = candidate.metadata.get("unit_reading")
    unit_start = candidate.metadata.get("unit_start")
    if not (
        isinstance(reading, str)
        and isinstance(prefix_reading, str)
        and isinstance(suffix, str)
        and isinstance(suffix_span, SourceSpan)
        and isinstance(unit_reading, str)
        and isinstance(unit_start, int)
        and candidate.core_span.start < suffix_span.start < suffix_span.end <= unit_start < candidate.core_span.end
    ):
        return None
    pieces = [
        RenderPiece(
            text=prefix_reading,
            provenance="GENERATED_READING",
            source_span=SourceSpan(candidate.core_span.start, suffix_span.start),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=suffix,
            provenance="ORIGINAL_KOREAN",
            source_span=suffix_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=" " + unit_reading,
            provenance="GENERATED_READING",
            source_span=SourceSpan(unit_start, candidate.core_span.end),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]
    return Surface(
        surface_type=candidate.surface_type or "RANGE_WITH_UNIT_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata=_surface_metadata(candidate),
    )


def _make_paired_large_unit_range_with_unit_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = candidate.metadata.get("reading")
    left_numeric_reading = candidate.metadata.get("left_numeric_reading")
    right_numeric_reading = candidate.metadata.get("right_numeric_reading")
    left_numeric_span = candidate.metadata.get("left_numeric_span")
    right_numeric_span = candidate.metadata.get("right_numeric_span")
    left_suffix_span = candidate.metadata.get("left_suffix_span")
    right_suffix_span = candidate.metadata.get("right_suffix_span")
    left_has_decimal = candidate.metadata.get("left_has_decimal") is True
    right_has_decimal = candidate.metadata.get("right_has_decimal") is True
    separator_span = candidate.metadata.get("separator_span")
    unit_reading = candidate.metadata.get("unit_reading")
    unit_start = candidate.metadata.get("unit_start")
    if not (
        isinstance(reading, str)
        and isinstance(left_numeric_reading, str)
        and isinstance(right_numeric_reading, str)
        and isinstance(left_numeric_span, SourceSpan)
        and isinstance(right_numeric_span, SourceSpan)
        and isinstance(left_suffix_span, SourceSpan)
        and isinstance(right_suffix_span, SourceSpan)
        and isinstance(separator_span, SourceSpan)
        and isinstance(unit_reading, str)
        and isinstance(unit_start, int)
        and unit_start < candidate.core_span.end
    ):
        return None
    pieces = [
        RenderPiece(
            text=left_numeric_reading,
            provenance="GENERATED_READING",
            source_span=left_numeric_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]
    if left_has_decimal:
        pieces.append(
            RenderPiece(
                text=" ",
                provenance="GENERATED_READING",
                source_span=left_suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    pieces.extend(
        [
        RenderPiece(
            text=raw_text[left_suffix_span.start : left_suffix_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=left_suffix_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text="에서 ",
            provenance="GENERATED_READING",
            source_span=separator_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=right_numeric_reading,
            provenance="GENERATED_READING",
            source_span=right_numeric_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        ]
    )
    if right_has_decimal:
        pieces.append(
            RenderPiece(
                text=" ",
                provenance="GENERATED_READING",
                source_span=right_suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    pieces.extend(
        [
        RenderPiece(
            text=raw_text[right_suffix_span.start : right_suffix_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=right_suffix_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=" " + unit_reading,
            provenance="GENERATED_READING",
            source_span=SourceSpan(unit_start, candidate.core_span.end),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        ]
    )
    return Surface(
        surface_type=candidate.surface_type or "RANGE_WITH_UNIT_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata=_surface_metadata(candidate),
    )


def _make_two_block_hyphen_code_surface(
    raw_text: str,
    candidate: SurfaceCandidate,
    raw: str,
) -> Surface | None:
    left = candidate.metadata.get("left")
    left_reading = candidate.metadata.get("left_reading")
    number = candidate.metadata.get("number")
    number_reading = candidate.metadata.get("number_reading")
    if not all(
        isinstance(value, str) for value in (left, left_reading, number, number_reading)
    ):
        return None
    assert isinstance(left, str)
    assert isinstance(left_reading, str)
    assert isinstance(number, str)
    assert isinstance(number_reading, str)
    hyphen_start = candidate.core_span.start + len(left)
    number_start = hyphen_start + 1
    render_pieces = [
        RenderPiece(
            text=left_reading,
            provenance=(
                "ORIGINAL_KOREAN"
                if all("\uac00" <= char <= "\ud7a3" for char in left)
                else "GENERATED_READING"
            ),
            source_span=SourceSpan(candidate.core_span.start, hyphen_start),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text="-",
            provenance="ORIGINAL_BOUNDARY",
            source_span=SourceSpan(hyphen_start, number_start),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=number_reading,
            provenance="GENERATED_READING",
            source_span=SourceSpan(number_start, candidate.core_span.end),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]
    return _make_core_render_surface(
        candidate,
        raw,
        f"{left_reading}-{number_reading}",
        render_pieces,
        default_surface_type="CODE_SEPARATOR_BLOCK_SURFACE",
    )


def _make_core_render_surface(
    candidate: SurfaceCandidate,
    raw: str,
    reading: str,
    render_pieces: list[RenderPiece],
    *,
    default_surface_type: str,
) -> Surface:
    return Surface(
        surface_type=candidate.surface_type or default_surface_type,
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=render_pieces,
        metadata=_surface_metadata(candidate),
    )


def _make_k_hangul_lexical_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = k_hangul_lexical_reading(raw)
    if reading is None:
        return None
    hangul_start = candidate.core_span.start + 2
    render_pieces = [
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
    ]
    return _make_core_render_surface(
        candidate,
        raw,
        reading,
        render_pieces,
        default_surface_type="K_HANGUL_LEXICAL_SURFACE",
    )


def _make_acronym_hangul_hyphen_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    pieces = acronym_hangul_hyphen_render_pieces(raw_text, candidate)
    if pieces is None:
        return None
    reading = "".join(piece.text for piece in pieces)
    return _make_core_render_surface(
        candidate,
        raw,
        reading,
        pieces,
        default_surface_type="ACRONYM_HANGUL_HYPHEN_LEXICAL_SURFACE",
    )


def _make_large_unit_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = parse_large_unit_candidate(raw_text, candidate)
    if reading is None:
        return None
    render_pieces = large_unit_render_pieces(raw_text, candidate)
    return _make_core_render_surface(
        candidate,
        raw,
        reading,
        render_pieces,
        default_surface_type="LARGE_UNIT_ATOMIC_SURFACE",
    )


def _make_counter_surface(
    raw_text: str, candidate: SurfaceCandidate, raw: str
) -> Surface | None:
    reading = parse_counter_candidate(raw_text, candidate)
    render_pieces = counter_render_pieces(raw_text, candidate)
    if reading is None or render_pieces is None:
        return None
    return _make_core_render_surface(
        candidate,
        raw,
        reading,
        render_pieces,
        default_surface_type="COUNTER_SURFACE",
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
        metadata=_surface_metadata(candidate),
    )


__all__ = ["parse_candidates"]
