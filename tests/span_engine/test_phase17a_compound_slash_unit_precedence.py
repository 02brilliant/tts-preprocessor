from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_compound_slash_unit_precedence_regression_smoke() -> None:
    assert transform("90km/h") == "시속 구십 킬로미터"
    assert transform("90km") == "구십-킬로미터"
    assert transform("15km/L") == "리터당 십오 킬로미터"
    assert transform("15.2km/L") == "리터당 십오쩜이 킬로미터"
    assert transform("3~8km/h") == "3~8km/h"
    assert transform("3~8cm") == "삼에서 팔-센티미터"


def test_compound_slash_unit_trace_owner() -> None:
    output = transform_with_trace("90km/h")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "compound_slash_unit" for claim in output.trace.claim_logs)


def test_simple_unit_owner_stays_simple_unit_without_slash() -> None:
    output = transform_with_trace("90km")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "simple_unit" for claim in output.trace.claim_logs)


def test_range_with_unit_owner_stays_range_with_unit() -> None:
    output = transform_with_trace("3~8cm")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "range_with_unit" for claim in output.trace.claim_logs)
