from __future__ import annotations

import json

from engine.prosody.paragraph import split_paragraphs
from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def _long_paragraph_with_strong_transition() -> str:
    return (
        "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
        "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
        "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
        "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
    )


def test_phase18c_long_paragraph_inserts_newline_before_strong_transition() -> None:
    text = _long_paragraph_with_strong_transition()
    output = transform(text)

    assert "\n" in output
    assert output == split_paragraphs(text)


def test_phase18c_comma_adapter_unchanged_when_paragraph_split_applies() -> None:
    text = "그리고 우리는 결과를 확인했다. 그러나 문제는 남아 있었다. 따라서 다음 단계를 진행한다."
    output = transform(text)

    assert output.startswith(
        "그리고, 우리는 결과를 확인했다. 그러나, 문제는 남아 있었다. 따라서, 다음 단계를 진행한다."
    )


def test_phase18c_trace_contract_has_no_paragraph_break_render_piece() -> None:
    output = transform_with_trace(
        "그리고 우리는 결과를 확인했다. 그러나 문제는 남아 있었다. 따라서 다음 단계를 진행한다."
    )
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == transform(
        "그리고 우리는 결과를 확인했다. 그러나 문제는 남아 있었다. 따라서 다음 단계를 진행한다."
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
    assert not any(
        getattr(log, "metadata", {}).get("prosody_type") == "paragraph_break"
        for log in getattr(output.trace, "prosody_logs", [])
    )
    assert not any(
        piece.owner == "prosody"
        and piece.provenance == "GENERATED_PUNCT"
        and piece.metadata.get("prosody_type") == "paragraph_break"
        for piece in output.render_pieces
    )
