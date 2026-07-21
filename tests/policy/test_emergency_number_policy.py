import pytest

from engine.main import transform
from tests._policy_case import TextCase, assert_exact


GENERAL_NUMBER_CASES = [
    # Policy: without emergency context, 112/119 are plain numbers.
    TextCase(
        case_id="emergency-plain-112-general-number",
        text="112",
        expected="백십이",
        rule="emergency number / plain-general-number",
        reason="Bare 112 has no emergency context and must fall back to the general numeric reading.",
    ),
    TextCase(
        case_id="emergency-plain-119-general-number",
        text="119",
        expected="백십구",
        rule="emergency number / plain-general-number",
        reason="Bare 119 has no emergency context and must fall back to the general numeric reading.",
    ),
    TextCase(
        case_id="emergency-general-number-contextual-sentence",
        text="회의실 번호는 112다",
        expected="회의실 번호는 백십이다",
        rule="emergency number / plain-general-number",
        reason="Non-emergency room-number context must not trigger the emergency reading.",
    ),
]


POSITIVE_CONTEXT_CASES = [
    # Policy: only explicit emergency context plus valid boundary/tail allows 일일이 / 일일구.
    TextCase(
        case_id="emergency-context-112-gingeupbeonho",
        text="긴급번호 112는 경찰 신고 번호다",
        expected="긴급번호 일일이는 경찰 신고 번호다",
        rule="emergency number / emergency-context-positive",
        reason="긴급번호 and 경찰 신고 are explicit emergency triggers and 는 is an allowed tail.",
    ),
    TextCase(
        case_id="emergency-context-119-hwaja",
        text="화재가 나면 119에 신고하세요",
        expected="화재가 나면 일일구에 신고하세요",
        rule="emergency number / emergency-context-positive",
        reason="화재 and 신고 provide emergency context and 에 is an allowed tail.",
    ),
    TextCase(
        case_id="emergency-context-112-gigu-gejo",
        text="응급 구조는 112로 연결한다",
        expected="응급 구조는 일일이로 연결한다",
        rule="emergency number / emergency-context-positive",
        reason="응급 and 구조 provide emergency context and 로 is an allowed tail.",
    ),
]


ALLOWED_PARTICLE_CASES = [
    TextCase(
        case_id="emergency-allowed-tail-neun",
        text="긴급 신고는 112는 아니고 별도 번호다",
        expected="긴급 신고는 일일이는 아니고 별도 번호다",
        rule="emergency number / allowed-particle-tail",
        reason="는 is on the allowed-tail whitelist once emergency context is present.",
    ),
    TextCase(
        case_id="emergency-allowed-tail-e",
        text="소방 신고는 119에 연결된다",
        expected="소방 신고는 일일구에 연결된다",
        rule="emergency number / allowed-particle-tail",
        reason="에 is an allowed emergency-number tail under explicit emergency context.",
    ),
    TextCase(
        case_id="emergency-allowed-tail-ro",
        text="경찰 신고는 112로 바로 연결된다",
        expected="경찰 신고는 일일이로 바로 연결된다",
        rule="emergency number / allowed-particle-tail",
        reason="로 is an allowed emergency-number tail under explicit emergency context.",
    ),
    TextCase(
        case_id="emergency-allowed-tail-reul",
        text="화재 신고는 119를 먼저 누른다",
        expected="화재 신고는 일일구를 먼저 누른다",
        rule="emergency number / allowed-particle-tail",
        reason="를 is an allowed emergency-number tail under explicit emergency context.",
    ),
]


