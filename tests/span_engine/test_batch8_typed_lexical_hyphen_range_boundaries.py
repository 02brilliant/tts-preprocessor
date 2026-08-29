from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [("12-15장", "십이에서 십오-장"), ("12-15 장", "십이에서 십오-장")],
)
def test_batch8_registered_jang_suffix_licenses_restricted_hyphen_range(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert [
        (claim.owner, claim.surface_type, claim.reason)
        for claim in output.trace.claim_logs
    ] == [
        (
            "range",
            "RANGE_SURFACE",
            "numeric_delimited_hyphen_range_korean_suffix_gate",
        )
    ]


@pytest.mark.parametrize(
    "text", ["12-15장abc", "-12-15장", "01-15장", "12-015장"]
)
def test_batch8_unlicensed_or_unsafe_hyphen_ranges_preserve_atomically(
    text: str,
) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI·디지털", "에이아이·디지털"),
        ("AI·반도체", "에이아이·반도체"),
        ("ISO·IEC", "아이에스오·아이이씨"),
        ("AI·디지털abc", "에이아이·디지털abc"),
    ],
)
def test_batch8_lexical_middle_dot_is_original_delimiter(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    if text == "ISO·IEC":
        assert [
            (claim.owner, claim.surface_type, claim.reason)
            for claim in output.trace.claim_logs
        ] == [
            (
                "lexical_compound",
                "LEXICAL_COMPOUND_SURFACE",
                "fixed_lexical_compound_match",
            )
        ]
        assert output.render_pieces[0].text == expected
        assert output.render_pieces[0].provenance == "GENERATED_READING"
        assert "·" in output.render_pieces[0].text
        return

    dot_piece = next(piece for piece in output.render_pieces if piece.text == "·")
    assert dot_piece.owner is None
    assert dot_piece.provenance == "ORIGINAL_BOUNDARY"
    assert dot_piece.source_span is not None


def test_batch8_k_hangul_and_dictionary_claims_are_independent() -> None:
    text = "K-푸드·K-뷰티·K-POP"
    output = transform_with_trace(text)
    assert output.normalized_text == "케이푸드·케이뷰티·케이팝"
    assert [claim.owner for claim in output.trace.claim_logs] == [
        "dictionary",
        "k_hangul_lexical",
        "k_hangul_lexical",
    ]
    assert [
        piece.text
        for piece in output.render_pieces
        if piece.provenance == "ORIGINAL_BOUNDARY"
    ] == ["·", "·"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("K-푸드", "케이푸드"), ("K-뷰티", "케이뷰티"), ("K-POP", "케이팝")],
)
def test_batch8_single_lexical_token_matches_sequence_behavior(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_batch8_unsafe_k_hangul_tail_preserves_full_token() -> None:
    assert transform("K-푸드-v2") == "K-푸드-v2"


@pytest.mark.parametrize("delimiter", ["~", "～", "∼", "〜"])
def test_batch8_all_registered_tilde_aliases_share_month_suffix(
    delimiter: str,
) -> None:
    text = f"1{delimiter}11월"
    output = transform_with_trace(text)
    assert output.normalized_text == "일월에서 십일월"
    assert any(
        claim.owner == "range"
        and claim.surface_type == "RANGE_SURFACE"
        and claim.reason == "range_shared_korean_suffix_gate"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    "text",
    [
        "1∼11월abc",
        "https://example.com/1∼11월",
        "`1∼11월`",
    ],
)
def test_batch8_unsafe_and_protected_month_ranges_do_not_partially_convert(
    text: str,
) -> None:
    assert transform(text) == text


def test_batch8_square_bracket_month_range_is_absolute_preserve_inside() -> None:
    assert transform("[1∼11월]") == "1∼11월"


def test_batch8_acronym_large_unit_and_range_claims_stay_independent() -> None:
    text = "FTA 요건과 AI·디지털 전략은 6402억 규모로 1∼11월 유지된다"
    output = transform_with_trace(text)
    assert output.normalized_text == (
        "에프티에이 요건과 에이아이·디지털 전략은 육천사백이억 규모로 "
        "일월에서 십일월 유지된다"
    )
    assert [claim.owner for claim in output.trace.claim_logs] == [
        "dictionary",
        "acronym_fallback",
        "large_unit_atomic",
        "range",
    ]
