from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_phase18c_no_paragraph_split_for_multi_sentence_text_yet() -> None:
    text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
    output = transform(text)

    assert "\n" not in output
    assert output == text


def test_phase18c_no_paragraph_split_yet_with_comma_adapter_active() -> None:
    text = "그리고 우리는 결과를 확인했다. 그러나 문제는 남아 있었다. 따라서 다음 단계를 진행한다."
    output = transform(text)

    assert "\n" not in output
    assert (
        output
        == "그리고, 우리는 결과를 확인했다. 그러나, 문제는 남아 있었다. 따라서, 다음 단계를 진행한다."
    )


def test_phase18c_trace_contract_has_no_paragraph_break_log_yet() -> None:
    output = transform_with_trace(
        "그리고 우리는 결과를 확인했다. 그러나 문제는 남아 있었다. 따라서 다음 단계를 진행한다."
    )
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == (
        "그리고, 우리는 결과를 확인했다. 그러나, 문제는 남아 있었다. 따라서, 다음 단계를 진행한다."
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
