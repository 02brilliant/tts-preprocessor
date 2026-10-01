from dataclasses import replace
import json
from pathlib import Path

import pytest

from engine.main import transform, transform_output
from engine.span_engine.models import ContextualDecisionKind, SourceSpan
from engine.span_engine.numeric_plan import number_component, vowel_data
from engine.span_engine.numeric_plan import project_annotations
from engine.span_engine.trace import render_piece_to_dict


@pytest.mark.parametrize(('source', 'expected'), [
    ('2~5명', '두~명에서 다섯-명'), ('2~5개', '두~개에서 다섯-개'),
    ('20~25명', '스무-명에서 스물다섯-명'), ('39~40명', '서른아홉-명에서 마흔-명'),
    ('2~5명은', '두~명에서 다섯-명은'), ('2~5 개를', '두~개에서 다섯-개를'),
    ('40~41명', '마흔-명에서 마흔한-명'), ('5-2개', '다섯-개에서 두~개'),
    ('99~100개', '아흔아홉-개에서 백-개'), ('2~5가지', '두~가지에서 다섯-가지'),
    ('3/4만큼', '사~분의 삼만큼'), ('3/4만큼은', '사~분의 삼만큼은'),
    ('3/4만큼으로', '사~분의 삼만큼으로'), ('전체의 3/4만큼 옮겼다.', '전체의 사~분의 삼만큼 옮겼다.'),
])
def test_approved_changes(source, expected):
    result = transform_output(source)
    assert result.normalized_text == expected
    assert not result.trace.fallback_logs
    assert all(log.passed for log in result.trace.validation_logs)


@pytest.mark.parametrize(('source', 'expected'), [
    ('2', '이~'), ('20', '이~십'), ('22', '이~십이'), ('2개', '두~개'),
    ('12개', '열~두-개'), ('22개', '스물두-개'), ('40명', '마흔-명'), ('40사람', '마흔-사람'),
    ('2.05%', '이~쩜-영오-퍼센트'), ('2.50kg', '이~쩜-오영-킬로그램'),
    ('52,025', '오~만 이~천이십오'), ('123,456', '십이만 삼천사백오십육'),
    ('010-1234-5678', '공일공 일이삼사 오육칠팔'), ('2~5%', '이~에서 오~퍼센트'),
    ('2~5kg', '이~에서 오~킬로그램'), ('2~5분', '이~분에서 오~분'),
    ('6월', '유월'), ('10월', '시월'), ('-5℃', '영하 오~도'),
    ('14:25', '14:25'), ('회의는 14:25에 시작한다.', '회의는 십사시 이~십오분에 시작한다.'),
    ('3/4', '사~분의 삼'), ('3/4은', '사~분의 삼은'), ('3/4를', '사~분의 삼을'),
])
def test_retained_outputs(source, expected):
    assert transform(source) == expected


@pytest.mark.parametrize('source', [
    '3/4만큼테스트', '3/4만큼은테스트', 'https://example.com/3/4만큼',
    '/path/3/4만큼', '`3/4만큼`', 'A3/4만큼', '3/4만큼/x',
    '3/4만큼_foo', '3/4만큼123',
])
def test_fraction_tail_and_protection(source):
    assert transform(source) == source


def test_range_unit_provenance_and_particle_once():
    output = transform_output('2~5명은')
    copies = [p for p in output.render_pieces if p.metadata.get('generated_unit_copy')]
    assert len(copies) == 1
    assert (copies[0].text, copies[0].provenance, copies[0].source_span) == ('명', 'GENERATED_READING', SourceSpan(3, 4))
    assert output.normalized_text.count('은') == 1
    assert any(p.provenance == 'ORIGINAL_KOREAN' and p.text == '명은' for p in output.render_pieces)
    plan = output.numeric_annotations[0].plan
    assert plan.semantic_kind == 'count' and plan.numeric_form == 'range'
    assert [c.raw for c in plan.components] == ['2', '5']
    assert [c.numeral_system for c in plan.components] == ['native', 'native']


def vowels(source):
    return [v for a in transform_output(source).numeric_annotations for c in a.plan.components for v in c.vowels]


@pytest.mark.parametrize('source', ['2','20','22','202','2002','4','40','42','5','50','52',
    '2개','12개','22개','3명','13명','23명','4마리','14마리','24마리',
    '10개','20개','10,000','20,000','52,025'])
def test_vowel_representative_set(source):
    targets = vowels(source)
    assert targets
    for target in targets:
        assert target.target in {'long', 'short', 'unresolved'}
        assert not hasattr(target, 'realized')
        if target.target != 'unresolved':
            assert target.lexeme_id and target.sources
        if target.lexical_length == 'long':
            assert target.target == ('long' if target.syllable_position == 0 else 'short')


def test_native_and_sino_position_are_lexical_not_tts_boundaries():
    assert [(v.lexeme, v.target) for v in vowels('12개')] == [('열','long'),('두','short')]
    assert vowels('2개')[0].target == 'long'
    assert vowels('22개')[-1].target == 'short'
    assert [(v.lexeme,v.target) for v in vowels('202') if v.lexeme == '이'] == [('이','long'),('이','short')]
    # Inserted 천-boundary must not lengthen subsequent 사/오.
    assert all(v.target == 'short' for v in vowels('123,456') if v.lexeme in {'사','오'})
    assert [v.target for v in vowels('52,025') if v.lexeme == '이'] == ['long','short']
    assert vowels('10,000')[0].target == 'unresolved'  # unverified lexical entry
    assert not transform_output('두 개, 이 사람').numeric_annotations


