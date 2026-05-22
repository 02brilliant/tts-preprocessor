from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_phase17c_admin_suffix_bracket_outputs() -> None:
    assert transform("[종로3가]") == "종로3가"
    assert transform("주소는 [종로3가]입니다") == "주소는 종로3가입니다"
    assert transform("(종로3가)") == ""
    assert transform("주소는 (종로3가)입니다") == "주소는 입니다"


def test_phase17c_admin_suffix_bracket_trace_debug() -> None:
    output = transform_with_trace("[종로3가]")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.trace.bracket_filter_logs
    assert not any(
        claim.owner == "administrative_suffix" for claim in output.trace.claim_logs
    )
