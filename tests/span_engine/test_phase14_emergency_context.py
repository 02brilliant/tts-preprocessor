from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("긴급번호 112는", "긴급번호 일일이는"),
        ("화재가 나면 119에 신고", "화재가 나면 일일구에 신고"),
        ("소방 119로 연락", "소방 일일구로 연락"),
        ("경찰 112에 신고", "경찰 일일이에 신고"),
        ("응급 상황은 119에서 처리", "응급 상황은 일일구에서 처리"),
    ],
)
def test_emergency_context_and_allowed_tail(text: str, expected: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert any(claim.owner == "emergency" for claim in output.trace.claim_logs)
    assert any(
        log.stage == "emergency_gate" and log.decision == "pass"
        for log in output.trace.gate_logs
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("긴급번호 112은", "긴급번호 일일이는"),
        ("긴급번호 119을", "긴급번호 일일구를"),
        ("긴급번호 119로", "긴급번호 일일구로"),
        ("긴급번호 112이", "긴급번호 일일이이"),
    ],
)
def test_emergency_safe_particle_interaction(text: str, expected: str) -> None:
    assert transform(text) == expected
