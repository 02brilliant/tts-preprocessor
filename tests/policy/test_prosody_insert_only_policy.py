from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace
from tests._span_prosody import apply_span_prosody


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안녕하세요, 그리고 갑니다", "안녕하세요, 그리고 갑니다"),
        ("하지만, 우리는 간다", "하지만, 우리는 간다"),
        ("안녕하세요 , 반갑습니다", "안녕하세요 , 반갑습니다"),
    ],
)
def test_prosody_preserves_existing_punctuation(text: str, expected: str):
    assert apply_span_prosody(text) == expected


def test_prosody_comma_is_insert_only_against_normalized_output():
    output = transform_with_trace("그리고 우리는 13:05에 출발한다")
    assert output.normalized_text == "그리고, 우리는 십삼시 오분에 출발한다"
    generated_commas = [
        piece
        for piece in output.render_pieces
        if piece.provenance == "GENERATED_PUNCT" and piece.text == ","
    ]
    assert len(generated_commas) == 1
    assert any(
        log.action == "insert_generated_punct"
        for log in output.trace.prosody_logs
    )


def test_full_pipeline_prosody_keeps_protected_numeric_phrase_intact():
    assert transform("그리고 우리는 13:05에 출발한다") == "그리고, 우리는 십삼시 오분에 출발한다"
