import json

import pytest

from engine.main import transform_output, transform_simplified, transform
from engine.span_engine.models import SourceSpan
from LLM.provenance import build_normalization_snapshot, minimal_snapshot
from LLM.residual_preprocessor import preprocess_residual
from LLM.selection_pipeline import (
    SelectionDecision, build_selection_plan, compose_selection, selection_numeric_annotations,
)
from LLM.pronunciation_overlay import apply_locked_pronunciation_mutations
from LLM.validation_models import AllowedMutation


@pytest.mark.parametrize("stage", [3, 4])
def test_sliced_selection_preserves_numeric_options_and_rebases_only_normalized_coordinates(stage):
    text = "앞말 2번"
    full = build_selection_plan(text, stage=stage)
    sliced = full.for_span(3, len(text))
    full_candidate = next(c for c in full.candidates if c.surface == "2번")
    candidate = next(c for c in sliced.candidates if c.surface == "2번")
    assert candidate.numeric_options and len(candidate.numeric_options) == len(candidate.options)
    assert candidate.candidate_id == full_candidate.candidate_id
    assert candidate.options == full_candidate.options
    for original, option in zip(full_candidate.numeric_options, candidate.numeric_options):
        assert option.source_span == SourceSpan(0, 2)
        assert option.components[0].source_span == SourceSpan(0, 1)
        assert option.unit_source_span == SourceSpan(1, 2)
        assert option.source_span.start == original.source_span.start - 3
        assert option.components[0].render_span == original.components[0].render_span
    decision = SelectionDecision(candidate.candidate_id, 1)
    output = compose_selection("2번", plan=sliced, decisions=(decision,))
    annotations = selection_numeric_annotations(minimal_snapshot("2번"), plan=sliced, decisions=(decision,))
    assert output == "두~번"
    assert annotations[0].output_span == SourceSpan(0, 3)
    assert annotations[0].plan.components[0].source_span == SourceSpan(0, 1)


def test_residual_fraction_components_retain_reversed_original_coordinates():
    text = "전체의 3/4"
    plan = build_selection_plan(text, stage=3)
    candidate = next(c for c in plan.candidates if c.surface == "3/4")
    option = candidate.numeric_options[0]
    assert [(c.role, c.raw, c.source_span) for c in option.components] == [
        ("denominator", "4", SourceSpan(6, 7)), ("numerator", "3", SourceSpan(4, 5))]


@pytest.mark.parametrize('stage', [3,4])
def test_finite_numeric_selection_keeps_plan_without_payload_extension(stage):
    text = '3번'
    snapshot = build_normalization_snapshot(transform_output(text))
    plan = build_selection_plan(text, stage=stage, snapshot=snapshot)
    candidate = next(c for c in plan.candidates if c.surface == '3번')
    assert candidate.options == ('삼번','세~번')
    assert len(candidate.numeric_options) == len(candidate.options)
    assert 'numeric' not in json.dumps(candidate.to_payload())
    decision = SelectionDecision(candidate.candidate_id, 1)
    output = compose_selection(text, plan=plan, decisions=(decision,))
    annotations = selection_numeric_annotations(snapshot, plan=plan, decisions=(decision,))
    assert output == '세~번' and len(annotations) == 1
    assert annotations[0].output_span == SourceSpan(0,3)
    assert annotations[0].plan.coordinate_space == 'normalized_input'
    assert annotations[0].plan.components[0].numeral_system == 'native'
    assert annotations[0].plan.components[0].vowels[0].target == 'long'


def test_residual_structure_reuses_decimal_parts_and_projects_existing_readings():
    result = preprocess_residual('2.50kg', snapshot=minimal_snapshot('2.50kg'))
    assert result.text == '이~쩜-오영-킬로그램'
    assert result.snapshot.numeric_annotations[0].plan.components[0].fractional_part == '50'
    output = transform_output('ABC 2개, 2개')
    snapshot = build_normalization_snapshot(output)
    # Explicit replacement before repeated readings changes coordinates by its
    # length delta; no text searching is needed to disambiguate the two 두.
    first_space = output.normalized_text.index(' ')
    mutation = AllowedMutation(0,first_space,'test',output.normalized_text[:first_space],('앞말',))
    updated = apply_locked_pronunciation_mutations(output.normalized_text,
        mutations=(mutation,), snapshot=snapshot, owner='test', provenance='GENERATED_READING')
    assert len(updated.snapshot.numeric_annotations) == 2
    delta = len('앞말') - first_space
    for before, after in zip(snapshot.numeric_annotations, updated.snapshot.numeric_annotations):
        assert after.output_span.start == before.output_span.start + delta
        assert after.plan.source_span == before.plan.source_span
        assert updated.text[after.output_span.start:after.output_span.end] == after.plan.text


def test_common_output_across_rule_profiles():
    source = '2~5명과 전체의 3/4만큼을 옮겼다.'
    assert transform_simplified(source) == transform(source) == '두~명에서 다섯-명과 전체의 사~분의 삼만큼을 옮겼다.'


@pytest.mark.parametrize('stage', [3, 4])
def test_quantity_followup_plan_survives_locked_snapshot(stage):
    output = transform_output('40명과 2~5마리')
    snapshot = build_normalization_snapshot(output)
    assert output.normalized_text == '마흔-명과 두~마리에서 다섯-마리'
    assert [a.plan.semantic_kind for a in snapshot.numeric_annotations] == ['count', 'count']
    assert [tuple(c.numeral_system for c in a.plan.components)
            for a in snapshot.numeric_annotations] == [('native',), ('native', 'native')]
    plan = build_selection_plan(output.normalized_text, stage=stage, snapshot=snapshot)
    assert all(not any(a.output_span and candidate.start < a.output_span.end
                       and a.output_span.start < candidate.end
                       for a in snapshot.numeric_annotations) for candidate in plan.candidates)
