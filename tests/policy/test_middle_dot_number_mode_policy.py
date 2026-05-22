import pytest

from engine.main import transform
from engine.pipeline.transform_engine import transform_text
from tests._policy_case import TextCase, assert_exact


NORMALIZATION_INTERACTION_CASES = [
    TextCase(
        case_id="interaction-bare-middle-dot-versus-dictionary-event",
        text="5·18과 5·18 민주화운동",
        expected="오 일팔과 오일팔 민주화운동",
        rule="middle dot + dictionary / interaction",
        reason="A bare middle-dot token must use structured parsing, while the fixed dictionary event phrase keeps its protected reading.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-dot-event-versus-middle-dot-structured",
        text="12.12 사태와 7·25를 비교한다",
        expected="십이십이 사태와 칠 이오를 비교한다",
        rule="event dot + middle dot / interaction",
        reason="Dot-event parsing and middle-dot structured parsing must coexist without becoming interchangeable.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-middle-dot-versus-dot-decimal",
        text="7·25와 7.25는 다르다",
        expected="칠 이오와 칠쩜이오는 다르다",
        rule="middle dot vs decimal / interaction",
        reason="Structured middle-dot output and decimal output must remain distinct inside the same sentence.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-spaced-middle-dot-versus-contiguous-middle-dot",
        text="123 · 456과 123·456은 다르다",
        expected="백이십삼 · 사백오십육과 일이삼 사오육은 다르다",
        rule="middle dot spacing / interaction",
        reason="Spaced and contiguous middle-dot patterns must normalize differently in the same sentence.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="interaction-leading-zero-bare-date-unit-counter",
        text="007 01월 03kg 01명",
        expected="공공칠 일월 삼 킬로그램 한 명",
        rule="digit mode + overrides / interaction",
        reason="A bare leading-zero token uses Digit Mode, while date, unit, and counter contexts override it in the same sequence.",
        classification="override",
    ),
    TextCase(
        case_id="interaction-leading-zero-bare-time-override",
        text="01 09시 07시 05분",
        expected="공일 아홉시 일곱시 오분",
        rule="digit mode + time override / interaction",
        reason="Bare leading-zero tokens use Digit Mode, but explicit time expressions keep time readings.",
        classification="override",
    ),
    TextCase(
        case_id="interaction-identifier-digit-mode-plus-date",
        text="ID: 00123 기록은 2025.01.03에 갱신한다",
        expected="아이디 공공일이삼 기록은 이천이십오년 일월 삼일에 갱신한다",
        rule="identifier + date / interaction",
        reason="Identifier Digit Mode and dotted date parsing must both apply exactly without leaking punctuation or number-mode conflicts.",
        classification="digit_mode",
    ),
    TextCase(
        case_id="interaction-phone-digit-mode-plus-counter-override",
        text="010-1234-5678 01명",
        expected="공일공 일이삼사 오육칠팔 한 명",
        rule="phone + counter override / interaction",
        reason="Phone-style digit blocks and counter-noun overrides must normalize independently inside one input.",
        classification="digit_mode",
    ),
    TextCase(
        case_id="interaction-middle-dot-and-leading-zero-blocks",
        text="01·09와 0001",
        expected="공일 공구와 공공공일",
        rule="middle dot + digit mode / interaction",
        reason="Structured middle-dot blocks and bare leading-zero tokens both rely on Digit Mode but must preserve their different surface structures.",
        classification="digit_mode",
    ),
    TextCase(
        case_id="interaction-middle-dot-with-date-and-decimal",
        text="2025.01.03 7·25 7.25",
        expected="이천이십오년 일월 삼일 칠 이오 칠쩜이오",
        rule="date + middle dot + decimal / interaction",
        reason="Date, structured middle-dot, and decimal parsing must resolve in strict precedence order inside one line.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-middle-dot-time-tail-guard",
        text="01·09시와 09시",
        expected="01·09시와 아홉시",
        rule="mixed guard + time override / interaction",
        reason="An attached time suffix on a middle-dot token must not trigger partial parsing, while a valid time token still normalizes.",
        classification="conflict",
    ),
    TextCase(
        case_id="interaction-middle-dot-unit-tail-guard",
        text="12·003kg와 03kg",
        expected="12·003kg와 삼 킬로그램",
        rule="mixed guard + unit override / interaction",
        reason="An attached unit suffix on a middle-dot token must not partially normalize, while a valid unit token still normalizes.",
        classification="conflict",
    ),
]


FULL_PIPELINE_INTERACTION_CASES = [
    TextCase(
        case_id="full-pipeline-connector-middle-dot-counter",
        text="그리고 7·25 자료는 01명에게 배포한다",
        expected="그리고, 칠 이오 자료는 한 명에게 배포한다",
        rule="connector + middle dot + counter / full pipeline",
        reason="Prosody may add only the connector comma while structured middle-dot reading and counter override remain intact.",
        classification="override",
    ),
    TextCase(
        case_id="full-pipeline-connector-identifier-date",
        text="그리고 ID: 00123 기록은 2025.01.03에 갱신한다",
        expected="그리고, 아이디 공공일이삼 기록은 이천이십오년 일월 삼일에 갱신한다",
        rule="connector + identifier + date / full pipeline",
        reason="Prosody must not break the identifier Digit Mode result or the dotted date reading.",
        classification="digit_mode",
    ),
    TextCase(
        case_id="full-pipeline-connector-middle-dot-vs-decimal",
        text="그리고 7·25와 7.25 수치를 비교한다",
        expected="그리고, 칠 이오와 칠쩜이오 수치를 비교한다",
        rule="connector + middle dot + decimal / full pipeline",
        reason="Prosody may add a connector comma, but the middle-dot and decimal readings must remain distinct.",
        classification="conflict",
    ),
    TextCase(
        case_id="full-pipeline-connector-spaced-and-contiguous-middle-dot",
        text="그리고 123 · 456 표기는 123·456과 다르다",
        expected="그리고, 백이십삼 · 사백오십육 표기는 일이삼 사오육과 다르다",
        rule="connector + middle dot spacing / full pipeline",
        reason="Prosody must not collapse the preserved spaced middle dot or the contiguous structured result.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="full-pipeline-connector-phone-currency-time",
        text="그리고 연락처는 010-1234-5678이고 비용은 ₩01,000이며 시작은 09시다",
        expected="그리고, 연락처는 공일공 일이삼사 오육칠팔이고 비용은 천 원이며 시작은 아홉시다",
        rule="connector + phone + currency + time / full pipeline",
        reason="Digit-mode phone blocks, currency override, and time override must survive the full pipeline together.",
        classification="override",
    ),
    TextCase(
        case_id="full-pipeline-connector-bare-middle-dot-versus-event-phrase",
        text="그리고 5·18과 12.12 사태 자료를 함께 본다",
        expected="그리고, 오 일팔과 십이십이 사태 자료를 함께 본다",
        rule="connector + middle dot conflict + event / full pipeline",
        reason="A bare middle-dot token must not become an event phrase, while the dotted event phrase stays protected through prosody.",
        classification="conflict",
    ),
]


@pytest.mark.parametrize("case", NORMALIZATION_INTERACTION_CASES, ids=lambda case: case.case_id)
def test_middle_dot_and_number_mode_normalization_interactions(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", FULL_PIPELINE_INTERACTION_CASES, ids=lambda case: case.case_id)
def test_middle_dot_and_number_mode_full_pipeline_interactions(case: TextCase):
    assert_exact(transform(case.text), case)
