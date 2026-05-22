from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("그리고 우리는 결과를 확인했다", "그리고, 우리는 결과를 확인했다"),
        ("그러나 문제는 남아 있었다", "그러나, 문제는 남아 있었다"),
        ("하지만 테스트는 통과했다", "하지만, 테스트는 통과했다"),
        ("그런데 결과가 달랐다", "그런데, 결과가 달랐다"),
        ("따라서 다음 단계를 진행한다", "따라서, 다음 단계를 진행한다"),
        (
            "첫 문장입니다. 그리고 우리는 결과를 확인했다",
            "첫 문장입니다. 그리고, 우리는 결과를 확인했다",
        ),
        (
            "오늘은 비가 왔다. 그러나 일정은 유지됐다",
            "오늘은 비가 왔다. 그러나, 일정은 유지됐다",
        ),
    ],
)
def test_phase18b_leading_connector_comma_expected(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("그리고 90km/h입니다", "그리고, 시속 구십 킬로미터입니다"),
        ("그리고 123-456-7890입니다", "그리고, 일이삼 사오육 칠팔구공입니다"),
        ("그리고 2025-01-03입니다", "그리고, 이천이십오년 일월 삼일입니다"),
        ("그리고 종로3가입니다", "그리고, 종로삼가입니다"),
    ],
)
def test_phase18b_leading_connector_before_generated_surface_expected(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
