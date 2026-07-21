from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12· 3", "십이· 삼"),
        ("12 ·3", "십이 ·삼"),
        ("12 · 3", "십이 · 삼"),
        ("12·   3", "십이·   삼"),
        ("12·3", "십이 삼"),
    ],
)
def test_batch4_spaced_and_attached_middle_dot_matrix(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_batch4_asymmetric_spaced_middle_dot_preserves_source_boundary() -> None:
    text = "12· 3"
    output = transform_with_trace(text)

    assert output.normalized_text == "십이· 삼"
    assert [
        (claim.owner, claim.reason, claim.span.start, claim.span.end)
        for claim in output.trace.claim_logs
    ] == [
        ("number", "phase7_minimal_ascii_number", 0, 2),
        ("number", "phase7_minimal_ascii_number", 4, 5),
    ]
    assert any(
        piece.text == "·"
        and piece.provenance == "ORIGINAL_BOUNDARY"
        and piece.source_span is not None
        and (piece.source_span.start, piece.source_span.end) == (2, 3)
        for piece in output.render_pieces
    )
    assert any(
        piece.text == " "
        and piece.provenance == "ORIGINAL_SPACE"
        and piece.source_span is not None
        and (piece.source_span.start, piece.source_span.end) == (3, 4)
        for piece in output.render_pieces
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01·09", "일 영구"),
        ("12·003", "십이 영영삼"),
        ("01·09와 0001", "일 영구와 0001"),
    ],
)
def test_batch4_contiguous_leading_zero_middle_dot_matrix(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert any(
        claim.owner == "middle_dot_numeric"
        and claim.surface_type == "LEXICAL_MIDDLEDOT_SURFACE"
        and claim.reason == "middle_dot_numeric_block_match"
        for claim in output.trace.claim_logs
    )


def test_batch4_suffix_owner_guards_do_not_leak_middle_dot_readings() -> None:
    time_text = "01·09시와 09시"
    time_output = transform_with_trace(time_text)
    assert time_output.normalized_text == time_text
    assert not any(
        claim.owner == "middle_dot_numeric"
        for claim in time_output.trace.claim_logs
    )
    assert [
        (claim.owner, claim.surface_type, claim.reason)
        for claim in time_output.trace.claim_logs
    ] == [
        ("time", "TIME_PRESERVE_SURFACE", "leading_zero_clock_hour_suffix_preserve"),
        ("time", "TIME_PRESERVE_SURFACE", "leading_zero_clock_hour_suffix_preserve"),
    ]

    unit_text = "12·003kg와 03kg"
    unit_output = transform_with_trace(unit_text)
    assert unit_output.normalized_text == unit_text
    assert not any(
        claim.owner == "middle_dot_numeric"
        for claim in unit_output.trace.claim_logs
    )
    assert all(
        claim.owner == "preserve"
        and claim.surface_type == "UNIT_CONTAMINATION_PRESERVE_SURFACE"
        and claim.reason == "unit_percent_suffix_invalid_or_disallowed_spacing_preserve"
        for claim in unit_output.trace.claim_logs
    )


def test_batch4_event_and_decimal_claims_are_independent() -> None:
    text = "12.12 사태와 12.12 수치를 함께 적었다"
    output = transform_with_trace(text)

    assert output.normalized_text == "십이십이 사태와 십이쩜일이 수치를 함께 적었다"
    assert [
        (claim.owner, claim.surface_type, claim.reason, claim.span.start, claim.span.end)
        for claim in output.trace.claim_logs
    ] == [
        ("event", "EVENT_SURFACE", "event_keyword_gate", 0, 5),
        ("decimal", "DECIMAL_SURFACE", "decimal_match", 10, 15),
    ]


def test_batch4_one_digit_right_dotted_event_uses_strong_keyword_gate() -> None:
    text = "12.3 비상계엄"
    output = transform_with_trace(text)
    assert output.normalized_text == "십이삼 비상계엄"
    assert any(
        claim.owner == "event"
        and claim.surface_type == "EVENT_SURFACE"
        and claim.reason == "event_keyword_gate"
        and (claim.span.start, claim.span.end) == (0, 4)
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    "text",
    [
        "https://example.com/12· 3",
        "/tmp/12· 3",
        '{"value":"12· 3"}',
        "[12· 3]",
        "12· 3A",
    ],
)
def test_batch4_protected_or_unsafe_spaced_middle_dot_does_not_partially_rewrite(
    text: str,
) -> None:
    expected = text.strip("[]") if text.startswith("[") else text
    assert transform(text) == expected
