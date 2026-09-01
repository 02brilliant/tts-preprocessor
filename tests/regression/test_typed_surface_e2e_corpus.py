from __future__ import annotations

import pytest

from engine.main import transform
from engine.main import transform
from tests._policy_case import TextCase, assert_exact


PARTIAL_MATCH_GUARD_CASES = [
    TextCase(
        case_id="typed-surface-partial-fta-noun",
        text="FTA 요건",
        expected="에프티에이 요건",
        rule="typed surface / partial match guard",
        reason="Acronym protection must normalize the acronym but must not reinterpret the following noun as a particle path.",
        classification="regression",
    ),
    TextCase(
        case_id="typed-surface-partial-ai-middle-dot-sentence",
        text="AI·디지털 교육",
        expected="에이아이·디지털 교육",
        rule="typed surface / canonical lexical middle-dot preservation",
        reason="The acronym normalizes independently while the original middle dot and Hangul continuation remain byte-exact.",
        classification="canonical",
    ),
    TextCase(
        case_id="typed-surface-partial-large-unit-currency",
        text="6402억 달러",
        expected="육천사백이억 달러",
        rule="typed surface / partial match guard",
        reason="Large-unit atomic outputs must normalize as a whole surface without introducing suffix repair gaps.",
        classification="regression",
    ),
    TextCase(
        case_id="typed-surface-partial-unicode-tilde-month",
        text="1∼11월",
        expected="일월에서 십일월",
        rule="typed surface / canonical shared-month range",
        reason="The range owner applies the shared 월 suffix reading to both operands for every registered tilde alias.",
        classification="canonical",
    ),
    TextCase(
        case_id="typed-surface-partial-tilde-unit",
        text="3~8cm",
        expected="삼에서 팔-센티미터",
        rule="typed surface / partial match guard",
        reason="Range plus unit must normalize as a whole surface instead of partially reading only the left side.",
        classification="regression",
    ),
    TextCase(
        case_id="typed-surface-partial-signed-degree",
        text="-1.3도",
        expected='마이너스 일-쩜-삼도',
        rule="typed surface / partial match guard",
        reason="Signed degree quantities must stay on the dedicated parser route and never leak a raw minus sign.",
        classification="regression",
    ),
    TextCase(
        case_id="typed-surface-partial-event-middle-dot",
        text="12·12 사태",
        expected="십이십이 사태",
        rule="typed surface / partial match guard",
        reason="Event-style middle-dot numbers must normalize as an event surface instead of a generic structured-number split.",
        classification="regression",
    ),
    TextCase(
        case_id="typed-surface-partial-hyphen-sequence",
        text="K-푸드·K-뷰티·K-POP",
        expected="케이푸드·케이뷰티·케이팝",
        rule="typed surface / canonical K lexical sequence",
        reason="K-Hangul owners and the K-POP dictionary entry normalize independently while original middle-dot delimiters remain unchanged.",
        classification="canonical",
    ),
]


LONG_SENTENCE_E2E_CASES = [
    TextCase(
        case_id="typed-surface-e2e-acronym-large-unit-range",
        text="FTA 요건만 충족하면 AI·디지털 교육 전략은 6402억 달러 규모로 1∼11월 동안 유지된다",
        expected="에프티에이 요건만 충족하면 에이아이·디지털 교육 전략은 육천사백이억 달러 규모로 일월에서 십일월 동안 유지된다",
        rule="typed surface / canonical independent lexical and range owners",
        reason="Acronym, original middle-dot delimiter, large-unit, and shared-month range decisions remain independent in one sentence.",
        classification="canonical",
    ),
    TextCase(
        case_id="typed-surface-e2e-lexical-non-rewrite-hyphen",
        text="민관 전문가가 있는 조직은 K-푸드·K-뷰티·K-POP 전략을 함께 검토한다",
        expected="민관 전문가가 있는 조직은 케이푸드·케이뷰티·케이팝 전략을 함께 검토한다",
        rule="typed surface / canonical K lexical and dictionary owners",
        reason="K-Hangul lexical claims and the K-POP dictionary entry normalize independently while original middle dots remain unchanged.",
        classification="canonical",
    ),
    TextCase(
        case_id="typed-surface-e2e-range-and-degree",
        text="기온은 -1.3도까지 떨어졌지만 3~8cm 적설은 유지됐다",
        expected='기온은 마이너스 일-쩜-삼도까지 떨어졌지만, 삼에서 팔-센티미터 적설은 유지됐다',
        rule="typed surface / canonical owners plus subordinate prosody",
        reason="Signed degree and range claims remain independent before prosody_extra inserts the registered -지만 clause comma.",
        classification="canonical",
    ),
    TextCase(
        case_id="typed-surface-e2e-event-mixed-paragraph",
        text="12·12 사태 이후 시장은 흔들렸지만 FTA 요건과 AI·반도체 전략은 유지됐다",
        expected="십이십이 사태 이후 시장은 흔들렸지만, 에프티에이 요건과 에이아이·반도체 전략은 유지됐다",
        rule="typed surface / canonical owners plus subordinate prosody",
        reason="Event, acronym, and lexical middle-dot claims remain atomic before prosody_extra inserts the registered -지만 clause comma.",
        classification="canonical",
    ),
]

FULL_PIPELINE_E2E_CASES = [
    TextCase(
        case_id="typed-surface-full-pipeline-connector-mixed",
        text="그리고 FTA는 유지하고 AI·반도체와 K-푸드 전략은 6402억 달러 규모로 1∼11월 동안 -1.3도 환경에서도 추진한다",
        expected='그리고, 에프티에이는 유지하고 에이아이·반도체와 케이푸드 전략은 육천사백이억 달러 규모로 일월에서 십일월 동안 마이너스 일-쩜-삼도 환경에서도 추진한다',
        rule="typed surface / full pipeline e2e",
        reason="Normalization, typed protected surfaces, phonetic smoothing, and prosody must cooperate without reopening protected boundaries in a mixed sentence.",
        classification="regression",
    ),
]


@pytest.mark.parametrize("case", PARTIAL_MATCH_GUARD_CASES, ids=lambda case: case.case_id)
def test_typed_surface_partial_match_guard_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", LONG_SENTENCE_E2E_CASES, ids=lambda case: case.case_id)
def test_typed_surface_long_sentence_e2e_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", FULL_PIPELINE_E2E_CASES, ids=lambda case: case.case_id)
def test_typed_surface_full_pipeline_e2e_cases(case: TextCase):
    assert_exact(transform(case.text), case)
