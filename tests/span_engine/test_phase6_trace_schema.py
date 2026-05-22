from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, TraceLogEntry, TransformTrace


TRACE_FIELDS = [
    "source_map_logs",
    "tokenization_logs",
    "shadow_logs",
    "claim_logs",
    "claim_collision_logs",
    "gate_logs",
    "parser_logs",
    "fallback_logs",
    "preserve_logs",
    "particle_exception_logs",
    "render_logs",
    "validation_logs",
    "prosody_logs",
    "bracket_filter_logs",
]


def test_transform_trace_has_all_schema_log_lists_with_independent_defaults() -> None:
    trace1 = TransformTrace()
    trace2 = TransformTrace()

    for field_name in TRACE_FIELDS:
        assert isinstance(getattr(trace1, field_name), list)
        assert getattr(trace1, field_name) == []

    trace1.source_map_logs.append({"event": "source_map_built"})

    assert trace2.source_map_logs == []


def test_trace_log_entry_contract_and_metadata_independence() -> None:
    entry1 = TraceLogEntry(
        stage="tokenization",
        event="token_created",
        span=SourceSpan(0, 2),
        raw="안녕",
    )
    entry2 = TraceLogEntry(stage="tokenization", event="token_created")

    entry1.metadata["x"] = 1

    assert entry1.stage == "tokenization"
    assert entry1.event == "token_created"
    assert entry1.span == SourceSpan(0, 2)
    assert "x" not in entry2.metadata


@pytest.mark.parametrize(
    ("stage", "event", "span"),
    [
        (123, "event", None),
        ("stage", 123, None),
        ("stage", "event", (0, 1)),
    ],
)
def test_trace_log_entry_rejects_invalid_types(
    stage: object, event: object, span: object
) -> None:
    with pytest.raises((TypeError, ValueError)):
        TraceLogEntry(stage=stage, event=event, span=span)  # type: ignore[arg-type]
