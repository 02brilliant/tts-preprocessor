from __future__ import annotations

import pytest

from engine.main import (
    transform,
    transform_simplified,
    transform_simplified_debug,
)
from engine.span_engine.profile import engine_profile
from engine.span_engine.transform import transform_with_trace
from engine.text_alignment import rendered_index_map


def test_minimal_correction_does_not_insert_automatic_paragraph_breaks() -> None:
    source = (
        "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
        "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
        "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
        "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
    )

    assert transform_simplified(source) == source
    assert transform_simplified_debug(source)["normalized_text"] == source
    # The simplified call must not disable paragraph splitting for later calls.
    assert "\n" in transform(source)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r", "\n\n"])
def test_minimal_correction_keeps_existing_sentence_breaks(newline: str) -> None:
    source = f"첫 문장입니다.{newline}두 번째 문장입니다."

    assert transform_simplified(source) == source
    assert transform_simplified_debug(source)["normalized_text"] == source
    assert transform(source) == "첫 문장입니다.\n\n두 번째 문장입니다."


def test_minimal_correction_retains_visual_line_joining_and_numeric_alignment() -> None:
    source = "수량은 2\n개입니다.\n다음 수량도 2개입니다."
    expected = "수량은 두~개입니다.\n다음 수량도 두~개입니다."

    assert transform_simplified(source) == expected
    assert transform_simplified_debug(source)["normalized_text"] == expected
    with engine_profile("simplified"):
        output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert not output.trace.fallback_logs
    mapping = rendered_index_map(output)
    assert mapping is not None
    rendered = "".join(piece.text for piece in output.render_pieces)
    assert all(rendered[before] == expected[after] for before, after in mapping.items())
    assert len(output.numeric_annotations) == 2
    for annotation in output.numeric_annotations:
        span = annotation.output_span
        assert span is not None
        assert expected[span.start:span.end] == annotation.plan.text
        component_span = annotation.plan.components[0].source_span
        assert source[component_span.start:component_span.end] == "2"
