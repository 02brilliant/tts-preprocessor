from __future__ import annotations

import pytest

from engine.span_engine.models import SourceSpan
from engine.span_engine.range import (
    parse_numeric_delimited_number,
    render_numeric_delimited_number,
)
from engine.span_engine.transform import transform, transform_with_trace


@pytest.mark.parametrize(
    ("raw", "expected_sign", "expected"),
    [
        ("2", None, "이"),
        ("+2", "+", "플러스 이"),
        ("-2", "-", "마이너스 이"),
        ("+0.05", "+", "플러스 영쩜영오"),
        ("-1,000.50", "-", "마이너스 천쩜오영"),
    ],
)
def test_p2_numeric_sign_rendering_characterization(
    raw: str,
    expected_sign: str | None,
    expected: str,
) -> None:
    parsed = parse_numeric_delimited_number(raw)
    assert parsed is not None
    assert parsed.sign_surface == expected_sign
    assert render_numeric_delimited_number(parsed) == expected


@pytest.mark.parametrize(
    ("text", "expected", "owner", "surface_type", "reason", "span"),
    [
        (
            "-2.3~+4.5kg이다",
            "마이너스 이쩜삼에서 플러스 사쩜오-킬로그램이다",
            "range_with_unit",
            "RANGE_WITH_UNIT_SURFACE",
            "numeric_delimited_hyphen_range_with_unit_gate",
            SourceSpan(0, 11),
        ),
        (
            "-1:2 비율",
            "마이너스 일 대 이 비율",
            "colon_semantic_pair",
            "COLON_SEMANTIC_PAIR_SURFACE",
            "colon_semantic_pair_explicit_context_gate",
            SourceSpan(0, 4),
        ),
    ],
)
def test_p2_signed_owner_trace_and_span_characterization(
    text: str,
    expected: str,
    owner: str,
    surface_type: str,
    reason: str,
    span: SourceSpan,
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert [
        (claim.owner, claim.surface_type, claim.reason, claim.span)
        for claim in output.trace.claim_logs
    ] == [(owner, surface_type, reason, span)]
    generated = [piece for piece in output.render_pieces if piece.owner == owner]
    assert len(generated) == 1
    assert generated[0].source_span == span
    assert generated[0].provenance == "GENERATED_READING"


@pytest.mark.parametrize(
    ("text", "expected", "owner", "generated"),
    [
        ("1~2이다", "일에서 이이다", "range", "일에서 이"),
        ("1~2테스트", "일에서 이 테스트", "range", "일에서 이 "),
        ("1~2처럼", "일에서 이 처럼", "range", "일에서 이 "),
        ("1~2다", "일에서 이 다", "range", "일에서 이 "),
        ("1:2이다", "일 대 이이다", "colon_semantic_pair", "일 대 이"),
        ("1:2테스트", "일 대 이 테스트", "colon_semantic_pair", "일 대 이 "),
        ("1:2처럼", "일 대 이처럼", "colon_semantic_pair", "일 대 이"),
        ("1:2다", "일 대 이다", "colon_semantic_pair", "일 대 이"),
    ],
)
def test_p2_owner_specific_attached_hangul_tail_characterization(
    text: str,
    expected: str,
    owner: str,
    generated: str,
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert output.render_pieces[0].text == generated
    assert output.render_pieces[0].owner == owner
    assert output.render_pieces[0].source_span == SourceSpan(0, 3)
    assert output.render_pieces[0].provenance == "GENERATED_READING"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~2 은", "일에서 이 은"),
        ("1~2.", "일에서 이."),
        ("1:2 은", "일 대 이 은"),
        ("1:2.", "일 대 이."),
        ("1~2abc", "1~2abc"),
        ("1:2abc", "1:2abc"),
    ],
)
def test_p2_tail_spacing_non_hangul_and_unsafe_ascii_boundaries(
    text: str,
    expected: str,
) -> None:
    assert transform(text) == expected
