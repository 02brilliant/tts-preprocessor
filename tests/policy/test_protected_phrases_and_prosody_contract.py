import pytest

from engine.main import transform
from engine.prosody.paragraph import split_paragraphs
from tests._policy_case import TextCase, assert_exact
from tests._span_prosody import apply_span_prosody


NO_COMMA_CASES = [
    # Simple topic-predicate structures should stay unsplit.
    TextCase(
        case_id="prosody-no-comma-simple-topic-predicate",
        text="주최 측은 일정을 발표했다",
        expected="주최 측은 일정을 발표했다",
        rule="prosody / no-comma",
        reason="A basic topic-predicate sentence is explicitly protected from comma insertion.",
    ),
    TextCase(
        case_id="prosody-no-comma-binary-phrase",
        text="사과와 배를 샀다",
        expected="사과와 배를 샀다",
        rule="prosody / binary phrase guard",
        reason="A simple A와 B phrase must not receive a midpoint comma.",
    ),
    TextCase(
        case_id="prosody-no-comma-numeric-heavy",
        text="이천이십오년 일월 삼일 십삼시 오분 백 원 삼 킬로그램 자료",
        expected="이천이십오년 일월 삼일 십삼시 오분 백 원 삼 킬로그램 자료",
        rule="prosody / numeric-density guard",
        reason="Numeric-heavy sentences should aggressively suppress comma insertion to avoid damaging protected readings.",
    ),
    TextCase(
        case_id="prosody-no-comma-protected-event-phrase",
        text="오일팔 민주화 운동 자료를 검토한다",
        expected="오일팔 민주화 운동 자료를 검토한다",
        rule="prosody / protected phrase guard",
        reason="An event phrase is a protected phrase and must not be split internally by commas.",
    ),
    TextCase(
        case_id="prosody-no-comma-protected-emergency-phrase",
        text="긴급번호 일일이는 경찰 신고 번호다",
        expected="긴급번호 일일이는 경찰 신고 번호다",
        rule="prosody / protected phrase guard",
        reason="A normalized emergency number is a protected phrase and prosody must not re-segment it.",
    ),
    TextCase(
        case_id="prosody-no-comma-protected-hybrid-counter",
        text="스물한 명이 참석했다",
        expected="스물한 명이 참석했다",
        rule="prosody / hybrid protection",
        reason="Hybrid counter results are protected and must not be split by later prosody decisions.",
    ),
    TextCase(
        case_id="prosody-no-comma-phonetic-time-binding",
        text="회의는 십삼시 오분에 시작한다",
        expected="회의는 십삼시 오분에 시작한다",
        rule="prosody / phonetic binding guard",
        reason="A phonetic-bound time expression is protected from internal or adjacent comma insertion.",
    ),
    TextCase(
        case_id="prosody-no-comma-currency-predicate",
        text="비용은 백 원이다",
        expected="비용은 백 원이다",
        rule="prosody / numeric predicate guard",
        reason="A numeric-unit phrase directly followed by the predicate should not receive a comma.",
    ),
]


COMMA_REQUIRED_CASES = [
    # Sentence-initial connectors are the clearest positive comma signal in the policy.
    TextCase(
        case_id="prosody-comma-connector-geurigo",
        text="그리고 우리는 바로 출발한다",
        expected="그리고, 우리는 바로 출발한다",
        rule="prosody / connector comma",
        reason="A sentence-initial connector such as 그리고 should take a conservative comma after it.",
    ),
    TextCase(
        case_id="prosody-comma-connector-hajiman",
        text="하지만 일정은 유지된다",
        expected="하지만, 일정은 유지된다",
        rule="prosody / connector comma",
        reason="A sentence-initial adversative connector is a clear positive comma trigger.",
    ),
    TextCase(
        case_id="prosody-comma-connector-hanpyeon",
        text="한편 마지막 설명은 다른 주제로 전환된다",
        expected="한편 마지막 설명은 다른 주제로 전환된다",
        rule="prosody / canonical context-gated 한편",
        reason="한편 is a paragraph transition and context-gated mid-sentence marker, not an unconditional leading-comma connector.",
        classification="canonical",
    ),
]


FULL_PIPELINE_PROTECTION_CASES = [
    # These cases verify that normalization, phonetic smoothing, and prosody cooperate without splitting protected phrases.
    TextCase(
        case_id="full-pipeline-protects-event-phrase-after-connector",
        text="그리고 12.12 사태 자료를 검토한다",
        expected="그리고, 십이십이 사태 자료를 검토한다",
        rule="protected phrase / event + prosody interaction",
        reason="Prosody may add a connector comma, but it must not split the normalized event phrase.",
    ),
    TextCase(
        case_id="full-pipeline-protects-emergency-phrase-after-connector",
        text="그리고 긴급번호 112는 경찰 신고 번호다",
        expected="그리고, 긴급번호 일일이는 경찰 신고 번호다",
        rule="protected phrase / emergency + prosody interaction",
        reason="The connector comma belongs before the clause, while the emergency phrase itself must remain intact.",
    ),
    TextCase(
        case_id="full-pipeline-protects-hybrid-counter-after-connector",
        text="그리고 자료는 21명에게 배포한다",
        expected="그리고, 자료는 스물한 명에게 배포한다",
        rule="protected phrase / hybrid counter + prosody interaction",
        reason="The connector comma must not cause prosody to split or reinterpret the hybrid counter result.",
    ),
    TextCase(
        case_id="full-pipeline-protects-phonetic-time-binding-after-connector",
        text="그리고 우리는 13:05에 출발한다",
        expected="그리고, 우리는 십삼시 오분에 출발한다",
        rule="protected phrase / phonetic binding + prosody interaction",
        reason="The connector comma may appear before the clause, but the phonetic-bound time must remain intact.",
    ),
]


def test_prosody_no_comma_preservation_matrix():
    # Policy-first no-comma preservation across protected phrases and numeric-heavy sentences.
    for case in NO_COMMA_CASES:
        assert_exact(apply_span_prosody(case.text), case)


def test_prosody_required_comma_matrix():
    # Registered leading connectors receive commas; context-gated 한편 remains unchanged at sentence start.
    for case in COMMA_REQUIRED_CASES:
        assert_exact(apply_span_prosody(case.text), case)


@pytest.mark.parametrize(
    "case",
    FULL_PIPELINE_PROTECTION_CASES,
    ids=lambda case: case.case_id,
)
def test_full_pipeline_protected_phrase_contract(case: TextCase):
    # Full pipeline assertions ensure prosody respects normalization and phonetic protected phrases.
    assert_exact(transform(case.text), case)


def test_prosody_paragraph_split_on_strong_transition():
    # A long buffer followed by "한편" is a direct paragraph-split signal in the policy.
    text = (
        "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
        "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
        "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
        "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
    )
    expected = (
        "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
        "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
        "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다.\n"
        "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
    )
    assert split_paragraphs(text) == expected


def test_prosody_paragraph_split_is_blocked_for_demonstratives():
    # Demonstrative starts are explicitly protected from paragraph splitting.
    text = (
        "첫 번째 문장은 문단 분리 조건을 충분히 검토할 수 있도록 길고 자세하게 작성되어 여러 배경 정보를 차례대로 설명합니다. "
        "두 번째 문장도 같은 흐름을 유지하면서 정책 기준과 예외 조건을 덧붙여 전체 길이를 안정적으로 늘립니다. "
        "이 문장은 바로 앞 설명을 이어받아 예시와 주석을 계속 덧붙이므로 별도 문단으로 나누지 않습니다."
    )
    assert split_paragraphs(text) == text
