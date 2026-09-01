from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import SIMPLE_UNIT_READINGS, SPECIAL_UNIT_READINGS


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('+1.5kg', '플러스 일-쩜-오-킬로그램'),
        ('+1.5 kg', '플러스 일-쩜-오-킬로그램'),
        ('-2.0kg', '마이너스 이-쩜-영-킬로그램'),
        ('-2.0 kg', '마이너스 이-쩜-영-킬로그램'),
        ('+1,000.50kg', '플러스 천-쩜-오영-킬로그램'),
        ('+1,000.50 kg', '플러스 천-쩜-오영-킬로그램'),
        ('1.5kg', '일-쩜-오-킬로그램'),
        ('1.5 kg', '일-쩜-오-킬로그램'),
        ('1,000.50kg', '천-쩜-오영-킬로그램'),
        ('1,000.50 kg', '천-쩜-오영-킬로그램'),
        ('+3.4cm', '플러스 삼-쩜-사-센티미터'),
        ('+3.4 cm', '플러스 삼-쩜-사-센티미터'),
        ('-3.4cm', '마이너스 삼-쩜-사-센티미터'),
        ('-3.4 cm', '마이너스 삼-쩜-사-센티미터'),
    ],
)
def test_registered_unit_attached_and_single_space_consistency(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("+25%", "플러스 이십오-퍼센트"),
        ("+25 %", "플러스 이십오-퍼센트"),
        ('-3.5%', '마이너스 삼-쩜-오-퍼센트'),
        ('-3.5 %', '마이너스 삼-쩜-오-퍼센트'),
        ('+1,000.50%', '플러스 천-쩜-오영-퍼센트'),
        ('+1,000.50 %', '플러스 천-쩜-오영-퍼센트'),
        ("25%", "이십오-퍼센트"),
        ("25 %", "이십오-퍼센트"),
        ('1,000.50%', '천-쩜-오영-퍼센트'),
        ('1,000.50 %', '천-쩜-오영-퍼센트'),
    ],
)
def test_percent_attached_and_single_space_consistency(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "+1.5  kg",
        "+1.5\tkg",
        "+1.5\nkg",
        "+25  %",
        "+25\t%",
        "+25\n%",
    ],
)
def test_suffix_spacing_limited_to_attached_or_one_ascii_space(source: str) -> None:
    assert transform(source) == source
    trace = transform_with_trace(source).trace
    assert trace is not None
    assert not any(
        log.owner in {"simple_unit", "special_unit"} for log in trace.claim_logs
    )


@pytest.mark.parametrize(
    "source",
    [
        "+01.5kg",
        "+01.5 kg",
        "01.5kg",
        "01.5 kg",
        "+1,00.5kg",
        "+1,00.5 kg",
        "+.5kg",
        "+.5 kg",
        "1.kg",
        "1. kg",
    ],
)
def test_invalid_unit_numeric_blocks_preserve_without_partial_fallback(
    source: str,
) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    "source",
    [
        "+01.5%",
        "+01.5 %",
        "+1,00.5%",
        "+1,00.5 %",
        "+.5%",
        "+.5 %",
        "1.%",
        "1. %",
    ],
)
def test_invalid_percent_numeric_blocks_preserve_without_partial_fallback(
    source: str,
) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    "source",
    [
        "/path/+1.5 kg/log",
        "/path/+25 %/log",
        "`+1.5 kg`",
        "`+25 %`",
        '{"unit":"+1.5 kg"}',
        '{"percent":"+25 %"}',
        "https://example.com?q=+1.5 kg",
        "email+tag@example.com",
    ],
)
def test_protected_contexts_preserve(source: str) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("+25 ℃", "영상 이십오도"),
        ("-3 ℃", "영하 삼도"),
        ("+77 °F", "화씨 영상 칠십칠도"),
        ("화씨 +77 °F", "화씨 영상 칠십칠도"),
        ("1~2 kg", "일에서 이-킬로그램"),
        ('+1.5~2 kg', '플러스 일-쩜-오에서 이-킬로그램'),
        ("1-2 kg", "일에서 이-킬로그램"),
        ("1-2테스트", "1-2테스트"),
        ("-1.5-2 kg", "-1.5-2 kg"),
        ("+1.5-2 kg", "+1.5-2 kg"),
        ("+1:2 테스트", "플러스 일 대 이 테스트"),
        ("3:4 테스트", "삼 대 사 테스트"),
        ("+1,000 원", "플러스 천-원"),
        ('-2,500.75원', '마이너스 이천오백-쩜-칠오-원'),
        ('-2,500.75 원', '마이너스 이천오백-쩜-칠오-원'),
        ("$1,000", "천-달러"),
        ("USD 1,000", "천-달러"),
    ],
)
def test_non_target_regressions_remain_unchanged(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_unit_registry_smoke_for_owner_supported_decimal_suffixes() -> None:
    skipped_suffixes = {
        "%",
        "％",
        "﹪",
        "℃",
        "℉",
        "º",
        "ºC",
        "ºF",
        "º C",
        "º F",
        "°",
        "°C",
        "°F",
        "° C",
        "° F",
    }
    suffixes = sorted(
        (set(SIMPLE_UNIT_READINGS) | set(SPECIAL_UNIT_READINGS)) - skipped_suffixes,
        key=len,
        reverse=True,
    )
    checked: list[str] = []
    checked_signed: list[str] = []
    for suffix in suffixes:
        attached_trace = transform_with_trace(f"1.5{suffix}").trace
        if attached_trace is None or not any(
            log.owner in {"simple_unit", "special_unit"}
            for log in attached_trace.claim_logs
        ):
            continue
        spaced_trace = transform_with_trace(f"1.5 {suffix}").trace
        if spaced_trace is None or not any(
            log.owner in {"simple_unit", "special_unit"}
            for log in spaced_trace.claim_logs
        ):
            continue
        checked.append(suffix)
        assert transform(f"1.5{suffix}") == transform(f"1.5 {suffix}")
        signed_attached_trace = transform_with_trace(f"+1.5{suffix}").trace
        signed_spaced_trace = transform_with_trace(f"+1.5 {suffix}").trace
        if (
            signed_attached_trace is not None
            and signed_spaced_trace is not None
            and any(
                log.owner in {"simple_unit", "special_unit"}
                for log in signed_attached_trace.claim_logs
            )
            and any(
                log.owner in {"simple_unit", "special_unit"}
                for log in signed_spaced_trace.claim_logs
            )
        ):
            checked_signed.append(suffix)
            assert transform(f"+1.5{suffix}") == transform(f"+1.5 {suffix}")
    assert {"kg", "cm"}.issubset(set(checked))
    assert {"kg", "cm"}.issubset(set(checked_signed))
