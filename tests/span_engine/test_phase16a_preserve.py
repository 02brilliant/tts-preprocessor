from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "--2℃",
        "++2℃",
        "+-2℃",
        "-℃",
        "+℃",
        "-2.℃",
        "-.5℃",
        "-2.5.3℃",
        "-2,5℃",
        "-2℃abc",
        "abc-2℃",
        "-2℃kg",
    ],
)
def test_signed_temperature_and_degree_preserve_unsupported_forms(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-2 °C", "영하 이도"),
        ("-2도", "마이너스 이도"),
        ('-2.5', '마이너스 이-쩜-오'),
        ('+2.5', '플러스 이-쩜-오'),
    ],
)
def test_phase16d_signed_number_updates_former_preserve_cases(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
