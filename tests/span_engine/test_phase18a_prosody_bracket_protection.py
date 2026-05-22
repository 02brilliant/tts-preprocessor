from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_phase18a_bracket_behavior_contract() -> None:
    assert transform("가격은 [3kg]입니다") == "가격은 3kg입니다"
    assert transform("번호는 (123-456-7890)입니다") == "번호는 입니다"
    assert transform("[90km/h]") == "90km/h"


def test_phase18a_bracket_trace_has_no_prosody_mutation() -> None:
    output = transform_with_trace("[90km/h]")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "90km/h"
    assert output.trace.bracket_filter_logs
    assert not getattr(output.trace, "prosody_logs", [])
