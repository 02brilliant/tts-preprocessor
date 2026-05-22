import pytest

from engine.main import transform
from engine.prosody.comma import insert_commas
from engine.pipeline.transform_engine import transform_text
from tests._policy_case import TextCase, assert_exact


REGRESSION_CASES = [
    # Known failure pattern: event phrases were previously split or misread as decimals.
    TextCase(
        case_id="regression-event-splitting-1212-satae",
        text="그리고 12.12 사태 자료를 검토한다",
        expected="그리고, 십이십이 사태 자료를 검토한다",
        rule="regression / event splitting",
        reason="The event phrase must stay intact; only the sentence-initial connector may receive a comma.",
        classification="conflict",
    ),
    TextCase(
        case_id="regression-event-splitting-518",
        text="그리고 5·18 민주화 운동 자료를 검토한다",
        expected="그리고, 오일팔 민주화 운동 자료를 검토한다",
        rule="regression / event splitting",
        reason="A middle-dot event phrase must remain a protected phrase all the way through the full pipeline.",
        classification="conflict",
    ),
    # Known failure pattern: emergency numbers were left unconverted even in explicit context.
    TextCase(
        case_id="regression-emergency-112-context",
        text="긴급번호 112는 경찰 신고 번호다",
        expected="긴급번호 일일이는 경찰 신고 번호다",
        rule="regression / emergency number",
        reason="An explicit emergency context must force the emergency-number reading for 112.",
        classification="override",
    ),
    TextCase(
        case_id="regression-emergency-119-context",
        text="화재가 나면 119에 신고하세요",
        expected="화재가 나면 일일구에 신고하세요",
        rule="regression / emergency number",
        reason="An explicit emergency context plus allowed particle tail must force the emergency-number reading for 119.",
        classification="override",
    ),
    # Known failure pattern: comma-decimal currency parsing broke in atomic forms.
    TextCase(
        case_id="regression-currency-eur-comma-decimal",
        text="€1,234.56",
        expected="천이백삼십사쩜오육 유로",
        rule="regression / atomic currency parse",
        reason="The full EUR comma-decimal span must normalize atomically instead of partially consuming only the number or code.",
        classification="override",
    ),
    # Known failure pattern: time readings were inconsistent between independent and HH:MM forms.
    TextCase(
        case_id="regression-independent-time-afternoon",
        text="오후 2시 출발",
        expected="오후 두시 출발",
        rule="regression / independent time",
        reason="An independent H시 form with 오후 must always normalize as time using the native hour reading.",
        classification="override",
    ),
    TextCase(
        case_id="regression-hhmm-positive-context",
        text="회의는 12:30에 시작한다",
        expected="회의는 열두시 삼십분에 시작한다",
        rule="regression / HH:MM positive context",
        reason="A positively licensed HH:MM form must normalize consistently with the independent H시 rules.",
        classification="override",
    ),
    # Known failure pattern: middle dots were treated like decimals or event markers.
    TextCase(
        case_id="regression-single-middle-dot-structured",
        text="7·25",
        expected="칠 이오",
        rule="regression / middle dot structured",
        reason="A single middle dot now follows the structured parser and must not collapse into decimal reading.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="regression-three-block-middle-dot-structured",
        text="1·2·3",
        expected="일 이 삼",
        rule="regression / middle dot structured",
        reason="A three-block middle-dot form must keep block boundaries without reading the middle dots as points.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="regression-bare-five-eighteen-not-event",
        text="5·18",
        expected="오 일팔",
        rule="regression / middle dot conflict",
        reason="A bare 5·18 form is no longer an event-number parse and must normalize through the structured middle-dot rule.",
        classification="conflict",
    ),
    TextCase(
        case_id="regression-spaced-middle-dot-preserves-symbol",
        text="123 · 456",
        expected="백이십삼 · 사백오십육",
        rule="regression / middle dot spacing guard",
        reason="Whitespace around the middle dot disables structured parsing and preserves the symbol.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="regression-leading-zero-digit-mode",
        text="0001",
        expected="공공공일",
        rule="regression / digit mode",
        reason="A bare leading-zero token must use Digit Mode instead of Number Mode.",
        classification="digit_mode",
    ),
    TextCase(
        case_id="regression-leading-zero-date-override",
        text="01월",
        expected="일월",
        rule="regression / override",
        reason="A date token must override the leading-zero Digit Mode trigger.",
        classification="override",
    ),
    TextCase(
        case_id="regression-leading-zero-time-override",
        text="09시",
        expected="아홉시",
        rule="regression / override",
        reason="A time token must override the leading-zero Digit Mode trigger.",
        classification="override",
    ),
    TextCase(
        case_id="regression-leading-zero-counter-override",
        text="01명",
        expected="한 명",
        rule="regression / override",
        reason="A counter-noun token must override the leading-zero Digit Mode trigger.",
        classification="override",
    ),
    # Known failure pattern: partial matches were leaking through instead of fully skipping.
    TextCase(
        case_id="regression-ph-partial-match-guard",
        text="pH 7.4a",
        expected="pH 7.4a",
        rule="regression / partial-match guard",
        reason="Invalid trailing tails on pH expressions must skip the full pattern with no partial rewrite.",
        classification="conflict",
    ),
    TextCase(
        case_id="regression-frequency-partial-match-guard",
        text="5Hzabc",
        expected="5Hzabc",
        rule="regression / partial-match guard",
        reason="Frequency parsing must reject alphabetic tails without converting the valid-looking prefix.",
        classification="conflict",
    ),
    # Known failure pattern: numeric-heavy sentences attracted too many commas.
    TextCase(
        case_id="regression-prosody-comma-explosion",
        text="이천이십육년 사월 십칠일 십삼시 오분 백 원 삼 킬로그램 자료",
        expected="이천이십육년 사월 십칠일 십삼시 오분 백 원 삼 킬로그램 자료",
        rule="regression / comma explosion",
        reason="Numeric-heavy sequences should suppress extra commas rather than adding pauses inside dense protected material.",
        classification="conflict",
    ),
    # Known failure pattern: protected phrases were broken by commas.
    TextCase(
        case_id="regression-protected-emergency-phrase-not-broken",
        text="그리고 긴급번호 112는 경찰 신고 번호다",
        expected="그리고, 긴급번호 일일이는 경찰 신고 번호다",
        rule="regression / protected phrase comma guard",
        reason="The connector comma may appear, but the normalized emergency phrase must remain intact.",
        classification="conflict",
    ),
    # Known failure pattern: false-positive unit parsing on invalid slash tails.
    TextCase(
        case_id="regression-unit-invalid-tail-kml",
        text="15.2km/La",
        expected="15.2km/La",
        rule="regression / invalid unit tail",
        reason="A trailing alphabetic tail after a compound unit must block the full parse.",
        classification="conflict",
    ),
    TextCase(
        case_id="regression-unit-invalid-tail-kmspeed",
        text="3km/speed",
        expected="3km/speed",
        rule="regression / invalid unit tail",
        reason="An unsupported slash compound must remain untouched rather than partially normalizing the supported-looking prefix.",
        classification="conflict",
    ),
]


@pytest.mark.parametrize("case", REGRESSION_CASES, ids=lambda case: case.case_id)
def test_known_policy_regressions(case: TextCase):
    # Route each regression through the layer that previously failed in production or earlier outputs.
    if "comma explosion" in case.rule:
        actual = insert_commas(case.text)
    elif "connector" in case.text or "자료를 검토한다" in case.text or "긴급번호 112는" in case.text and case.text.startswith("그리고"):
        actual = transform(case.text)
    else:
        actual = transform_text(case.text)
    assert_exact(actual, case)
