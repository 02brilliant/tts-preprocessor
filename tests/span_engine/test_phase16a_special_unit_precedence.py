from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform, transform_with_trace


def test_unsigned_special_unit_regression_kept() -> None:
    assert transform("5℃") == "오도"
    assert transform("3°") == "삼도"
    assert transform("20％") == "이십 퍼센트"
    assert transform("45㎡") == "사십오 제곱미터"


def test_signed_temperature_precedes_special_unit_in_trace() -> None:
    output = transform_with_trace("-2℃")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "signed_temperature" for claim in output.trace.claim_logs)
    assert any(log.owner == "signed_temperature" for log in output.trace.parser_logs)
    assert any(
        log.owner == "signed_temperature" for log in output.trace.render_logs
    )


def test_signed_degree_precedes_special_unit_in_trace() -> None:
    output = transform_with_trace("+3°")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "signed_degree" for claim in output.trace.claim_logs)
    assert any(log.owner == "signed_degree" for log in output.trace.parser_logs)


def test_unsigned_special_unit_does_not_claim_signed_owner() -> None:
    output_celsius = transform_with_trace("5℃")
    output_degree = transform_with_trace("3°")

    assert any(claim.owner == "special_unit" for claim in output_celsius.trace.claim_logs)
    assert not any(
        claim.owner == "signed_temperature"
        for claim in output_celsius.trace.claim_logs
    )
    assert any(claim.owner == "special_unit" for claim in output_degree.trace.claim_logs)
    assert not any(
        claim.owner == "signed_degree" for claim in output_degree.trace.claim_logs
    )