def test_zeroes_and_sequence_domains():
    for source, fraction in [('2.05%','05'),('2.50kg','50')]:
        plan = transform_output(source).numeric_annotations[0].plan
        assert plan.components[0].fractional_part == fraction
        digits = [v for v in plan.components[0].vowels if 'fraction_digits' in v.domain]
        assert len(digits) == 2 and all(v.target == 'unresolved' for v in digits)
        assert any(b.kind == 'number_unit' and b.text == '-' for b in plan.boundaries)
    plan = transform_output('010-1234-5678').numeric_annotations[0].plan
    assert [c.raw for c in plan.components] == ['010','1234','5678']
    assert all(v.target == 'unresolved' for c in plan.components for v in c.vowels)
    assert any(b.origin == 'original' and b.kind == 'identifier_separator' for b in plan.boundaries)
    assert any(b.origin == 'generated' and b.kind == 'identifier_group' for b in plan.boundaries)


def test_confirmed_contextual_number_keeps_known_source_and_unit_coordinates():
    source = "학생을 3조로 나눴다"
    output = transform_output(source)
    assert output.normalized_text == "학생을 세~조로 나눴다"
    plan = output.numeric_annotations[0].plan
    assert plan.components[0].source_span == SourceSpan(4, 5)
    assert plan.unit_source_span == SourceSpan(5, 6)
    assert plan.components[0].numeral_system == "native"


@pytest.mark.parametrize(("source", "expected", "form", "raws"), [
    ("+3조각", "플러스 세-조각", "integer", ["+3"]),
    ("+12조각", "플러스 열두-조각", "integer", ["+12"]),
    ("2만3천", "이만삼천", "structured_integer", ["2만3천"]),
    ("25.50억", "이십오-쩜-오영-억", "decimal", ["25.50"]),
    ("1:2:3", "일 대 이 대 삼", "ratio", ["1", "2", "3"]),
    ("1：2：3", "일 대 이 대 삼", "ratio", ["1", "2", "3"]),
])
def test_owner_metadata_gaps_are_recorded_without_marker_scope_expansion(source, expected, form, raws):
    output = transform_output(source)
    assert output.normalized_text == expected
    annotation = output.numeric_annotations[0]
    plan = annotation.plan
    assert annotation.alignment == "exact"
    assert plan.numeric_form == form
    assert [component.raw for component in plan.components] == raws
    assert plan.marker_status == "owner_scope_unresolved"
    assert plan.analysis_status == "owner_linguistic_unit_unresolved"
    assert all(v.target == "unresolved" for c in plan.components for v in c.vowels)
    assert all(c.source_span and source[c.source_span.start:c.source_span.end] == c.raw for c in plan.components)
    if source.startswith("+"):
        assert plan.components[0].numeral_system == "native"
        assert plan.semantic_kind == "count"
        assert plan.unit == "조각"
    if form == "decimal":
        assert plan.components[0].fractional_part == "50"


def test_explicit_insertions_at_numeric_annotation_edges_have_correct_affinity():
    output = transform_output("20kg")
    annotation = output.numeric_annotations[0]
    span = annotation.output_span
    edits = ((span.start, span.start, "앞말 ", None), (span.end, span.end, ",", None))
    updated = project_annotations((annotation,), edits)[0]
    assert updated.output_span == SourceSpan(span.start + 3, span.end + 3)
    final = "앞말 " + output.normalized_text + ","
    assert final[updated.output_span.start:updated.output_span.end] == annotation.plan.text


def test_repeated_numbers_exact_offsets_and_no_guessed_final_alignment():
    source = '2개와 22개, 2개를 옮겼다.'
    output = transform_output(source)
    annotations = output.numeric_annotations
    assert len(annotations) == 3
    assert [a.plan.source_span.start for a in annotations] == [0,4,9]
    for a in annotations:
        assert a.alignment == 'exact'
        assert output.normalized_text[a.output_span.start:a.output_span.end] == a.plan.text
    changed = replace(output, normalized_text='변경 ' + output.normalized_text)
    assert all(a.output_span is None and a.alignment == 'final_coordinates_unresolved' for a in changed.numeric_annotations)


def test_contextual_decision_and_public_serialization():
    deferred = transform_output('3번').numeric_annotations[0].plan
    confirmed = transform_output('3번 처리했다.').numeric_annotations[0].plan
    assert deferred.decision is ContextualDecisionKind.DEFERRED
    assert deferred.components == ()
    assert confirmed.decision is ContextualDecisionKind.CONFIRMED
    assert confirmed.components[0].numeral_system == 'native'
    assert confirmed.components[0].vowels[0].target == 'long'
    assert set(ContextualDecisionKind) == {ContextualDecisionKind.CONFIRMED, ContextualDecisionKind.DEFERRED,
        ContextualDecisionKind.ABSOLUTE_PRESERVE, ContextualDecisionKind.NOT_APPLICABLE}
    serialized = json.dumps([render_piece_to_dict(p) for p in transform_output('2개').render_pieces])
    assert 'numeric_plan' not in serialized and 'lexical_length' not in serialized


def test_assets_in_every_binary_and_native_special_form():
    root = Path(__file__).resolve().parents[2]
    for name in ['tts_preprocessor.spec','tts_preprocessor_simplified.spec',
                 'tts_preprocessor_standard_llm.spec','tts_preprocessor_natural_llm.spec']:
        spec = (root / name).read_text()
        assert '"numeric_vowels.json"' in spec and '"engine/span_engine/data"' in spec
    assert vowel_data()['entries']['sino:이']['lexeme_id'] == 'krdict:71125'
    component = number_component('3', system='native', native_reading='석')
    assert component.groups == (('석',),) and component.vowels[0].target == 'unresolved'
