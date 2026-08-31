from __future__ import annotations

from LLM.provenance import build_normalization_snapshot
from engine.span_engine.transform import transform_with_trace


def test_snapshot_projects_generated_readings_to_normalized_coordinates() -> None:
    output = transform_with_trace("AI는 3kg이다.")
    snapshot = build_normalization_snapshot(output)

    locked = [span for span in snapshot.spans if span.locked and not span.protected]
    assert locked
    for span in locked:
        assert snapshot.normalized_text[span.normalized_start:span.normalized_end] == span.text
    assert any("에이아이" in span.text for span in locked)
    assert any("삼-킬로그램" in span.text for span in locked)


def test_snapshot_marks_canonical_protected_literals() -> None:
    output = transform_with_trace("주소는 https://example.com/a1 입니다.")
    snapshot = build_normalization_snapshot(output)
    protected = [span for span in snapshot.spans if span.protected]
    assert [span.text for span in protected] == ["https://example.com/a1"]

