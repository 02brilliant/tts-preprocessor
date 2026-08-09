from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("러시아의 Su(수호이)는 전투기다", "러시아의 수호이는 전투기다"),
        ("Su(수호이)-57", "수호이-오십칠"),
        ("su(수호이)-57", "수호이-오십칠"),
        ("AI(인공지능) 플랫폼", "인공지능 플랫폼"),
        ("LG(엘지)는 기업이다", "엘지는 기업이다"),
        ("foo(수호이)는 코드다", "foo는 코드다"),
        ("LG(003550)의 인공지능(AI) 플랫폼", "엘지의 인공지능 플랫폼"),
    ],
)
def test_direct_latin_korean_parenthetical_alias(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_parenthesized_hangul_alias_uses_the_latin_token_span_only() -> None:
    output = transform_with_trace("Su(수호이)는 전투기다")

    assert output.normalized_text == "수호이는 전투기다"
    assert any(
        claim.owner == "parenthesized_hangul_alias"
        and claim.reason == "direct_latin_korean_parenthetical_alias"
        for claim in output.trace.claim_logs
    )
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(log.event == "parenthesis_elided" for log in output.trace.bracket_filter_logs)


def test_parenthesized_hangul_alias_keeps_following_hyphen_as_boundary() -> None:
    output = transform_with_trace("Su(수호이)-57")

    assert output.normalized_text == "수호이-오십칠"
    assert any(
        piece.text == "-" and piece.provenance == "ORIGINAL_BOUNDARY"
        for piece in output.render_pieces
    )
    assert all(log.passed for log in output.trace.validation_logs)
