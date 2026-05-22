from __future__ import annotations

import json

from engine.span_engine import RenderPiece, ShadowUnit, SourceSpan, TransformTrace
from engine.span_engine.trace import trace_to_dict
from engine.span_engine.validation import validate_shadow


def test_failed_validation_trace_shape_is_json_serializable_and_diagnostic() -> None:
    shadow = [ShadowUnit("KOREAN_LITERAL", "전문가", SourceSpan(0, 3))]
    pieces = [RenderPiece("전문이", "ORIGINAL_KOREAN", SourceSpan(0, 3))]
    validation = validate_shadow(pieces, shadow)
    trace = TransformTrace()
    trace.validation_logs.extend(validation.logs)

    trace_dict = trace_to_dict(trace)

    json.dumps(trace_dict, ensure_ascii=False)
    first_log = trace_dict["validation_logs"][0]
    assert first_log["reason"] == "original_text_mismatch"
    assert first_log["expected"] == "전문가"
    assert first_log["actual"] == "전문이"
    assert first_log["span"] == {"start": 0, "end": 3, "length": 3}
