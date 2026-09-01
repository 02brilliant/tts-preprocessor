from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import (
    HANGUL_CONTEXT_UNIT_EXCLUSIONS,
    SIMPLE_UNIT_READINGS,
    SPECIAL_UNIT_READINGS,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("5sec", "오-초"),
        ("5 sec", "오-초"),
        ("5Sec", "오-초"),
        ("5secs", "오-초"),
        ("5ms", "오-밀리초"),
        ("5 ms", "오-밀리초"),
        ("5msec", "오-밀리초"),
        ("5㎳", "오-밀리초"),
        ("5µs", "오-마이크로초"),
        ("5μs", "오-마이크로초"),
        ("5us", "오-마이크로초"),
        ("5µsec", "오-마이크로초"),
        ("5μsec", "오-마이크로초"),
        ("5usec", "오-마이크로초"),
        ("5㎲", "오-마이크로초"),
        ("5ns", "오-나노초"),
        ("5nsec", "오-나노초"),
        ("5㎱", "오-나노초"),
        ("5ps", "오-피코초"),
        ("5㎰", "오-피코초"),
        ('2.5sec', '이-쩜-오-초'),
        ('2.5ms', '이-쩜-오-밀리초'),
        ("1,000ms", "천-밀리초"),
        ('+2.5sec', '플러스 이-쩜-오-초'),
        ("-3ms", "마이너스 삼-밀리초"),
        ('–2.5µs', '마이너스 이-쩜-오-마이크로초'),
        ("3만sec", "삼만-초"),
        ("3만 ms", "삼만-밀리초"),
        ('3.5만ms', '삼-쩜-오-만-밀리초'),
        ("45~50만sec", "사십오에서 오십만-초"),
        ("3~5ms", "삼에서 오-밀리초"),
        ("수 sec", "수 초"),
        ("수sec을", "수 초를"),
        ("수 ms", "수 밀리초"),
        ("수 ㎳", "수 밀리초"),
    ],
)
def test_registered_second_family_reads_like_other_latin_units(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(
        log.owner
        in {
            "simple_unit",
            "special_unit",
            "korean_numeric_unit",
            "range_with_unit",
        }
        for log in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("5s", "5s"),
        ("5S", "5S"),
        ("5SEC", "5SEC"),
        ("5MS", "5MS"),
        ("5US", "5US"),
        ("5second", "5second"),
        ("5seconds", "5seconds"),
        ("5secabc", "5secabc"),
        ("5msabc", "5msabc"),
        ("1/2sec", "1/2sec"),
        ("1/2ms", "1/2ms"),
        ("sec", "sec"),
        ("ms", "ms"),
        ("수 min", "수 min"),
        ("수 us", "수 us"),
        ("수 ps", "수 ps"),
        ("수 secs", "수 secs"),
        ("5m/sec", "초속 오 미터"),
        ("5m/s", "초속 오 미터"),
    ],
)
def test_second_family_keeps_single_letter_and_collision_guards(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_single_letter_s_stays_unregistered() -> None:
    assert "s" not in SIMPLE_UNIT_READINGS
    assert "S" not in SIMPLE_UNIT_READINGS
    assert "SEC" not in SIMPLE_UNIT_READINGS
    assert "MS" not in SIMPLE_UNIT_READINGS
    assert "US" not in SIMPLE_UNIT_READINGS
    assert {
        "sec": "초",
        "secs": "초",
        "ms": "밀리초",
        "msec": "밀리초",
        "µs": "마이크로초",
        "μs": "마이크로초",
        "us": "마이크로초",
        "ns": "나노초",
        "ps": "피코초",
    }.items() <= SIMPLE_UNIT_READINGS.items()
    assert {
        "㎳": "밀리초",
        "㎲": "마이크로초",
        "㎱": "나노초",
        "㎰": "피코초",
    }.items() <= SPECIAL_UNIT_READINGS.items()
    assert {"us", "usec", "ps", "secs", "Sec"} <= HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "sec" not in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "ms" not in HANGUL_CONTEXT_UNIT_EXCLUSIONS


def test_attached_second_unit_uses_simple_unit_owner() -> None:
    output = transform_with_trace("5sec")
    assert any(
        claim.owner == "simple_unit" and claim.reason == "simple_unit_numeric_prefix"
        for claim in output.trace.claim_logs
    )
