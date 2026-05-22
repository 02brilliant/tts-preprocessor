from __future__ import annotations

import json

import pytest

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("가격은 [3kg]입니다", "가격은 3kg입니다"),
        ("문서 [AI] 확인", "문서 AI 확인"),
        ("값은 [123]입니다", "값은 123입니다"),
        ("포맷은 [JSON]입니다", "포맷은 JSON입니다"),
        ("입력 [[K:사용자입력]] 확인", "입력 [K:사용자입력] 확인"),
    ],
)
def test_square_bracket_content_is_protected_and_unwrapped(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert transform(text) == expected
    assert not any(
        claim.owner in {"dictionary", "acronym_fallback", "number"}
        and claim.span.start >= text.index("[")
        and claim.span.end <= text.rindex("]") + 1
        for claim in output.trace.claim_logs
    )
    assert output.trace.bracket_filter_logs
    json.dumps(output_to_debug_dict(output), ensure_ascii=False)


def test_square_bracket_render_pieces_remain_pre_filter_for_validation() -> None:
    output = transform_with_trace("가격은 [3kg]입니다")

    assert output.normalized_text == "가격은 3kg입니다"
    assert "".join(piece.text for piece in output.render_pieces) == "가격은 [3kg]입니다"
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(log.event == "square_bracket_unwrapped" for log in output.trace.bracket_filter_logs)
