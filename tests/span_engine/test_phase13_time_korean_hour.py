from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시", "세 시"),
        ("3시에 시작", "세 시에 시작"),
        ("3시 5분", "세 시 오분"),
        ("3시 5분 7초", "세 시 오분 칠초"),
        ("오후 3시", "오후 세 시"),
        ("오전 10시 30분", "오전 열 시 삼십분"),
        ("12시", "열두 시"),
        ("12시에", "열두 시에"),
        ("12시를", "열두 시를"),
        ("12시을", "열두 시을"),
        ("12시는", "열두 시는"),
        ("12시은", "열두 시은"),
        ("12시가", "열두 시가"),
        ("12시이", "열두 시이"),
        ("12시로", "열두 시로"),
        ("12시으로", "열두 시으로"),
        ("12시와", "열두 시와"),
        ("12시과", "열두 시과"),
        ("12시도", "열두 시도"),
        ("12시만", "열두 시만"),
        ("12시보다 늦게", "열두 시보다 늦게"),
        ("12시처럼 보인다", "열두 시처럼 보인다"),
        ("12시마다 알림", "열두 시마다 알림"),
        ("12시면 늦다", "열두 시면 늦다"),
        ("12시이면", "열두 시이면"),
        ("12시라면", "열두 시라면"),
        ("12시이라고 했다", "열두 시이라고 했다"),
        ("12시라고 했다", "열두 시라고 했다"),
        ("12시인데", "열두 시인데"),
        ("12시였다", "열두 시였다"),
        ("12시이었다", "열두 시이었다"),
        ("12시이다", "열두 시이다"),
        ("12시에는", "열두 시에는"),
        ("12시에서", "열두 시에서"),
        ("12시에도", "열두 시에도"),
        ("12시보다", "열두 시보다"),
        ("12시인", "열두 시인"),
    ],
)
def test_korean_hour_time(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("낮 12시를 기준", "낮 열두 시를 기준"),
        ("낮 12시는 기준", "낮 열두 시는 기준"),
        ("낮 12시가 기준", "낮 열두 시가 기준"),
        ("낮 12시로 기준", "낮 열두 시로 기준"),
        ("낮 12시면 늦다", "낮 열두 시면 늦다"),
        ("오전 12시를 기준", "오전 열두 시를 기준"),
        ("오후 3시는 어렵다", "오후 세 시는 어렵다"),
        ("밤 10시면 늦다", "밤 열 시면 늦다"),
        ("새벽 2시라고 했다", "새벽 두 시라고 했다"),
    ],
)
def test_korean_hour_time_safe_context_tail(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3시리즈",
        "A3시",
        "3시abc",
        "99시",
        "3시 99분",
        "3시 5분 99초",
        "12시리즈",
        "12시스템",
        "12시장",
        "12시험",
        "12시즌",
        "12시abc",
        "낮 12시리즈",
        "낮 12시스템",
        "낮 12시장",
        "낮 12시험",
        "낮 12시즌",
        "낮 12시abc",
    ],
)
def test_invalid_or_attached_korean_time_preserve(text: str) -> None:
    assert transform(text) == text


def test_korean_hour_time_safe_tail_trace() -> None:
    output = transform_with_trace("낮 12시를 기준")

    assert output.normalized_text == "낮 열두 시를 기준"
    assert any(
        claim.owner == "time" and claim.reason == "time_hour_korean_context"
        for claim in output.trace.claim_logs
    )
    assert not any(
        claim.reason == "attached_korean_time_preserve"
        for claim in output.trace.claim_logs
    )
    assert output.trace.particle_exception_logs == []


def test_korean_time_markers_remain_original_korean() -> None:
    output = transform_with_trace("3시 5분")

    assert output.normalized_text == "세 시 오분"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("세 ", "GENERATED_READING", SourceSpan(0, 1), "time"),
        ("시", "ORIGINAL_KOREAN", SourceSpan(1, 2), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(2, 3), None),
        ("오", "GENERATED_READING", SourceSpan(3, 4), "time"),
        ("분", "ORIGINAL_KOREAN", SourceSpan(4, 5), None),
    ]
