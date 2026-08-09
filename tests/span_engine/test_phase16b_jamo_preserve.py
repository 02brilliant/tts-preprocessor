from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "ㆆ",
        "ㆍ",
        "ㅿ",
        "가",
        "한글",
        "안녕하세요",
        "ㄱAI",
        "AIㄱ",
        "ㄱ123",
        "123ㄱ",
        "AㄱB",
        "ㄱkg",
        "ㄱcm",
    ],
)
def test_jamo_preserve_and_unsafe_adjacency(text: str) -> None:
    assert transform(text) == text


def test_jamo_two_block_hyphen_code_policy() -> None:
    assert transform("ㄱ-1") == "기역-일"
