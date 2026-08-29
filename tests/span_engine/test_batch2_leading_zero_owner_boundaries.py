from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01", "01"),
        ("003", "003"),
        ("007", "007"),
        ("0001", "0001"),
        ("01명", "01명"),
        ("01명에게", "01명에게"),
        ("03kg", "03kg"),
        ("03 kg", "03 kg"),
        ("₩01,000", "₩01,000"),
        ("₩ 01,000", "₩ 01,000"),
        ("09시", "아홉-시"),
        ("07시 05분", "일곱-시 오분"),
        ("009시", "아홉-시"),
        ("09 시", "09 시"),
    ],
)
def test_leading_zero_owner_matrix(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0", "영"),
        ("1", "일"),
        ("10", "십"),
        ("01월", "일월"),
        ("03일", "삼일"),
        ("010-1234-5678", "공일공 일이삼사 오육칠팔"),
    ],
)
def test_batch2_registered_non_preserve_owners_remain_narrow(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["00123abc", "A01", "01A", "한글01", "01한글"],
)
def test_batch2_identifier_and_alphanumeric_boundaries_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("03kg", "unit_percent_suffix_invalid_or_disallowed_spacing_preserve"),
        ("₩01,000", "currency_invalid_numeric_or_spacing_preserve"),
    ],
)
def test_batch2_invalid_owner_amounts_full_claim_preserve(
    text: str, reason: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert any(
        claim.owner == "preserve"
        and claim.claim_type == "preserve"
        and claim.reason == reason
        and (claim.span.start, claim.span.end) == (0, len(text))
        for claim in output.trace.claim_logs
    )
    assert output.render_pieces[0].text == text
    assert output.render_pieces[0].provenance == "ORIGINAL_BOUNDARY"


def test_suffix_clock_leading_zero_uses_time_surface() -> None:
    text = "07시 05분"
    output = transform_with_trace(text)
    time_claims = [
        claim for claim in output.trace.claim_logs if claim.owner == "time"
    ]

    assert output.normalized_text == "일곱-시 오분"
    assert [(claim.span.start, claim.span.end) for claim in time_claims] == [
        (0, 2),
        (4, 6),
    ]
    assert all(
        claim.surface_type == "TIME_SURFACE"
        and claim.reason
        in {"time_hour_korean_context", "time_minute_korean_context"}
        for claim in time_claims
    )
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)


def test_batch2_bare_and_counter_leading_zero_have_no_generated_numeric_reading() -> None:
    for text in ("0001", "01명"):
        output = transform_with_trace(text)
        assert output.normalized_text == text
        assert not any(
            piece.provenance == "GENERATED_READING"
            for piece in output.render_pieces
        )


def test_batch2_identifier_payload_and_date_owners_are_independent() -> None:
    text = "ID: 00123 기록은 2025.01.03에 갱신한다"
    output = transform_with_trace(text)

    assert (
        output.normalized_text
        == "아이디: 00123 기록은 이천이십오년 일월 삼일에 갱신한다"
    )
    assert any(claim.owner == "acronym_fallback" for claim in output.trace.claim_logs)
    assert any(claim.owner == "date" for claim in output.trace.claim_logs)
    payload_start = text.index("00123")
    assert any(
        piece.text == "00123"
        and piece.provenance == "ORIGINAL_BOUNDARY"
        and piece.source_span is not None
        and (piece.source_span.start, piece.source_span.end)
        == (payload_start, payload_start + 5)
        for piece in output.render_pieces
    )


def test_batch2_phone_and_counter_boundaries_are_independent() -> None:
    text = "010-1234-5678 01명"
    output = transform_with_trace(text)

    assert output.normalized_text == "공일공 일이삼사 오육칠팔 01명"
    assert any(
        claim.owner == "hyphen_digit_blocks"
        and (claim.span.start, claim.span.end) == (0, 13)
        for claim in output.trace.claim_logs
    )
    assert not any(
        piece.owner == "counter_noun" for piece in output.render_pieces
    )
    assert output.render_pieces[-2].text == "01"
    assert output.render_pieces[-2].provenance == "ORIGINAL_BOUNDARY"
