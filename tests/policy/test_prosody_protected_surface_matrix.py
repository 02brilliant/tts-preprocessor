import pytest

from engine.main import transform
from tests._policy_case import TextCase, assert_exact
from tests._span_prosody import apply_span_prosody


PROTECTED_SURFACE_NO_COMMA_CASES = [
    TextCase(
        case_id="prosody-protected-acronym-particle",
        text="에프티에이는 유지된다",
        expected="에프티에이는 유지된다",
        rule="prosody / protected surface negative",
        reason="A protected acronym output with a following particle must not be internally segmented by prosody.",
        classification="prosody",
    ),
    TextCase(
        case_id="prosody-protected-acronym-sequence",
        text="에프티에이와 엠에프엔은 동시에 검토한다",
        expected="에프티에이와 엠에프엔은 동시에 검토한다",
        rule="prosody / protected surface negative",
        reason="Adjacent protected acronym outputs must not trigger midpoint-style comma insertion.",
        classification="prosody",
    ),
    TextCase(
        case_id="prosody-protected-lexical-middle-dot-sequence",
        text="에이아이 반도체와 코스피 에이아이는 다르다",
        expected="에이아이 반도체와 코스피 에이아이는 다르다",
        rule="prosody / protected surface negative",
        reason="Lexical middle-dot outputs must remain intact as protected surfaces in prosody.",
        classification="prosody",
    ),
    TextCase(
        case_id="prosody-protected-single-letter-hyphen-sequence",
        text="케이-푸드와 씨-레벨은 동시에 검토한다",
        expected="케이-푸드와 씨-레벨은 동시에 검토한다",
        rule="prosody / protected surface negative",
        reason="Single-letter hyphen lexical outputs must remain intact as protected surfaces in prosody.",
        classification="prosody",
    ),
    TextCase(
        case_id="prosody-protected-large-unit-particle",
        text="육천사백이억을 이미 반영했다",
        expected="육천사백이억을 이미 반영했다",
        rule="prosody / protected surface negative",
        reason="Atomic large-unit outputs with particles must not be split by prosody.",
        classification="prosody",
    ),
    TextCase(
        case_id="prosody-protected-signed-degree-sequence",
        text="마이너스 일쩜삼도와 마이너스 영쩜오도를 비교한다",
        expected="마이너스 일쩜삼도와 마이너스 영쩜오도를 비교한다",
        rule="prosody / protected surface negative",
        reason="Signed degree outputs must remain intact as protected surfaces in prosody.",
        classification="prosody",
    ),
]


FULL_PIPELINE_PROTECTED_SURFACE_CASES = [
    TextCase(
        case_id="full-pipeline-protected-acronym-topic",
        text="그리고 FTA는 유지된다",
        expected="그리고, 에프티에이는 유지된다",
        rule="prosody / leading connector + protected acronym",
        reason="Prosody may add only the leading connector comma while preserving the protected acronym output.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-acronym-subject",
        text="그리고 AI가 핵심이다",
        expected="그리고, 에이아이가 핵심이다",
        rule="prosody / leading connector + protected acronym",
        reason="Prosody may add only the leading connector comma while preserving the protected acronym output.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-acronym-mfn",
        text="그리고 MFN은 예외다",
        expected="그리고, 엠에프엔은 예외다",
        rule="prosody / leading connector + protected acronym",
        reason="Prosody may add only the leading connector comma while preserving the protected acronym output.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-lexical-middle-dot-korean",
        text="그리고 AI·반도체 전략을 논의한다",
        expected="그리고, 에이아이·반도체 전략을 논의한다",
        rule="prosody / leading connector + lexical middle dot",
        reason="Prosody may add only the leading connector comma while preserving the lexical middle-dot protected output.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-lexical-middle-dot-acronym",
        text="그리고 ISO·IEC 표준을 검토한다",
        expected="그리고, 아이에스오·아이이씨 표준을 검토한다",
        rule="prosody / leading connector + lexical middle dot",
        reason="Prosody may add only the leading connector comma while preserving the lexical middle-dot protected output.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-lexical-middle-dot-dictionary",
        text="그리고 KOSPI·AI 지표를 본다",
        expected="그리고, 코스피·에이아이 지표를 본다",
        rule="prosody / leading connector + lexical middle dot",
        reason="Prosody may add only the leading connector comma while preserving the lexical middle-dot protected output.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-single-letter-hyphen-primary",
        text="그리고 K-푸드와 K-뷰티를 육성한다",
        expected="그리고, 케이푸드와 케이뷰티를 육성한다",
        rule="prosody / leading connector + single-letter hyphen lexical compound",
        reason="Prosody may add only the leading connector comma while preserving managed K-Hangul lexical outputs.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-single-letter-hyphen-generalized",
        text="그리고 B-플랜과 C-레벨을 점검한다",
        expected="그리고, B-플랜과 C-레벨을 점검한다",
        rule="prosody / leading connector + single-letter hyphen lexical compound",
        reason="Prosody may add only the leading connector comma while preserving unsupported generalized letter-Hangul surfaces.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-large-unit-particle",
        text="그리고 6402억을 투입한다",
        expected="그리고, 육천사백이억을 투입한다",
        rule="prosody / leading connector + large-unit atomic parse",
        reason="Prosody may add only the leading connector comma while preserving atomic large-unit outputs with particles.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-large-unit-subject",
        text="그리고 1조가 넘는다",
        expected="그리고, 1조가 넘는다",
        rule="prosody / leading connector + contextual number-unit defer",
        reason="Prosody may add only the leading connector comma while the ambiguous 조 surface remains source-exact.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-large-unit-topic",
        text="그리고 100억은 이미 반영됐다",
        expected="그리고, 백억은 이미 반영됐다",
        rule="prosody / leading connector + large-unit atomic parse",
        reason="Prosody may add only the leading connector comma while preserving atomic large-unit outputs with particles.",
        classification="prosody",
    ),
    TextCase(
        case_id="full-pipeline-protected-signed-degree-sequence",
        text="그리고 -1.3도와 -0.5도 기록을 비교한다",
        expected="그리고, 마이너스 일쩜삼도와 마이너스 영쩜오도 기록을 비교한다",
        rule="prosody / leading connector + signed degree quantity",
        reason="Prosody may add only the leading connector comma while preserving signed-degree protected outputs.",
        classification="prosody",
    ),
]


@pytest.mark.parametrize("case", PROTECTED_SURFACE_NO_COMMA_CASES, ids=lambda case: case.case_id)
def test_prosody_direct_protected_surface_no_comma(case: TextCase):
    assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize("case", FULL_PIPELINE_PROTECTED_SURFACE_CASES, ids=lambda case: case.case_id)
def test_full_pipeline_protected_surface_connector_cases(case: TextCase):
    assert_exact(transform(case.text), case)
