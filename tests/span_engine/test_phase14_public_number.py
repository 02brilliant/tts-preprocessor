from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("국민콜 110에 문의", "국민콜 일일공에 문의"),
        ("다산콜 120은", "다산콜 일이공은"),
        ("질병 상담 1339에 문의", "질병 상담 일삼삼구에 문의"),
    ],
)
def test_public_number_context_gate(text: str, expected: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert any(claim.owner == "public_number" for claim in output.trace.claim_logs)
    assert any(
        log.stage == "public_number_gate" and log.decision == "pass"
        for log in output.trace.gate_logs
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("110명 참석", "백십명 참석"),
        ("120명", "백이십명"),
        ("1339에 문의", "천삼백삼십구에 문의"),
    ],
)
def test_public_number_missing_context_falls_back_to_number(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert not any(claim.owner == "public_number" for claim in output.trace.claim_logs)
