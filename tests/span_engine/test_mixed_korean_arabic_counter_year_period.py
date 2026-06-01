from __future__ import annotations

import pytest

from engine.main import transform_with_rollout
from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("지난 1년간", "지난 일 년간"),
        ("지난 2년간", "지난 이 년간"),
        ("지난 10년간", "지난 십 년간"),
        ("1년간", "일 년간"),
        ("이민자 6천400명 가운데", "이민자 육천사백 명 가운데"),
        ("6천400명", "육천사백 명"),
        ("6천400명 가운데 43%가", "육천사백 명 가운데 사십삼 퍼센트가"),
        (
            "내무부 자료에 따르면 지난 1년간 국경에서 미성년자라고 주장한 이민자 6천400명 가운데 43%가 성인으로 판명됐습니다.",
            "내무부 자료에 따르면 지난 일 년간 국경에서 미성년자라고 주장한 이민자 육천사백 명 가운데 사십삼 퍼센트가 성인으로 판명됐습니다.",
        ),
    ],
)
def test_mixed_counter_and_year_period_positive_production(
    text: str, expected: str
) -> None:
    assert transform_with_rollout(text, mode="span_default", include_debug=False) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6400명", "육천사백 명"),
        ("6,400명", "육천사백 명"),
        ("6천 400명", "육천 사백 명"),
        ("6천400", "6천400"),
        ("1년", "일년"),
        ("지난 1년 동안", "지난 일년 동안"),
        ("3시간 18분", "세 시간 십팔분"),
        ("21명", "스물한 명"),
        ("31명", "서른한 명"),
        ("43%", "사십삼 퍼센트"),
    ],
)
def test_mixed_counter_and_year_period_existing_outputs(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "6천400abc",
        "6천400명abc",
        "6천400명/log",
        "/path/6천400명/log",
        "https://example.com?q=6천400명",
        '{"count":"6천400명"}',
        "`6천400명`",
        "1년간abc",
        "/path/1년간/log",
        "https://example.com?q=1년간",
        '{"period":"1년간"}',
        "`1년간`",
    ],
)
def test_mixed_counter_and_year_period_preserve_contexts(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[6천400명]", "6천400명"),
        ("[1년간]", "1년간"),
    ],
)
def test_mixed_counter_and_year_period_square_bracket_unwrap(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_mixed_counter_and_year_period_claim_owners() -> None:
    counter_output = transform_with_trace("6천400명")
    year_output = transform_with_trace("1년간")

    assert counter_output.normalized_text == "육천사백 명"
    assert any(claim.owner == "counter_noun" for claim in counter_output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in counter_output.trace.claim_logs)

    assert year_output.normalized_text == "일 년간"
    assert any(claim.owner == "duration" for claim in year_output.trace.claim_logs)
    assert not any(claim.owner == "counter_noun" for claim in year_output.trace.claim_logs)
