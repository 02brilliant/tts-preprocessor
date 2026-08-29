from __future__ import annotations

import pytest

from engine.span_engine.currency import (
    CURRENCY_CODE_READINGS,
    CURRENCY_SYMBOL_READINGS,
    KOREAN_CURRENCY_SUFFIX_READINGS,
)
from engine.span_engine.transform import transform, transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1000원", "천-원"),
        ("1,000원", "천-원"),
        ("1,000 원", "천-원"),
        ("KRW1000", "천-원"),
        ("KRW1,000", "천-원"),
        ("KRW 1,000", "천-원"),
        ("₩1000", "천-원"),
        ("₩1,000", "천-원"),
        ("￦1,000", "천-원"),
        ("1000KRW", "천-원"),
        ("1,000KRW", "천-원"),
        ("1,000 KRW", "천-원"),
    ],
)
def test_krw_integer_forms_share_canonical_output(source: str, expected: str) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1000.50원", "천쩜오영-원"),
        ("1,000.50원", "천쩜오영-원"),
        ("1,000.50 원", "천쩜오영-원"),
        ("KRW1000.50", "천쩜오영-원"),
        ("KRW1,000.50", "천쩜오영-원"),
        ("KRW 1,000.50", "천쩜오영-원"),
        ("₩1000.50", "천쩜오영-원"),
        ("₩1,000.50", "천쩜오영-원"),
        ("￦1,000.50", "천쩜오영-원"),
        ("1000.50KRW", "천쩜오영-원"),
        ("1,000.50KRW", "천쩜오영-원"),
        ("1,000.50 KRW", "천쩜오영-원"),
    ],
)
def test_krw_decimal_forms_share_canonical_output(source: str, expected: str) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("+1000원", "플러스 천-원"),
        ("+1,000원", "플러스 천-원"),
        ("+1,000 원", "플러스 천-원"),
        ("KRW+1000", "플러스 천-원"),
        ("KRW+1,000", "플러스 천-원"),
        ("KRW +1,000", "플러스 천-원"),
        ("₩+1000", "플러스 천-원"),
        ("₩+1,000", "플러스 천-원"),
        ("+₩1000", "플러스 천-원"),
        ("+₩1,000", "플러스 천-원"),
        ("+1000KRW", "플러스 천-원"),
        ("+1,000KRW", "플러스 천-원"),
        ("+1,000 KRW", "플러스 천-원"),
    ],
)
def test_krw_plus_sign_forms_share_canonical_output(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("-1000원", "마이너스 천-원"),
        ("-1,000원", "마이너스 천-원"),
        ("-1,000 원", "마이너스 천-원"),
        ("KRW-1000", "마이너스 천-원"),
        ("KRW-1,000", "마이너스 천-원"),
        ("KRW -1,000", "마이너스 천-원"),
        ("₩-1000", "마이너스 천-원"),
        ("₩-1,000", "마이너스 천-원"),
        ("-₩1000", "마이너스 천-원"),
        ("-₩1,000", "마이너스 천-원"),
        ("-1000KRW", "마이너스 천-원"),
        ("-1,000KRW", "마이너스 천-원"),
        ("-1,000 KRW", "마이너스 천-원"),
    ],
)
def test_krw_minus_sign_forms_share_canonical_output(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("+1,000.50원", "플러스 천쩜오영-원"),
        ("+1,000.50 원", "플러스 천쩜오영-원"),
        ("KRW+1,000.50", "플러스 천쩜오영-원"),
        ("KRW +1,000.50", "플러스 천쩜오영-원"),
        ("₩+1,000.50", "플러스 천쩜오영-원"),
        ("+₩1,000.50", "플러스 천쩜오영-원"),
        ("+1,000.50KRW", "플러스 천쩜오영-원"),
        ("+1,000.50 KRW", "플러스 천쩜오영-원"),
        ("-2,500.75원", "마이너스 이천오백쩜칠오-원"),
        ("-2,500.75 원", "마이너스 이천오백쩜칠오-원"),
        ("KRW-2,500.75", "마이너스 이천오백쩜칠오-원"),
        ("KRW -2,500.75", "마이너스 이천오백쩜칠오-원"),
        ("₩-2,500.75", "마이너스 이천오백쩜칠오-원"),
        ("-₩2,500.75", "마이너스 이천오백쩜칠오-원"),
        ("-2,500.75KRW", "마이너스 이천오백쩜칠오-원"),
        ("-2,500.75 KRW", "마이너스 이천오백쩜칠오-원"),
    ],
)
def test_krw_signed_decimal_forms_share_canonical_output(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_krw_form_equivalence_matrix() -> None:
    integer_forms = [
        "1,000원",
        "1,000 원",
        "KRW1000",
        "KRW1,000",
        "KRW 1,000",
        "₩1000",
        "₩1,000",
        "￦1,000",
        "1000KRW",
        "1,000KRW",
        "1,000 KRW",
    ]
    assert {transform(source) for source in integer_forms} == {"천-원"}

    signed_decimal_forms = [
        "-2,500.75원",
        "-2,500.75 원",
        "KRW-2,500.75",
        "KRW -2,500.75",
        "₩-2,500.75",
        "-₩2,500.75",
        "-2,500.75KRW",
        "-2,500.75 KRW",
    ]
    assert {transform(source) for source in signed_decimal_forms} == {
        "마이너스 이천오백쩜칠오-원"
    }


def test_registered_non_krw_currency_smoke_equivalence() -> None:
    for code, reading in CURRENCY_CODE_READINGS.items():
        if reading == "원":
            continue
        forms = [f"{code}1000", f"{code}1,000", f"{code} 1,000", f"1000{code}", f"1,000{code}", f"1,000 {code}"]
        forms.extend(
            f"{marker}1,000"
            for marker, marker_reading in CURRENCY_SYMBOL_READINGS.items()
            if marker_reading == reading
        )
        forms.extend(
            f"1,000{suffix}"
            for suffix, suffix_reading in KOREAN_CURRENCY_SUFFIX_READINGS.items()
            if suffix_reading == reading
        )
        outputs = {transform(source) for source in forms}
        assert outputs == {f"천-{reading}"}


@pytest.mark.parametrize(
    "source",
    [
        "+01.5원",
        "+01.5 원",
        "+1,00.5원",
        "+1,00.5 원",
        "+.5원",
        "+.5 원",
        "1.원",
        "1. 원",
        "KRW +01.5",
        "KRW+01.5",
        "KRW +1,00.5",
        "KRW+1,00.5",
        "KRW +.5",
        "KRW+.5",
        "KRW 1.",
        "KRW1.",
        "₩+01.5",
        "+₩01.5",
        "₩+1,00.5",
        "+₩1,00.5",
        "₩+.5",
        "+₩.5",
        "₩1.",
        "+01.5KRW",
        "+01.5 KRW",
        "+1,00.5KRW",
        "+1,00.5 KRW",
        "+.5KRW",
        "+.5 KRW",
        "1.KRW",
        "1. KRW",
        "--₩1,000",
        "₩--1,000",
        "KRW+-1,000",
    ],
)
def test_invalid_currency_numeric_blocks_preserve_without_partial_fallback(
    source: str,
) -> None:
    assert transform(source) == source


def test_compound_plus_minus_currency_amount_uses_residual_signed_reading() -> None:
    assert transform("+-1,000원") == "플러스 마이너스 천원"


@pytest.mark.parametrize(
    "source",
    [
        "1,000  원",
        "1,000\t원",
        "1,000\n원",
        "KRW  1,000",
        "KRW\t1,000",
        "KRW\n1,000",
        "1,000  KRW",
        "1,000\tKRW",
        "1,000\nKRW",
    ],
)
def test_currency_spacing_limited_to_attached_or_one_ascii_space(
    source: str,
) -> None:
    from engine.prosody.paragraph import split_paragraphs
    from engine.span_engine.language_gate import has_hangul_syllable

    expected = split_paragraphs(source) if has_hangul_syllable(source) else source
    assert transform(source) == expected
    trace = transform_with_trace(source).trace
    assert trace is not None
    assert not any(log.owner == "currency" for log in trace.claim_logs)


@pytest.mark.parametrize(
    "source",
    [
        "`1,000원`",
        "`KRW1000`",
        "`₩1,000`",
        "`1,000 KRW`",
        '{"price":"1,000원"}',
        '{"price":"KRW1000"}',
        '{"price":"₩1,000"}',
        '{"price":"1,000 KRW"}',
        "/path/1,000원/log",
        "/path/KRW1000/log",
        "/path/₩1,000/log",
        "/path/1,000KRW/log",
        "https://example.com?q=KRW1000",
        "SKU-KRW1000",
        "version-KRW1000",
        "ABC1000KRW",
    ],
)
def test_currency_protected_and_code_like_contexts_preserve(source: str) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("+1.5 kg", "플러스 일쩜오-킬로그램"),
        ("+25 %", "플러스 이십오-퍼센트"),
        ("+25 ℃", "영상 이십오도"),
        ("1~2 kg", "일에서 이-킬로그램"),
        ("1-2 kg", "일에서 이-킬로그램"),
        ("3:4 테스트", "삼 대 사 테스트"),
        ("1-2테스트", "1-2테스트"),
    ],
)
def test_currency_non_target_regressions(source: str, expected: str) -> None:
    assert transform(source) == expected
