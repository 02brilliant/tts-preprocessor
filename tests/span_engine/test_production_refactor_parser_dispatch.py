from __future__ import annotations

import pytest

import engine.span_engine.parser as parser_module
from engine.span_engine import SourceSpan, SurfaceCandidate, transform_with_trace
from engine.span_engine.parser import parse_candidates


def _claim_snapshot(output) -> list[tuple[str, str, str | None, str | None, int, int]]:
    return [
        (
            claim.owner,
            claim.claim_type,
            claim.surface_type,
            claim.reason,
            claim.span.start,
            claim.span.end,
        )
        for claim in output.trace.claim_logs
    ]


def _parser_snapshot(output) -> list[tuple[str, str | None, str, str | None, int, int]]:
    return [
        (
            log.owner,
            log.surface_type,
            log.decision,
            log.metadata.get("reading"),
            log.span.start,
            log.span.end,
        )
        for log in output.trace.parser_logs
    ]


def _piece_snapshot(output) -> list[tuple[str, str, str | None, int, int]]:
    return [
        (
            piece.text,
            piece.provenance,
            piece.owner,
            piece.source_span.start,
            piece.source_span.end,
        )
        for piece in output.render_pieces
        if piece.source_span is not None
    ]


def test_k_hangul_core_surface_provenance_contract() -> None:
    output = transform_with_trace("K-푸드")

    assert output.normalized_text == "케이푸드"
    assert _claim_snapshot(output) == [
        (
            "k_hangul_lexical",
            "surface",
            "K_HANGUL_LEXICAL_SURFACE",
            "k_hangul_lexical_prefix_full_consume",
            0,
            4,
        )
    ]
    assert _parser_snapshot(output) == [
        (
            "k_hangul_lexical",
            "K_HANGUL_LEXICAL_SURFACE",
            "success",
            "케이푸드",
            0,
            4,
        )
    ]
    assert _piece_snapshot(output) == [
        ("케이", "GENERATED_READING", "k_hangul_lexical", 0, 2),
        ("푸드", "ORIGINAL_KOREAN", "k_hangul_lexical", 2, 4),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_acronym_hangul_core_surface_provenance_contract() -> None:
    output = transform_with_trace("KTX-이음")

    assert output.normalized_text == "케이티엑스-이음"
    assert _claim_snapshot(output) == [
        (
            "acronym_hangul_hyphen",
            "surface",
            "ACRONYM_HANGUL_HYPHEN_LEXICAL_SURFACE",
            "managed_acronym_hangul_hyphen_lexical_compound",
            0,
            6,
        )
    ]
    assert _parser_snapshot(output) == [
        (
            "acronym_hangul_hyphen",
            "ACRONYM_HANGUL_HYPHEN_LEXICAL_SURFACE",
            "success",
            "케이티엑스-이음",
            0,
            6,
        )
    ]
    assert _piece_snapshot(output) == [
        ("케이티엑스", "GENERATED_READING", "acronym_hangul_hyphen", 0, 3),
        ("-", "ORIGINAL_BOUNDARY", "acronym_hangul_hyphen", 3, 4),
        ("이음", "ORIGINAL_KOREAN", "acronym_hangul_hyphen", 4, 6),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_large_unit_core_surface_provenance_contract() -> None:
    output = transform_with_trace("6402억 달러")

    assert output.normalized_text == "육천사백이억 달러"
    assert _claim_snapshot(output) == [
        (
            "large_unit_atomic",
            "surface",
            "LARGE_UNIT_ATOMIC_SURFACE",
            "large_unit_numeric_surface",
            0,
            5,
        )
    ]
    assert _parser_snapshot(output) == [
        (
            "large_unit_atomic",
            "LARGE_UNIT_ATOMIC_SURFACE",
            "success",
            "육천사백이억",
            0,
            5,
        )
    ]
    assert _piece_snapshot(output) == [
        ("육천사백이", "GENERATED_READING", "large_unit_atomic", 0, 4),
        ("억", "ORIGINAL_KOREAN", "large_unit_atomic", 4, 5),
        (" ", "ORIGINAL_SPACE", None, 5, 6),
        ("달러", "ORIGINAL_KOREAN", None, 6, 8),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_multiplier_remains_full_span_policy_distinct_control() -> None:
    output = transform_with_trace("3배")

    assert output.normalized_text == "세 배"
    assert _claim_snapshot(output) == [
        (
            "multiplier",
            "surface",
            "MULTIPLIER_SURFACE",
            "multiplier_bae_owner",
            0,
            1,
        )
    ]
    assert _parser_snapshot(output) == [
        ("multiplier", "MULTIPLIER_SURFACE", "success", "세 배", 0, 2)
    ]
    assert _piece_snapshot(output) == [
        ("세 ", "GENERATED_READING", "multiplier", 0, 1),
        ("배", "ORIGINAL_KOREAN", "multiplier", 1, 2),
    ]


def test_common_generated_surface_and_preserve_no_surface_contract() -> None:
    generated = transform_with_trace("3 kg")
    preserved = transform_with_trace("pH7.4test")

    assert generated.normalized_text == "삼 킬로그램"
    assert _parser_snapshot(generated) == [
        ("simple_unit", "SIMPLE_UNIT_SURFACE", "success", "삼 킬로그램", 0, 4)
    ]
    assert _piece_snapshot(generated) == [
        ("삼 킬로그램", "GENERATED_READING", "simple_unit", 0, 4)
    ]

    assert preserved.normalized_text == "pH7.4test"
    assert _claim_snapshot(preserved) == [
        (
            "preserve",
            "preserve",
            "PH_PRESERVE_SURFACE",
            "ph_unsafe_tail_preserve",
            0,
            9,
        )
    ]
    assert _parser_snapshot(preserved) == []
    assert _piece_snapshot(preserved) == [
        ("pH7.4test", "ORIGINAL_BOUNDARY", None, 0, 9)
    ]


def test_unknown_or_invalid_candidate_is_omitted_without_parser_masking() -> None:
    candidates = [
        SurfaceCandidate(
            core_span=SourceSpan(0, 1),
            full_span=SourceSpan(0, 1),
            owner="unknown_owner",
        ),
        SurfaceCandidate(
            core_span=SourceSpan(0, 1),
            full_span=SourceSpan(0, 1),
            owner="acronym_hangul_hyphen",
        ),
    ]

    assert parse_candidates("X", candidates) == []


def test_owner_parser_exception_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = SurfaceCandidate(
        core_span=SourceSpan(0, 3),
        full_span=SourceSpan(0, 3),
        owner="dictionary",
        surface_type="DICTIONARY_SURFACE",
        reason="test_exception_contract",
    )

    def raise_parser_error(raw: str) -> str:
        raise RuntimeError(f"parser failed for {raw}")

    monkeypatch.setattr(parser_module, "dictionary_reading", raise_parser_error)

    with pytest.raises(RuntimeError, match="parser failed for GPT"):
        parse_candidates("GPT", [candidate])
