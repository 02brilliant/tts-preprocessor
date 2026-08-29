import pytest

from engine.main import transform
from engine.main import transform
from tests._policy_case import TextCase, assert_exact


NORMALIZATION_INTERACTION_CASES = [
    TextCase(
        case_id="interaction-bare-middle-dot-versus-dictionary-event",
        text="5·18과 5·18 민주화운동",
        expected="오·일팔과 오일팔 민주화운동",
        rule="middle dot + dictionary / interaction",
        reason="A bare middle-dot token must use structured parsing, while the fixed dictionary event phrase keeps its protected reading.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-dot-event-versus-middle-dot-structured",
        text="12.12 사태와 7·25를 비교한다",
        expected="십이십이 사태와 칠·이오를 비교한다",
        rule="event dot + middle dot / interaction",
        reason="Dot-event parsing and middle-dot structured parsing must coexist without becoming interchangeable.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-middle-dot-versus-dot-decimal",
        text="7·25와 7.25는 다르다",
        expected="칠·이오와 칠쩜이오는 다르다",
        rule="middle dot vs decimal / interaction",
        reason="Structured middle-dot output and decimal output must remain distinct inside the same sentence.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-spaced-middle-dot-versus-contiguous-middle-dot",
        text="123 · 456과 123·456은 다르다",
        expected="백이십삼 · 사백오십육과 일이삼·사오육은 다르다",
        rule="middle dot spacing / interaction",
        reason="Spaced and contiguous middle-dot patterns must normalize differently in the same sentence.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="interaction-leading-zero-preserve-date-unit-counter",
        text="007 01월 03kg 01명",
        expected="007 일월 03kg 01명",
        rule="leading-zero preserve + date owner / interaction",
        reason="The date month owner transforms 01월 while the bare, invalid unit-amount, and counter surfaces preserve independently.",
        classification="preserve",
    ),
    TextCase(
        case_id="interaction-leading-zero-standalone-and-time-override",
        text="01 09시 07시 05분",
        expected="01 아홉-시 일곱-시 오분",
        rule="leading-zero standalone preserve + suffix time override / interaction",
        reason="The bare number preserves, while registered 시/분 suffix owners normalize their own leading-zero numeric cores.",
        classification="override",
    ),
    TextCase(
        case_id="interaction-identifier-payload-preserve-plus-date",
        text="ID: 00123 기록은 2025.01.03에 갱신한다",
        expected="아이디: 00123 기록은 이천이십오년 일월 삼일에 갱신한다",
        rule="identifier payload preserve + date / interaction",
        reason="The acronym and dotted date owners transform independently while the colon and leading-zero identifier payload preserve.",
        classification="preserve",
    ),
    TextCase(
        case_id="interaction-phone-reading-plus-leading-zero-counter-preserve",
        text="010-1234-5678 01명",
        expected="공일공 일이삼사 오육칠팔 01명",
        rule="phone owner + leading-zero counter preserve / interaction",
        reason="The phone owner reads its hyphen blocks while the adjacent leading-zero counter surface preserves independently.",
        classification="preserve",
    ),
    TextCase(
        case_id="canonical-middle-dot-leading-zero-and-standalone-preserve",
        text="01·09와 0001",
        expected="영일·영구와 0001",
        rule="middle dot block reading + standalone leading-zero preserve",
        reason="The short first block uses numeric value reading, the later block reads every digit with 영 for zero, and the independent standalone leading-zero token preserves.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="interaction-middle-dot-with-date-and-decimal",
        text="2025.01.03 7·25 7.25",
        expected="이천이십오년 일월 삼일 칠·이오 칠쩜이오",
        rule="date + middle dot + decimal / interaction",
        reason="Date, structured middle-dot, and decimal parsing must resolve in strict precedence order inside one line.",
        classification="conflict",
    ),
    TextCase(
        case_id="canonical-middle-dot-leading-zero-time-override",
        text="01·09시와 09시",
        expected="01·09시와 아홉-시",
        rule="middle dot guard + leading-zero suffix-clock override",
        reason="The mixed middle-dot token stays protected, while the independent suffix clock is normalized by the time owner.",
        classification="override",
    ),
    TextCase(
        case_id="canonical-middle-dot-leading-zero-unit-preserve",
        text="12·003kg와 03kg",
        expected="12·003kg와 03kg",
        rule="middle dot guard + invalid leading-zero unit preserve",
        reason="The unit contamination preserve owner blocks both invalid leading-zero unit amounts and prevents a partial middle-dot reading.",
        classification="preserve",
    ),
]


FULL_PIPELINE_INTERACTION_CASES = [
    TextCase(
        case_id="full-pipeline-connector-middle-dot-counter",
        text="그리고 7·25 자료는 01명에게 배포한다",
        expected="그리고, 칠·이오 자료는 01명에게 배포한다",
        rule="connector + middle dot + counter / full pipeline",
        reason="Prosody may add only the connector comma while structured middle-dot reading and leading-zero counter preservation remain intact.",
        classification="override",
    ),
    TextCase(
        case_id="full-pipeline-connector-identifier-date",
        text="그리고 ID: 00123 기록은 2025.01.03에 갱신한다",
        expected="그리고, 아이디: 00123 기록은 이천이십오년 일월 삼일에 갱신한다",
        rule="connector + identifier + date / full pipeline",
        reason="Prosody must preserve the identifier-like payload while retaining the dotted date reading.",
        classification="digit_mode",
    ),
    TextCase(
        case_id="full-pipeline-connector-middle-dot-vs-decimal",
        text="그리고 7·25와 7.25 수치를 비교한다",
        expected="그리고, 칠·이오와 칠쩜이오 수치를 비교한다",
        rule="connector + middle dot + decimal / full pipeline",
        reason="Prosody may add a connector comma, but the middle-dot and decimal readings must remain distinct.",
        classification="conflict",
    ),
    TextCase(
        case_id="full-pipeline-connector-spaced-and-contiguous-middle-dot",
        text="그리고 123 · 456 표기는 123·456과 다르다",
        expected="그리고, 백이십삼 · 사백오십육-표기는 일이삼·사오육과 다르다",
        rule="connector + middle dot spacing / full pipeline",
        reason="Prosody must not collapse the preserved spaced middle dot or the contiguous structured result.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="full-pipeline-connector-phone-currency-time",
        text="그리고 연락처는 010-1234-5678이고 비용은 ₩01,000이며 시작은 09시다",
        expected="그리고, 연락처는 공일공 일이삼사 오육칠팔이고 비용은 ₩01,000이며 시작은 아홉-시다",
        rule="connector + phone + currency + time / full pipeline",
        reason="Phone and suffix-clock owners normalize independently while the leading-zero currency surface remains preserved.",
        classification="override",
    ),
    TextCase(
        case_id="full-pipeline-connector-bare-middle-dot-versus-event-phrase",
        text="그리고 5·18과 12.12 사태 자료를 함께 본다",
        expected="그리고, 오·일팔과 십이십이 사태 자료를 함께 본다",
        rule="connector + middle dot conflict + event / full pipeline",
        reason="A bare middle-dot token must not become an event phrase, while the dotted event phrase stays protected through prosody.",
        classification="conflict",
    ),
]


@pytest.mark.parametrize("case", NORMALIZATION_INTERACTION_CASES, ids=lambda case: case.case_id)
def test_middle_dot_and_number_mode_normalization_interactions(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", FULL_PIPELINE_INTERACTION_CASES, ids=lambda case: case.case_id)
def test_middle_dot_and_number_mode_full_pipeline_interactions(case: TextCase):
    assert_exact(transform(case.text), case)
