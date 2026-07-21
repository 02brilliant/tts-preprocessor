from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    "text",
    [
        "OpenAI",
        "USB3",
        "1e6",
        "3.2E-4",
        "1-1-9",
        "종로3가",
        "{{S:사용자입력}}",
        "㎏",
        "㎡",
        "１",
    ],
)
def test_phase8_unsupported_and_literal_inputs_preserve(text: str) -> None:
    if text == "1-1-9":
        assert transform(text) == "일 일 구"
    elif text == "종로3가":
        assert transform(text) == "종로삼가"
    else:
        assert transform(text) == text


def test_phase8_strong_bare_time_like_reads_as_time() -> None:
    assert transform("13:05") == "십삼시 오분"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.14", "삼쩜일사"),
        ("12.3 비상계엄", "십이삼 비상계엄"),
    ],
)
def test_phase28a_normalized_regression(text: str, expected: str) -> None:
    # Phase 28B: Expected to fail until Phase 28C
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[3kg]", "3kg"),
        ("(약) 3만원", "삼만 원"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
    ],
)
def test_phase9_bracket_filter_updates_phase8_literal_regression(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
