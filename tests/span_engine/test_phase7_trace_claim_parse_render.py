from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_owner_first_claim_trace_for_dictionary_acronym_and_number() -> None:
    cases = [("GPT", "dictionary"), ("AI", "acronym_fallback"), ('123', 'number')]

    for text, owner in cases:
        output = transform_with_trace(text)
        assert any(claim.owner == owner for claim in output.trace.claim_logs)


def test_managed_mixed_case_dictionary_input_has_dictionary_claim() -> None:
    output = transform_with_trace("OpenAI")

    assert output.normalized_text == "오픈 에이아이"
    assert any(claim.owner == "dictionary" for claim in output.trace.claim_logs)


def test_parser_and_render_trace_records_generated_owners() -> None:
    output = transform_with_trace("GPT 123")

    assert output.normalized_text == "지피티 백이십삼"
    assert any(log.owner == "dictionary" and log.decision == "success" for log in output.trace.parser_logs)
    assert any(log.owner == "number" and log.decision == "success" for log in output.trace.parser_logs)
    assert any(log.owner == "dictionary" and log.provenance == "GENERATED_READING" for log in output.trace.render_logs)
    assert any(log.owner == "number" and log.provenance == "GENERATED_READING" for log in output.trace.render_logs)
    assert all(log.passed for log in output.trace.validation_logs)


def test_debug_export_includes_generated_render_and_claim_parser_logs() -> None:
    debug = output_to_debug_dict(transform_with_trace("GPT 123"))

    json.dumps(debug, ensure_ascii=False)
    assert any(piece["provenance"] == "GENERATED_READING" for piece in debug["render_pieces"])
    assert debug["trace"]["claim_logs"]
    assert debug["trace"]["parser_logs"]
    assert debug["trace"]["render_logs"]
    assert debug["trace"]["validation_logs"]
