from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("FTA는", "에프티에이는", "dictionary"),
        ("K-푸드", "케이푸드", "k_hangul_lexical"),
        ("3~8cm", "삼에서 팔 센티미터", "range_with_unit"),
        ("6402억", "육천사백이억", "large_unit_atomic"),
        ("-1.3도", "마이너스 일쩜삼도", "signed_number"),
        ("12·12 사태", "십이십이 사태", "event"),
    ],
)
def test_span_trace_emits_owned_surface_claim(
    text: str,
    expected: str,
    owner: str,
):
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert any(
        claim.owner == owner and claim.claim_type == "surface"
        for claim in output.trace.claim_logs
    )


def test_surface_claims_remain_protected_from_prosody_reentry():
    text = "그리고 FTA는 유지하고 AI·반도체 전략은 6402억 달러 규모다"
    output = transform_with_trace(text)
    assert output.normalized_text == transform(text)
    assert output.normalized_text.startswith("그리고,")
    assert all(not claim.reentry_allowed for claim in output.trace.claim_logs)
    assert any(log.action == "insert_generated_punct" for log in output.trace.prosody_logs)


def test_range_surface_remains_atomic_through_prosody():
    output = transform_with_trace("3~8cm 범위로 자란다")
    assert output.normalized_text == "삼에서 팔 센티미터 범위로 자란다"
    range_claims = [
        claim for claim in output.trace.claim_logs
        if claim.owner == "range_with_unit"
    ]
    assert len(range_claims) == 1
