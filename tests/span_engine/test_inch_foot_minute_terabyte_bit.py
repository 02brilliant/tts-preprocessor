from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10in", "십 인치"),
        ("10in입니다", "십 인치입니다"),
        ("5ft", "오 피트"),
        ("5 ft", "오 피트"),
        ("3min", "삼 분"),
        ("3 min", "삼 분"),
        ("10TB", "십 테라바이트"),
        ("10 TB", "십 테라바이트"),
        ("2.5TB", "이쩜오 테라바이트"),
        ("3만TB", "삼만 테라바이트"),
        ("3만 TB", "삼만 테라바이트"),
        ("45~50만TB", "사십오에서 오십만 테라바이트"),
        ("3~5ft", "삼에서 오 피트"),
        ("3~5min", "삼에서 오 분"),
        ("3~5in", "삼에서 오 인치"),
        ("8bit", "팔 비트"),
        ("8 bit", "팔 비트"),
        ("8bits", "팔 비트"),
        ("2.5bit", "이쩜오 비트"),
        ("bit", "비트"),
        ("bits", "비트"),
        ("bit는", "비트는"),
        ("bit입니다", "비트입니다"),
        ("수 bit", "수 비트"),
        ("한글 bit 한글", "한글 비트 한글"),
        ("수 TB", "수 테라바이트"),
        ("10TB/s", "초당 십 테라바이트"),
        ("3m/min", "분속 삼 미터"),
    ],
)
def test_inch_foot_minute_terabyte_and_bit_units(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
            ("10 in", "10 in"),
            ("3만 in", "삼만 in"),
            ("3~5 in", "삼에서 오 in"),
        ("in", "in"),
        ("10inch", "10inch"),
        ("5ftabc", "5ftabc"),
        ("3minutes", "3minutes"),
        ("10TBabc", "10TBabc"),
        ("TB", "TB"),
        ("TB는", "티비는"),
        ("a bit", "a bit"),
        ("the bit", "the bit"),
        ("habit", "habit"),
        ("bitcoin", "bitcoin"),
        ("8bitabc", "8bitabc"),
        ("ft", "ft"),
        ("min", "min"),
        ("수 in", "수 in"),
        ("수 ft", "수 ft"),
        ("수 min", "수 min"),
    ],
)
def test_inch_foot_minute_terabyte_and_bit_guards(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_attached_inch_uses_simple_unit_owner() -> None:
    output = transform_with_trace("10in")
    assert any(
        claim.owner == "simple_unit" and claim.reason == "simple_unit_numeric_prefix"
        for claim in output.trace.claim_logs
    )


def test_bare_bit_uses_hangul_context_owner_path() -> None:
    output = transform_with_trace("bit")
    assert any(
        claim.owner == "simple_unit" and claim.reason == "hangul_context_unit"
        for claim in output.trace.claim_logs
    )
