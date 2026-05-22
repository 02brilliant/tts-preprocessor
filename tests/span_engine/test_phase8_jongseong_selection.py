from __future__ import annotations

import pytest

from engine.span_engine.particle import (
    choose_safe_particle,
    final_hangul_syllable,
    has_jongseong,
    jongseong_index,
)


def test_final_hangul_syllable_uses_last_non_space_modern_hangul() -> None:
    assert final_hangul_syllable("에프티에이 ") == "이"
    assert final_hangul_syllable("유알엘") == "엘"
    assert final_hangul_syllable("ABC") is None


def test_jongseong_helpers_use_modern_hangul_syllable_codepoints() -> None:
    assert jongseong_index("이") == 0
    assert has_jongseong("이") is False
    assert has_jongseong("엘") is True
    assert has_jongseong("삼") is True


@pytest.mark.parametrize(
    ("reading", "particle", "expected"),
    [
        ("에프티에이", "은", "는"),
        ("유알엘", "는", "은"),
        ("에이아이", "을", "를"),
        ("삼", "를", "을"),
        ("에이아이", "으로", "로"),
        ("유알엘", "으로", "로"),
        ("십", "으로", "으로"),
        ("에이아이", "이", None),
        ("에이아이", "가", None),
        ("ABC", "은", None),
    ],
)
def test_choose_safe_particle(reading: str, particle: str, expected: str | None) -> None:
    assert choose_safe_particle(reading, particle) == expected