DISALLOWED_SUFFIX_CASES = [
    TextCase(
        case_id="emergency-disallowed-myeong",
        text="112명 참석",
        expected="백십이 명 참석",
        rule="emergency number / disallowed-suffix",
        reason="명 blocks the emergency reading but remains a registered counter owner with canonical spacing.",
    ),
    TextCase(
        case_id="emergency-disallowed-geon",
        text="오늘 119건이 접수됐다",
        expected="오늘 백십구 건이 접수됐다",
        rule="emergency number / disallowed-suffix",
        reason="건 blocks the emergency reading but remains a registered counter owner with canonical spacing.",
    ),
    TextCase(
        case_id="emergency-disallowed-beon",
        text="긴급 신고는 112번으로 한다",
        expected="긴급 신고는 백십이번으로 한다",
        rule="emergency number / disallowed-suffix",
        reason="번 is explicitly disallowed as an emergency tail even when emergency context exists.",
    ),
    TextCase(
        case_id="emergency-disallowed-ho",
        text="119호는 비상구 옆이다",
        expected="백십구호는 비상구 옆이다",
        rule="emergency number / disallowed-suffix",
        reason="호 is not an allowed emergency tail and should normalize as a general number label.",
    ),
    TextCase(
        case_id="emergency-disallowed-alpha-tail",
        text="112abc",
        expected="112abc",
        rule="emergency number / disallowed-suffix",
        reason="Alphabetic tails are disallowed and must not trigger either emergency conversion or partial fallback rewriting.",
    ),
]


EMBEDDED_NEGATIVE_CASES = [
    TextCase(
        case_id="canonical-single-letter-alnum-code-a112",
        text="A112",
        expected="에이 백십이",
        rule="single-letter alnum code / emergency exclusion",
        reason="The entire A112 surface belongs to the single-letter alnum code owner, so emergency and partial general-number fallbacks do not run.",
        classification="override",
    ),
    TextCase(
        case_id="emergency-embedded-2112",
        text="2112",
        expected="이천백십이",
        rule="emergency number / embedded-token-negative",
        reason="A larger number ending with 112 is not an emergency token and should read as a normal integer.",
    ),
    TextCase(
        case_id="emergency-embedded-abc119",
        text="abc119",
        expected="abc119",
        rule="emergency number / embedded-token-negative",
        reason="An alphanumeric embedding blocks emergency conversion and should not be split into partial rewrites.",
    ),
    TextCase(
        case_id="emergency-embedded-9119",
        text="9119",
        expected="구천백십구",
        rule="emergency number / embedded-token-negative",
        reason="A larger number ending in 119 is not an emergency token and should read as a normal integer.",
    ),
]


PROSODY_INTERACTION_CASES = [
    TextCase(
        case_id="emergency-prosody-protected-112",
        text="그리고 긴급번호 112는 경찰 신고 번호다",
        expected="그리고, 긴급번호 일일이는 경찰 신고 번호다",
        rule="emergency number / prosody interaction",
        reason="Once normalized to 일일이, prosody may add only the connector comma and must not split the protected phrase.",
    ),
    TextCase(
        case_id="emergency-prosody-protected-119",
        text="그리고 화재가 나면 119에 신고하세요",
        expected="그리고, 화재가 나면 일일구에 신고하세요",
        rule="emergency number / prosody interaction",
        reason="Once normalized to 일일구, prosody may add only the connector comma and must not split the protected phrase.",
    ),
]


@pytest.mark.parametrize("case", GENERAL_NUMBER_CASES, ids=lambda case: case.case_id)
def test_emergency_plain_general_number_cases(case: TextCase):
    # Bare 112/119 are general numbers unless emergency context is explicitly present.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", POSITIVE_CONTEXT_CASES, ids=lambda case: case.case_id)
def test_emergency_context_positive_cases(case: TextCase):
    # Emergency readings require explicit emergency context plus valid token boundary and allowed tail.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", ALLOWED_PARTICLE_CASES, ids=lambda case: case.case_id)
def test_emergency_allowed_particle_tail_cases(case: TextCase):
    # Allowed particles are part of the documented emergency-number tail whitelist.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", DISALLOWED_SUFFIX_CASES, ids=lambda case: case.case_id)
def test_emergency_disallowed_suffix_cases(case: TextCase):
    # Disallowed suffixes must not use the emergency reading and should fall back conservatively.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", EMBEDDED_NEGATIVE_CASES, ids=lambda case: case.case_id)
def test_emergency_embedded_token_negative_cases(case: TextCase):
    # Embedded tokens must not be reinterpreted as emergency numbers.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", PROSODY_INTERACTION_CASES, ids=lambda case: case.case_id)
def test_emergency_prosody_interaction_cases(case: TextCase):
    # Prosody must treat normalized emergency outputs as protected phrases.
    assert_exact(transform(case.text), case)
