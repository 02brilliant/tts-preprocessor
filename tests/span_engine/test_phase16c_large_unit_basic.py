from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3만", "삼만"),
        ("12만", "십이만"),
        ("123만", "백이십삼만"),
        ("1000만", "천만"),
        ("2억", "이억"),
        ("21억", "이십일억"),
        ("3조", "삼조"),
        ("예산은 3억입니다", "예산은 삼억입니다"),
        ("수량은 12만입니다", "수량은 십이만입니다"),
        ("금액은 2조입니다", "금액은 이조입니다"),
    ],
)
def test_large_unit_atomic_basic_expected_output(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3만은 충분", "삼만은 충분"),
        ("3만를 넘다", "삼만를 넘다"),
        ("3만을 넘다", "삼만을 넘다"),
        ("2억으로 계산", "이억으로 계산"),
        ("2억로 계산", "이억로 계산"),
    ],
)
def test_large_unit_atomic_suffix_preservation(text: str, expected: str) -> None:
    assert transform(text) == expected
