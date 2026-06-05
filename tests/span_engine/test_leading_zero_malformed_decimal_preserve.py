from __future__ import annotations

import pytest

from engine.main import transform_with_rollout


def normalize(src: str) -> str:
    return transform_with_rollout(src, mode="span_default", include_debug=False)


@pytest.mark.parametrize(
    "src",
    [
        "01.5",
        "001.5",
        "+01.5",
        "-01.5",
        "+001.5",
        "-001.5",
    ],
)
def test_standalone_leading_zero_malformed_decimals_preserve(src: str) -> None:
    assert normalize(src) == src


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("0.5", "영쩜오"),
        ("+0.5", "플러스 영쩜오"),
        ("-0.5", "마이너스 영쩜오"),
        ("1.5", "일쩜오"),
        ("+1.5", "플러스 일쩜오"),
        ("-1.5", "마이너스 일쩜오"),
        ("0.8초", "영쩜팔 초"),
        ("0.03%", "영쩜영삼 퍼센트"),
        ("0.5배", "영쩜오 배"),
        ("0.5명", "영쩜오 명"),
    ],
)
def test_valid_zero_decimal_behavior_unchanged(src: str, expected: str) -> None:
    assert normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("1.", "일."),
        ("3..140", "삼..백사십"),
        ("25..50", "이십오..오십"),
        ("2,34", "2,34"),
        ("2,,345", "2,,345"),
        ("2,34억", "2,34억"),
        ("3백..4십만", "3백..4십만"),
    ],
)
def test_segmented_malformed_numeric_behavior_unchanged(src: str, expected: str) -> None:
    assert normalize(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("`01.5`", "`01.5`"),
        ("[01.5]", "01.5"),
        ("/path/01.5/log", "/path/01.5/log"),
        ('{"value":"01.5"}', '{"value":"01.5"}'),
        ("A01.5", "A01.5"),
        ("v01.5", "v01.5"),
    ],
)
def test_leading_zero_malformed_decimal_protected_or_code_like(
    src: str, expected: str
) -> None:
    assert normalize(src) == expected
