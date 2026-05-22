from __future__ import annotations

import pytest

from engine.main import transform
from engine.pipeline.transform_engine import transform_text
from engine.prosody.comma import insert_commas


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안녕하세요, 그리고 갑니다", "안녕하세요, 그리고 갑니다"),
        ("하지만, 우리는 간다", "하지만, 우리는 간다"),
        ("안녕하세요 , 반갑습니다", "안녕하세요 , 반갑습니다"),
    ],
)
def test_prosody_preserves_existing_punctuation(text: str, expected: str):
    assert insert_commas(text) == expected


def test_prosody_comma_is_insert_only_against_normalized_output():
    normalized = transform_text("그리고 우리는 13:05에 출발한다")
    prosody = insert_commas(normalized)
    assert normalized == "그리고 우리는 십삼시 오분에 출발한다"
    assert prosody == "그리고, 우리는 십삼시 오분에 출발한다"
    assert prosody.replace(",", "") == normalized


def test_full_pipeline_prosody_keeps_protected_numeric_phrase_intact():
    assert transform("그리고 우리는 13:05에 출발한다") == "그리고, 우리는 십삼시 오분에 출발한다"
