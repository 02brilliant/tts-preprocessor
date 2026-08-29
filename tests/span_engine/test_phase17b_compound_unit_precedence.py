from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_phase17b_precedence_regression_smoke() -> None:
    assert transform("90km/h") == "시속 구십 킬로미터"
    assert transform("15km/L") == "리터당 십오 킬로미터"
    assert transform("15.2km/L") == "리터당 십오쩜이 킬로미터"
    assert transform("120mg/dL") == "데시리터당 백이십 밀리그램"
    assert transform("90km") == "구십-킬로미터"
    assert transform("3~8cm") == "삼에서 팔-센티미터"
    assert transform("60fps") == "육십 에프피에스"
    assert transform("10Mbps") == "십 메가비피에스"


def test_phase17b_slash_owner_trace() -> None:
    output = transform_with_trace("10MB/s")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "compound_slash_unit" for claim in output.trace.claim_logs)


def test_phase17b_exact_owner_trace() -> None:
    output = transform_with_trace("60fps")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "compound_exact_unit" for claim in output.trace.claim_logs)
