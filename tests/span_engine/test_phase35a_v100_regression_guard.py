from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("90km/h이다", "시속 구십 킬로미터이다"),
        ("[3kg]", "3kg"),
        ("40℉abc", "40℉abc"),
        ("45m²", "사십오 제곱미터"),
        ("2.4PB", "이쩜사 페타바이트"),
        ("pH7.4test", "pH7.4test"),
        ("2.5%pa", "2.5%pa"),
        ("1/0", "1/0"),
        ("3시간 18분", "세 시간 십팔분"),
        ("1/3", "삼분의 일"),
        ("2.5%p", "이쩜오 퍼센트포인트"),
    ],
)
def test_phase35a_v100_and_phase34_regression_guard(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "①②③",
        "１２３",
        "⅓",
        "1,23,456원",
        "🚨 119 ☃ 45m²",
        "The weird value is ① and 45m².",
    ],
)
def test_phase35a_no_crash_invariant_extended(text: str) -> None:
    output = transform(text)
    assert isinstance(output, str)
    if text:
        assert output
