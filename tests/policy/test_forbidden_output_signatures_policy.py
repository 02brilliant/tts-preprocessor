from __future__ import annotations

import pytest

from engine.main import transform


GLOBAL_FORBIDDEN_SIGNATURE_CASES = (
    ("전문가", "전문이"),
    ("있는", "있은"),
    ("FTA율", "에프티에 이"),
    ("AI이", "에이아가"),
    ("K-푸드", "케가-푸드"),
    ("6402억", "육천사백이 억"),
    ("3~8cm", "삼~8cm"),
    ("1∼11월", "일∼십일월"),
    ("12.3 비상계엄", "십이쩜삼 비상계엄"),
)

CONTEXTUAL_FORBIDDEN_SIGNATURE_CASES = (
    ("12.12", "십이십이 사태"),
    ("12·12", "십이십이 사태"),
    ("112는 일반 문맥이다", "일일이"),
    ("119명은 대기한다", "일일구"),
    ("3~8cm", "삼에서 팔 cm"),
    ("FTA은", "에프티에이은"),
    ("AI이", "에이아이가"),
)

PURE_HANGUL_INVARIANCE_CASES = (
    "전문가",
    "있는",
    "하지만",
    "있습니다",
    "전문  가",
    "안녕하세요 , 반갑습니다",
)


@pytest.mark.parametrize(("text", "forbidden"), GLOBAL_FORBIDDEN_SIGNATURE_CASES)
def test_global_forbidden_output_signatures(text: str, forbidden: str):
    actual = transform(text)
    assert forbidden not in actual, f"input={text!r} forbidden={forbidden!r} actual={actual!r}"


@pytest.mark.parametrize(("text", "forbidden"), CONTEXTUAL_FORBIDDEN_SIGNATURE_CASES)
def test_contextual_forbidden_output_signatures(text: str, forbidden: str):
    actual = transform(text)
    assert forbidden not in actual, f"input={text!r} forbidden={forbidden!r} actual={actual!r}"


@pytest.mark.parametrize("text", PURE_HANGUL_INVARIANCE_CASES)
def test_pure_hangul_literals_remain_unchanged(text: str):
    assert transform(text) == text
