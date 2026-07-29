from __future__ import annotations

import pytest

from engine.main import transform, transform_debug
from engine.span_engine import SourceSpan, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("0분기", "영분기"),
        ("1분기 2분기", "일분기 이분기"),
        ("4분기", "사분기"),
        ("10분기", "십분기"),
        ("2025년 1분기", "이천이십오년 일분기"),
        ("1 분기", "일 분기"),
        ("제1분기", "제 일분기"),
    ),
)
def test_registered_quarter_suffix_reads_only_the_numeric_core(
    text: str,
    expected: str,
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("1분기부터 4분기까지", "일분기부터 사분기까지"),
        ("실적은 2분기였다.", "실적은 이분기였다."),
        ("1.5분기", "일쩜오 분기"),
        ("+1.5분기", "플러스 일쩜오 분기"),
        ("-1.5분기", "마이너스 일쩜오 분기"),
    ),
)
def test_quarter_suffix_preserves_attachment_and_reuses_decimal_policy(
    text: str,
    expected: str,
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    (
        "01분기",
        "1.분기",
        "1..5분기",
        "1,00분기",
        "+1분기",
        "-1분기",
        "4A분기",
        "1분기abc",
        "A1분기",
    ),
)
def test_quarter_suffix_malformed_or_code_like_surface_is_atomic(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    (
        "https://example.com/1분기",
        "/tmp/1분기.txt",
        "report_1분기.txt",
        '{"quarter":"1분기"}',
        "`1분기`",
    ),
)
def test_quarter_suffix_respects_protected_spans(text: str) -> None:
    assert transform(text) == text


def test_quarter_suffix_uses_numeric_suffix_owner_not_time_prefix_preserve() -> None:
    output = transform_with_trace("1분기")

    assert output.normalized_text == "일분기"
    assert any(
        claim.owner == "numeric_suffix"
        and claim.reason == "numeric_korean_suffix_fallback"
        and claim.span == SourceSpan(0, 1)
        for claim in output.trace.claim_logs
    )
    assert not any(
        claim.reason == "unsafe_korean_minute_second_suffix_preserve"
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.text == "일"
        and piece.provenance == "GENERATED_READING"
        and piece.source_span == SourceSpan(0, 1)
        and piece.owner == "numeric_suffix"
        for piece in output.render_pieces
    )
    assert any(
        piece.text == "분기"
        and piece.provenance == "ORIGINAL_KOREAN"
        and piece.source_span == SourceSpan(1, 3)
        for piece in output.render_pieces
    )


def test_quarter_suffix_debug_contract_has_no_contextual_decision_log() -> None:
    debug = transform_debug("1분기 2분기")

    assert debug["normalized_text"] == "일분기 이분기"
    claims = debug["debug"]["trace"]["claim_logs"]
    assert [claim["owner"] for claim in claims] == [
        "numeric_suffix",
        "numeric_suffix",
    ]
    assert debug["debug"]["trace"]["contextual_decision_logs"] == []


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("1~4분기", "일에서 사 분기"),
        ("1-4분기", "일에서 사 분기"),
    ),
)
def test_quarter_range_uses_general_range_policy_not_date_shared_suffix(
    text: str,
    expected: str,
) -> None:
    assert transform(text) == expected


def test_non_numeric_quarter_expression_is_unchanged() -> None:
    assert transform("이번 분기부터 다음 분기까지") == "이번 분기부터 다음 분기까지"
