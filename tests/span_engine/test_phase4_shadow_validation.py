from __future__ import annotations

import pytest

from engine.span_engine import RenderPiece
from engine.span_engine.render import render_tokens_pass_through
from engine.span_engine.shadow import build_shadow_buffer
from engine.span_engine.tokenizer import tokenize_immutable_spans
from engine.span_engine.validation import validate_shadow


@pytest.mark.parametrize(
    "raw_text",
    [
        "안녕하세요",
        "전문  가",
        "안녕하세요,",
        "AI는 123입니다",
        "회의는 13:05에 시작한다",
        "emoji 😀 테스트",
        "zero\u200bwidth",
    ],
)
def test_pass_through_render_passes_shadow_validation(raw_text: str) -> None:
    tokens = tokenize_immutable_spans(raw_text)
    shadow = build_shadow_buffer(tokens)
    pieces = render_tokens_pass_through(tokens)
    result = validate_shadow(pieces, shadow)

    assert result.passed is True
    if shadow:
        assert result.logs
    assert all(log.passed for log in result.logs)


def test_validate_shadow_ignores_plain_generated_or_boundary_text_not_in_shadow() -> None:
    result = validate_shadow(
        [RenderPiece("스물한", "GENERATED_READING", None, owner="counter_noun")],
        [],
    )

    assert result.passed is True
