from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7m^2", "칠-제곱미터"),
        ("7m^3", "칠-세제곱미터"),
        ("7 m^3", "칠-세제곱미터"),
        ('2.5cm^2', '이-쩜-오-제곱센티미터'),
        ("3kg^3", "삼kg^3"),
        ("7m^3 한글", "칠-세제곱미터 한글"),
        ("7m^3한글", "칠-세제곱미터한글"),
    ],
)
def test_registered_english_unit_caret_power_positive_matrix(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("m^3", "m^3"),
        ("7m ^3", "칠-미터 ^3"),
        ("7m^3a", "칠m^3a"),
        ("7m^31", "칠m^31"),
        ("7m^3.", "칠-세제곱미터."),
        ("7V^3", "칠V^3"),
    ],
)
def test_registered_english_unit_caret_power_keeps_existing_invalid_paths(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_caret_power_unit_full_claims_before_simple_unit() -> None:
    output = transform_with_trace("부피는 7m^3이다")

    assert output.normalized_text == "부피는 칠-세제곱미터이다"
    claim = next(
        claim
        for claim in output.trace.claim_logs
        if claim.owner == "caret_power_unit"
    )
    assert (claim.span.start, claim.span.end) == (4, 8)
    assert any(
        piece.owner == "caret_power_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
