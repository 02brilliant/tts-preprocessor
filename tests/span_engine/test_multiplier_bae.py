from __future__ import annotations

import pytest

from engine.main import transform, transform_debug


def _production_transform(src: str) -> str:
    return transform(src)


def _claim_owners(src: str) -> list[str]:
    result = transform_debug(src)
    return [
        claim["owner"]
        for claim in result["debug"]["trace"]["claim_logs"]
    ]


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("주가가 3배 이상 상승했다.", "주가가 세-배 이상 상승했다."),
        ("주가가 1배 올랐다.", "주가가 한-배 올랐다."),
        ("매출이 2배 늘었다.", "매출이 두-배 늘었다."),
        ("가격은 4배 뛰었다.", "가격은 네-배 뛰었다."),
        ("거래량은 10배 증가했다.", "거래량은 열-배 증가했다."),
        ("가격은 20배 뛰었다.", "가격은 스무-배 뛰었다."),
        ("사용자는 39배 늘었다.", "사용자는 서른아홉-배 늘었다."),
        ("규모는 40배 커졌다.", "규모는 사십-배 커졌다."),
        ("가치는 100배 상승했다.", "가치는 백-배 상승했다."),
        ("가치는 1000배 상승했다.", "가치는 천-배 상승했다."),
        ("수익률은 1.5배 올랐다.", "수익률은 일쩜오-배 올랐다."),
        ("수익률은 0.5배 올랐다.", "수익률은 영쩜오-배 올랐다."),
        ("거래액은 2.25배로 늘었다.", "거래액은 이쩜이오-배로 늘었다."),
        ("규모는 1,000배 확대됐다.", "규모는 천-배 확대됐다."),
        ("거래액은 1,000.5배 확대됐다.", "거래액은 천쩜오-배 확대됐다."),
    ],
)
def test_multiplier_bae_positive(src: str, expected: str) -> None:
    assert _production_transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("주가가 3배 상승했다.", "주가가 세-배 상승했다."),
        ("주가가 3 배 상승했다.", "주가가 세-배 상승했다."),
        ("수익이 1.5배였다.", "수익이 일쩜오-배였다."),
        ("수익이 1.5 배였다.", "수익이 일쩜오-배였다."),
    ],
)
def test_multiplier_bae_spacing_variants(src: str, expected: str) -> None:
    assert _production_transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("주가는 3배로 올랐다.", "주가는 세-배로 올랐다."),
        ("주가는 3배이었다.", "주가는 세-배이었다."),
        ("주가는 3배입니다.", "주가는 세-배입니다."),
        ("거래액은 2.25배로 늘었다.", "거래액은 이쩜이오-배로 늘었다."),
    ],
)
def test_multiplier_bae_tail_preservation(src: str, expected: str) -> None:
    assert _production_transform(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("`3배`", "`3배`"),
        ("[3배]", "3배"),
        ("/path/3배/log", "/path/3배/log"),
        ('{"value":"3배"}', '{"value":"3배"}'),
        ("A3배", "A3배"),
        ("v3배", "v3배"),
    ],
)
def test_multiplier_bae_protected_contexts(src: str, expected: str) -> None:
    assert _production_transform(src) == expected


@pytest.mark.parametrize(
    "src",
    [
        "주가가 03배 상승했다.",
        "주가가 1,00배 상승했다.",
        "주가가 .5배 상승했다.",
        "주가가 1.배 상승했다.",
        "주가가 +3배 상승했다.",
        "주가가 -3배 상승했다.",
        "주가가 –3배 상승했다.",
    ],
)
def test_multiplier_bae_invalid_numeric_does_not_claim(src: str) -> None:
    assert "multiplier" not in _claim_owners(src)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("차량 3대가 이동했다.", "차량 세-대가 이동했다."),
        ("차량 40대가 이동했다.", "차량 사십-대가 이동했다."),
        ("21명", "스물한-명"),
        ("40명", "사십-명"),
    ],
)
def test_multiplier_bae_does_not_break_counters(src: str, expected: str) -> None:
    assert _production_transform(src) == expected
