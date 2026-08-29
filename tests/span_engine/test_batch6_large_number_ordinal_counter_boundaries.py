from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


def test_batch6_supported_large_number_width_ends_at_gyeong() -> None:
    assert transform("99999999999999999999") == (
        "구천구백구십구경 구천구백구십구조 구천구백구십구억 "
        "구천구백구십구만 구천구백구십구"
    )


def test_batch6_hae_width_no_hangul_input_preserves_exactly() -> None:
    text = "100000000000000000000"
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert output.trace.claim_logs == []
    assert any(
        log.reason == "global_no_hangul_bypass"
        and log.action == "preserve_original"
        for log in output.trace.fallback_logs
    )


def test_batch6_unsupported_large_number_fallback_is_segment_local_with_hangul() -> None:
    text = "값은 100000000000000000000이고 3kg이다"
    output = transform_with_trace(text)

    assert output.normalized_text == "값은 100000000000000000000이고 삼-킬로그램이다"
    assert any(
        piece.owner == "simple_unit" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        log.reason == "hangul_input_whole_fallback_prohibited"
        and log.action == "segment_fallback"
        and log.metadata["segment_failures"] == [
            {
                "start": 3,
                "end": 26,
                "error_type": "ValueError",
                "error_message": "value is too large",
            }
        ]
        for log in output.trace.fallback_logs
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제5차", "제-오차"),
        ("제62회", "제-육십이회"),
        ("제 15권", "제-십오권"),
    ],
)
def test_batch6_prefixed_ordinal_spacing_is_owner_generated(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert [
        (claim.owner, claim.surface_type, claim.reason)
        for claim in output.trace.claim_logs
    ] == [
        (
            "numeric_suffix",
            "NUMERIC_SUFFIX_SURFACE",
            "prefixed_ordinal_numeric_suffix",
        )
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제2.5차", "제-이쩜오차"),
        ("제2-차", "제2-차"),
        ("A제5차", "A제5차"),
        ("제5차abc", "제-오차abc"),
    ],
)
def test_batch6_prefixed_ordinal_split_or_preserve_forms(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("60여 명", "육십여 명"),
        ("1만3천여 명", "일만삼천여 명"),
        ("1만3천 여 명", "일만삼천 여 명"),
    ],
)
def test_batch6_approximate_marker_preserves_source_attachment(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_batch6_large_approximate_claim_is_atomic() -> None:
    output = transform_with_trace("내년 1만3천여 명을 모집한다")
    assert output.normalized_text == "내년 일만삼천여 명을 모집한다"
    assert any(
        claim.owner == "large_unit_atomic"
        and claim.reason == "large_unit_structured_integer_surface"
        for claim in output.trace.claim_logs
    )


def test_batch6_emergency_and_counter_claims_are_independent() -> None:
    output = transform_with_trace("긴급번호 112는 112명과 다르다")
    assert output.normalized_text == "긴급번호 일일이는 백십이-명과 다르다"
    assert [claim.owner for claim in output.trace.claim_logs] == [
        "emergency",
        "counter_noun",
    ]
    assert output.trace.claim_logs[0].reason == "emergency_context_tail_gate"
    assert output.trace.claim_logs[1].reason == "counter_policy_gate"


def test_batch6_comma_decimal_is_one_compact_decimal_claim() -> None:
    text = "1,234,567,890,123.456"
    output = transform_with_trace(text)
    assert output.normalized_text == (
        "일조이천삼백사십오억육천칠백팔십구만백이십삼쩜사오육"
    )
    assert [
        (claim.owner, claim.surface_type, claim.reason, claim.span.start, claim.span.end)
        for claim in output.trace.claim_logs
    ] == [("decimal", "DECIMAL_SURFACE", "decimal_match", 0, len(text))]
