from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 13:05에 시작한다", "회의는 십삼시 오분에 시작한다"),
        ("13:05에 시작한다", "십삼시 오분에 시작한다"),
        ("오후 9:30에 출발", "오후 아홉시 삼십분에 출발"),
        ("예약 시간은 10:00입니다", "예약 시간은 열시입니다"),
        ("마감은 23:59까지", "마감은 이십삼시 오십구분까지"),
        ("오늘 9:30 출발", "오늘 아홉시 삼십분 출발"),
    ],
)
def test_time_colon_gate_passes_with_context(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:30", "영시 삼십분"),
        ("13:05", "십삼시 오분"),
        ("24:00", "이십사시"),
    ],
)
def test_time_colon_gate_strong_bare_time_like_reads_as_time(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "score 12:30",
        "12:30 13:40",
        "99:00",
        "13:05abc",
        "a13:05",
        "13:05:99",
        "13:05:30",
        "00:00:00",
        "23:59:59",
    ],
)
def test_time_colon_gate_preserves_ambiguous_or_unsupported(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("13:99", "십삼 대 구십구"),
        ("1:2", "일 대 이"),
    ],
)
def test_time_colon_gate_non_time_like_broad_colon_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_time_colon_gate_defers_ratio_context_to_semantic_pair_owner() -> None:
    assert transform("비율 1:2") == "비율 일 대 이"


def test_strong_bare_time_records_gate_pass() -> None:
    output = transform_with_trace("13:05")

    assert output.normalized_text == "십삼시 오분"
    assert any(
        log.stage == "time_gate"
        and log.raw == "13:05"
        and log.decision == "pass"
        and log.reason == "strong_time_like_bare"
        for log in output.trace.gate_logs
    )
