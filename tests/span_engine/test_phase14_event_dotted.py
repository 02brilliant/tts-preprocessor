from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.12 사태", "십이십이 사태"),
        ("그리고 12.12 사태", "그리고, 십이십이 사태"),
        ("4.19 혁명", "사일구 혁명"),
        ("6.25 전쟁", "육이오 전쟁"),
        ("3.1 운동", "삼일 운동"),
        ("10.26 사건", "십이육 사건"),
        ("12.12사태", "십이십이사태"),
    ],
)
def test_dotted_event_with_immediate_keyword(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_dotted_event_claim_owner_and_keyword_preservation() -> None:
    output = transform_with_trace("12.12 사태")

    assert output.normalized_text == "십이십이 사태"
    assert any(claim.owner == "event" for claim in output.trace.claim_logs)
    assert ("십이십이", "GENERATED_READING", "event") in [
        (piece.text, piece.provenance, piece.owner) for piece in output.render_pieces
    ]
    assert ("사태", "ORIGINAL_KOREAN") in [
        (piece.text, piece.provenance) for piece in output.render_pieces
    ]
