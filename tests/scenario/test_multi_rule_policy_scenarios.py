import pytest

from engine.main import transform
from engine.main import transform
from tests._policy_case import TextCase, assert_exact


NORMALIZATION_SCENARIOS = [
    # Multi-rule scenarios are the main place where precedence and guard bugs surface.
    TextCase(
        case_id="scenario-bracket-date-time-currency",
        text="회의(비공개) [긴급] 일정은 2025.01.03 13:05에 시작하고 비용은 €1,234.56이다",
        expected='회의 긴급 일정은 이천이십오년 일월 삼일 십삼시 오분에 시작하고 비용은 천이백삼십사-쩜-오육-유로이다',
        rule="multi-rule / bracket + date + HH:MM + currency",
        reason="Bracket cleanup must happen first, then date/time parsing and atomic currency parsing must cooperate without partial rewrites.",
    ),
    TextCase(
        case_id="scenario-event-suffix-clock-range-spacing",
        text="5·18 민주화 운동 행사는 오후 3시 15분부터 5시까지 열린다",
        expected="오일팔 민주화 운동 행사는 오후 세-시 십오분부터 다섯-시까지 열린다",
        rule="multi-rule / event + suffix-clock range spacing",
        reason="Event and time owners normalize independently, and each generated hour reading keeps canonical spacing before the original 시 marker.",
    ),
    TextCase(
        case_id="scenario-emergency-plus-compound-unit",
        text="화재가 나면 119에 신고하고 연비는 15.2km/L로 확인한다",
        expected="화재가 나면 일일구에 신고하고 연비는 리터당 십오쩜이 킬로미터로 확인한다",
        rule="multi-rule / emergency + compound unit",
        reason="Emergency-number context and compound-unit parsing must both apply without either blocking the other.",
    ),
    TextCase(
        case_id="scenario-time-plus-currency",
        text="회의는 12:30에 시작하고 비용은 ₩100이다",
        expected="회의는 열두시 삼십분에 시작하고 비용은 백-원이다",
        rule="multi-rule / HH:MM + currency",
        reason="Time normalization and currency normalization should coexist in one clause without introducing commas or partial rewrites.",
    ),
    TextCase(
        case_id="scenario-independent-event-and-decimal-claims",
        text="12.12 사태와 12.12 수치를 함께 적었다",
        expected='십이십이 사태와 십이-쩜-일이 수치를 함께 적었다',
        rule="multi-rule / event claim + decimal fallback",
        reason="The strong event keyword owns only the first dotted surface; the independent numeric value uses the decimal owner rather than sentence-wide preservation.",
    ),
    TextCase(
        case_id="scenario-bracket-preserve-plus-independent-compound-unit",
        text="가격은 [€1,234.56]이고 연비는 15.2km/L다",
        expected="가격은 €1,234.56이고 연비는 리터당 십오쩜이 킬로미터다",
        rule="multi-rule / bracket absolute preserve + compound unit",
        reason="The bracket owner blocks currency reentry only inside its span, while the later compound unit claims and renders independently.",
        classification="preserve",
    ),
    TextCase(
        case_id="scenario-emergency-and-general-number-same-sentence",
        text="긴급번호 112는 경찰 신고 번호이고 112명은 회의실에 있다",
        expected="긴급번호 일일이는 경찰 신고 번호이고 백십이-명은 회의실에 있다",
        rule="multi-rule / canonical emergency and counter precedence",
        reason="Emergency digit reading and the independent counter owner coexist; the counter owner generates its canonical space before 명.",
        classification="canonical",
    ),
    TextCase(
        case_id="scenario-ph-plus-frequency",
        text="pH 7.0과 60Hz 장비를 점검했다",
        expected='피에이치 칠-쩜-영과 육십-헤르츠 장비를 점검했다',
        rule="multi-rule / pH + frequency",
        reason="Two partial-match-protected special formats should normalize independently and exactly.",
    ),
]


FULL_PIPELINE_SCENARIOS = [
    TextCase(
        case_id="scenario-full-pipeline-connector-event-currency",
        text="그리고 12.12 사태 자료와 €1,234.56 보고서를 검토한다",
        expected='그리고, 십이십이 사태 자료와 천이백삼십사-쩜-오육-유로 보고서를 검토한다',
        rule="multi-rule / connector + event + currency + prosody",
        reason="Prosody may add a connector comma, but the event phrase and atomic currency reading must remain intact.",
    ),
    TextCase(
        case_id="scenario-full-pipeline-connector-hybrid-counter",
        text="그리고 5·18 민주화 운동 자료는 21명에게 배포한다",
        expected="그리고, 오일팔 민주화 운동 자료는 스물한-명에게 배포한다",
        rule="multi-rule / connector + event + hybrid counter + prosody",
        reason="Connector comma insertion must not split either the protected event phrase or the hybrid counter result.",
    ),
]


@pytest.mark.parametrize("case", NORMALIZATION_SCENARIOS, ids=lambda case: case.case_id)
def test_multi_rule_normalization_scenarios(case: TextCase):
    # These scenarios exercise cross-category precedence without involving prosody heuristics.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", FULL_PIPELINE_SCENARIOS, ids=lambda case: case.case_id)
def test_multi_rule_full_pipeline_scenarios(case: TextCase):
    # These scenarios cover the extra prosody contract on top of normalization and phonetic smoothing.
    assert_exact(transform(case.text), case)
