"""Presentation edits preserve exact character ownership without text matching."""
import pytest
import subprocess
import sys

from engine.main import transform_output
from engine.text_alignment import MappedText, rendered_index_map
from engine.prosody.paragraph import split_paragraphs, split_paragraphs_with_mapping
from LLM.provenance import build_normalization_snapshot


def test_paragraph_can_be_imported_before_span_engine_in_fresh_runtime():
    command = ("from engine.prosody.paragraph import split_paragraphs; "
               "from engine.main import transform; "
               "assert split_paragraphs('문장이 끝났다.') == '문장이 끝났다.'; "
               "assert transform('2개') == '두~개'")
    result = subprocess.run([sys.executable, "-c", command], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("source", [
    "  2개, 2개, 2개  ",
    "2개 (제외할 2개) 2개",
    "2개 {2개} 2개",
    "2개 [2개] 2개 【2개】 2개",
    "2개 {  2개\t2개  } 2개",
    "2개.\n2개.\n2개.",
    "2개를\n옮겼고 2개를 기록했다.",
    "2개\n\n2개",
    "\ue000 2개 (오늘) 2개",
    '회의에서 "2개\n2개"를 기록했다.',
    "주소는 https://example.com/245 이고 2개, 2개다.",
    "`2.50kg`과 2개 (오늘) 2개",
])
def test_final_coordinates_are_recorded_edits(source):
    output = transform_output(source)
    rendered = "".join(piece.text for piece in output.render_pieces)
    mapping = rendered_index_map(output)
    assert mapping is not None
    assert all(rendered[before] == output.normalized_text[after] for before, after in mapping.items())
    snapshot = build_normalization_snapshot(output)
    assert all(output.normalized_text[s.normalized_start:s.normalized_end] == s.text for s in snapshot.spans)
    for annotation in output.numeric_annotations:
        if annotation.output_span is not None:
            span = annotation.output_span
            assert output.normalized_text[span.start:span.end] == annotation.plan.text
    assert not output.trace.fallback_logs


@pytest.mark.parametrize("source", [
    "", " \t\n", "앞말\n뒷말", "앞말\n\n뒷말", "첫 문장.\r\n다음 문장.",
    '"인용문\n계속" 다음 문장.', "보고서는 충분히 긴 문장으로 구성되어 있다. " * 30,
])
def test_paragraph_mapping_keeps_policy_output_and_character_order(source):
    result = split_paragraphs_with_mapping(MappedText.identity(source))
    assert result.text == split_paragraphs(source)
    indices = [index for index in result.indices if index is not None]
    assert indices == sorted(set(indices))
    assert all(source[index] == result.text[position]
               for position, index in enumerate(result.indices) if index is not None)


@pytest.mark.parametrize("source", ["수량은  \n\n  2개이다.", "수량은 2 \n  개이다."])
def test_numeric_source_coordinates_survive_input_newline_normalization(source):
    output = transform_output(source)
    annotation = output.numeric_annotations[0]
    component = annotation.plan.components[0]
    assert source[component.source_span.start:component.source_span.end] == component.raw == "2"
    assert annotation.plan.coordinate_space == "source"
    span = annotation.plan.source_span
    if span is not None:
        assert source[span.start:span.end] == annotation.plan.raw
    else:
        # The owner includes a newly inserted trailing space. Its original end
        # is uncertain even though numeral and unit coordinates are exact.
        assert annotation.plan.raw == "2 "
        assert any(boundary.kind == "input_normalization" and boundary.source_span is None
                   for boundary in annotation.plan.boundaries)
    assert source[annotation.plan.unit_source_span.start:annotation.plan.unit_source_span.end] == "개"
    assert annotation.alignment == "exact"
