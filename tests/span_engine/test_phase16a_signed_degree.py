from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-3°", "마이너스 삼도"),
        ("+3°", "플러스 삼도"),
        ("-3.5°", "마이너스 삼쩜오도"),
        ("+3.5°", "플러스 삼쩜오도"),
        ("각도는 -3°입니다", "각도는 마이너스 삼도입니다"),
    ],
)
def test_signed_degree_expected_output(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3°을 표시", "플러스 삼도를 표시"),
        ("+3°를 표시", "플러스 삼도를 표시"),
    ],
)
def test_signed_degree_safe_particle_interaction(text: str, expected: str) -> None:
    assert transform(text) == expected
