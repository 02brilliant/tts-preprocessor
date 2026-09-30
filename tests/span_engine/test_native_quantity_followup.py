import pytest

from engine.main import transform, transform_output, transform_simplified
from engine.span_engine.models import SourceSpan


QUANTITY_UNITS = ("개", "명", "마리", "그루", "송이", "자루", "벌", "켤레")
READINGS = {
    1: "한", 20: "스무", 39: "서른아홉", 40: "마흔", 41: "마흔한",
    50: "쉰", 99: "아흔아홉", 100: "백", 101: "백일",
}


@pytest.mark.parametrize("unit", QUANTITY_UNITS)
@pytest.mark.parametrize("number,reading", READINGS.items())
def test_exact_quantity_policy_and_plan(unit, number, reading):
    source = f"{number}{unit}"
    output = transform_output(source)
    assert output.normalized_text == f"{reading}-{unit}"
    annotation = output.numeric_annotations[0]
    component = annotation.plan.components[0]
    assert annotation.plan.semantic_kind == "count"
    assert component.raw == str(number)
    assert component.numeral_system == ("native" if number < 100 else "sino")
    assert "".join(component.groups[0]) == reading
    assert annotation.plan.source_span == SourceSpan(0, len(str(number)))
    assert annotation.plan.unit_source_span == SourceSpan(len(str(number)), len(source))
    assert annotation.alignment == "exact"


@pytest.mark.parametrize("unit", QUANTITY_UNITS)
def test_range_reuses_exact_quantity_policy_and_unit_provenance(unit):
    source = f"39~40{unit}은 40~50{unit}보다 적다."
    output = transform_output(source)
    assert output.normalized_text == (
        f"서른아홉-{unit}에서 마흔-{unit}은 마흔-{unit}에서 쉰-{unit}보다 적다."
    )
    annotations = [a for a in output.numeric_annotations if a.plan.numeric_form == "range"]
    assert len(annotations) == 2
    assert [tuple(c.numeral_system for c in a.plan.components) for a in annotations] == [
        ("native", "native"), ("native", "native")
    ]
    copies = [p for p in output.render_pieces if p.metadata.get("generated_unit_copy")]
    assert len(copies) == 2
    assert all(p.text == unit and p.provenance == "GENERATED_READING" for p in copies)
    assert all(a.alignment == "exact" for a in annotations)
    assert not output.trace.fallback_logs
    assert all(log.passed for log in output.trace.validation_logs)


@pytest.mark.parametrize("unit", QUANTITY_UNITS)
def test_range_delimiters_spacing_and_reversed_order(unit):
    assert transform(f"2~5{unit}") == f"두-{unit}에서 다섯-{unit}"
    assert transform(f"2-5{unit}") == f"두-{unit}에서 다섯-{unit}"
    assert transform(f"2∼5{unit}") == f"두-{unit}에서 다섯-{unit}"
    assert transform(f"2～5{unit}") == f"두-{unit}에서 다섯-{unit}"
    assert transform(f"2~ 5 {unit}을") == f"두-{unit}에서 다섯-{unit}을"
    assert transform(f"5~2{unit}") == f"다섯-{unit}에서 두-{unit}"
    assert transform(f"2 - 5{unit}") == f"2 - 5{unit}"


@pytest.mark.parametrize("source,expected", [
    ("0명", "영-명"), ("040명", "040명"), ("40.5명", "사십-쩜-오-명"),
    ("-40명", "마이너스 사십 명"), ("+40명", "플러스 사십 명"),
    ("40/2명", "이분의 사십 명"), ("4,,0명", "4,,0명"),
    ("02~5마리", "02~5마리"), ("2~05마리", "2~05마리"),
    ("2~5.5마리", "이에서 오-쩜-오 마리"),
    ("-2~5마리", "마이너스 이에서 오 마리"),
    ("2~5마리수", "이에서 오 마리수"),
    ("2~5그루터기", "이에서 오 그루터기"),
    ("2~5송이버섯", "이에서 오 송이버섯"),
    ("2~5벌레", "이에서 오 벌레"),
    ("2~5마리_foo", "이에서 오 마리_foo"),
    ("https://example.com/2~5마리", "https://example.com/2~5마리"),
    ("`2~5마리`", "`2~5마리`"),
    ("[2~5마리]", "[2~5마리]"),
])
def test_no_new_native_reading_or_partial_quantity_range(source, expected):
    output = transform_output(source)
    assert output.normalized_text == expected
    assert not any(a.plan.semantic_kind == "count" and a.plan.numeric_form == "range"
                   for a in output.numeric_annotations)


@pytest.mark.parametrize("source,expected", [
    ("40권", "사십-권"), ("40장", "사십-장"), ("40척", "사십-척"),
    ("40대", "사십-대"), ("40번 처리했다.", "사십-번 처리했다."),
    ("40시간", "사십-시간"), ("40사람", "마흔-사람"),
    ("40살", "마흔-살"), ("40가지", "마흔-가지"),
    ("100명", "백-명"), ("101명", "백일-명"),
    ("2~5%", "이에서 오-퍼센트"), ("2~5kg", "이에서 오-킬로그램"),
    ("2~5분", "이분에서 오분"), ("2~5가지", "두-가지에서 다섯-가지"),
    ("010-1234-5678", "공일공 일이삼사 오육칠팔"),
    ("3/4만큼", "사분의 삼만큼"),
])
def test_unrelated_counter_and_owner_policy(source, expected):
    assert transform(source) == expected


@pytest.mark.parametrize("source,expected", [
    ("3,456", "삼천사백오십육"),
    ("123,456", "십이만 삼천사백오십육"),
    ("52,025", "오만 이천이십오"),
    ("123,456원", "십이만 삼천사백오십육-원"),
    ("123,456kg", "십이만 삼천사백오십육-킬로그램"),
    ("1.23456", "일-쩜-이삼사-오육"),
    ("1.23456789", "일-쩜-이삼사오-육칠팔구"),
    ("2.05%", "이-쩜-영오-퍼센트"),
    ("2.50kg", "이-쩜-오영-킬로그램"),
])
def test_integer_boundary_change_leaves_other_boundaries(source, expected):
    output = transform_output(source)
    assert output.normalized_text == expected
    if source == "123,456":
        plan = output.numeric_annotations[0].plan
        assert [(b.kind, b.text) for b in plan.boundaries if b.origin == "generated"] == [
            ("numeric_internal", " ")
        ]
    if source == "2.50kg":
        assert output.numeric_annotations[0].plan.components[0].fractional_part == "50"


def test_lexical_vowels_do_not_follow_removed_integer_hyphen():
    output = transform_output("123,456와 40명, 40번 처리했다.")
    cardinal, quantity, contextual = [a.plan for a in output.numeric_annotations]
    assert cardinal.text == "십이만 삼천사백오십육"
    assert all(b.text != "-" for b in cardinal.boundaries if b.origin == "generated")
    assert [(v.lexeme, v.target) for v in cardinal.components[0].vowels if v.lexeme in {"사", "오"}] == [
        ("사", "short"), ("오", "short")
    ]
    assert quantity.components[0].numeral_system == "native"
    assert quantity.components[0].groups == (("마흔",),)
    assert quantity.components[0].vowels[0].target == "unresolved"
    assert contextual.components[0].numeral_system == "sino"
    assert all(a.alignment == "exact" for a in output.numeric_annotations)
    assert transform_simplified("40명과 2~5마리") == transform("40명과 2~5마리")
