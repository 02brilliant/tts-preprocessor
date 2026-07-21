from __future__ import annotations

import json

import pytest

from engine.span_engine.compare import build_span_debug


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("3~8cm", "삼에서 팔 센티미터", "range_with_unit"),
        ("2025-01-03", "이천이십오년 일월 삼일", "date"),
        ("90km/h", "시속 구십 킬로미터", "compound_slash_unit"),
        ("[3kg]", "3kg", "special_unit"),
    ],
)
def test_phase19a_span_debug_shape_for_representative_cases(
    text: str, expected: str, owner: str
) -> None:
    debug = build_span_debug(text)

    json.dumps(debug, ensure_ascii=False)
    assert debug["normalized_text"] == expected
    assert "trace" in debug
    trace = debug["trace"]
    assert "claim_logs" in trace
    assert "render_logs" in trace
    assert "validation_logs" in trace
    if text != "[3kg]":
        assert any(log.get("owner") == owner for log in trace["claim_logs"])


def test_phase19a_span_debug_shape_for_prosody_case() -> None:
    debug = build_span_debug("그리고 우리는 결과를 확인했다")

    json.dumps(debug, ensure_ascii=False)
    assert debug["normalized_text"] == "그리고, 우리는 결과를 확인했다"
    assert "trace" in debug
    assert any(
        log.get("metadata", {}).get("prosody_type") == "comma"
        for log in debug["trace"]["prosody_logs"]
    )
    assert any(
        piece.get("owner") == "prosody"
        and piece.get("provenance") == "GENERATED_PUNCT"
        and piece.get("text") == ","
        for piece in debug["render_pieces"]
    )
