from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,000KB/s", "초당 천 킬로바이트"),
        ("1,000 KB/s", "초당 천 킬로바이트"),
    ],
)
def test_phase36b_hotfix_data_rate_integer_comma_regression(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.5KB/s", "초당 십이쩜오 킬로바이트"),
        ("12.5 KB/s", "초당 십이쩜오 킬로바이트"),
        ("12.5MB/s", "초당 십이쩜오 메가바이트"),
        ("12.5 MB/s", "초당 십이쩜오 메가바이트"),
        ("3.2GB/s", "초당 삼쩜이 기가바이트"),
        ("3.2 GB/s", "초당 삼쩜이 기가바이트"),
        ("4.8TB/s", "초당 사쩜팔 테라바이트"),
        ("4.8 TB/s", "초당 사쩜팔 테라바이트"),
        ("2.4PB/s", "초당 이쩜사 페타바이트"),
        ("2.4 PB/s", "초당 이쩜사 페타바이트"),
    ],
)
def test_phase36b_hotfix_decimal_data_rate(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "서버는 12.5MB/s 처리율을 기록했다.",
            "서버는 초당 십이쩜오 메가바이트 처리율을 기록했다.",
        ),
        (
            "내부 테스트에서는 3.2 GB/s 데이터 처리량을 확인했다.",
            "내부 테스트에서는 초당 삼쩜이 기가바이트 데이터 처리량을 확인했다.",
        ),
    ],
)
def test_phase36b_hotfix_embedded_korean_sentence(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_phase36b_hotfix_prevents_decimal_number_only_partial_rewrite() -> None:
    result = transform("12.5 MB/s")
    assert result == "초당 십이쩜오 메가바이트"
    for leftover in ("KB/s", "MB/s", "GB/s", "PB/s"):
        assert leftover not in result


@pytest.mark.parametrize(
    "text",
    [
        "KB/s",
        "MB/s",
        "1,000KB/speed",
        "12.5MB/sec",
        "12.5MB/second",
        "abc12.5MB/s",
        "1,00KB/s",
        "1,23,456MB/s",
        "1,,000GB/s",
        "1,000 KB / s",
        "12.5 MB / s",
    ],
)
def test_phase36b_hotfix_preserve_cases(text: str) -> None:
    assert transform(text) == text
