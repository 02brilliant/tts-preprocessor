from __future__ import annotations

import pytest

from engine.main import transform
from tests._policy_case import TextCase, assert_exact


CANONICAL_OUTPUT_CASES = (
    TextCase(
        case_id="canonical-bracket-date-time-currency",
        text="회의(비공개) [긴급] 일정은 2025.01.03 13:05에 시작하고 비용은 €1,234.56이다",
        expected='회의 긴급 일정은 이천이십오년 일월 삼일 십삼시 오분에 시작하고 비용은 천이백삼십사-쩜-오육-유로이다',
        rule="canonical / bracket + date_time + currency",
        reason="정책 7장의 대표 복합 canonical output이다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-emergency-compound-unit",
        text="화재가 나면 119에 신고하고 연비는 15.2km/L로 확인한다",
        expected="화재가 나면 일일구에 신고하고 연비는 리터당 십오쩜이 킬로미터로 확인한다",
        rule="canonical / emergency + compound_unit",
        reason="긴급번호와 compound unit은 각 owner stage대로 함께 동작해야 한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-emergency-vs-general-number",
        text="긴급번호 112는 경찰 신고 번호이고 112명은 회의실에 있다",
        expected="긴급번호 일일이는 경찰 신고 번호이고 백십이-명은 회의실에 있다",
        rule="canonical / emergency vs number split",
        reason="같은 숫자라도 emergency context와 일반 숫자 owner가 분리되어야 한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-event-currency-prosody",
        text="그리고 12.12 사태 자료와 €1,234.56 보고서를 검토한다",
        expected='그리고, 십이십이 사태 자료와 천이백삼십사-쩜-오육-유로 보고서를 검토한다',
        rule="canonical / event + currency + prosody",
        reason="정책 canonical table의 event/currency/prosody 복합 출력이다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-counter-hybrid",
        text="21명",
        expected="스물한-명",
        rule="canonical / counter hybrid",
        reason="hybrid threshold 이하 counter는 native reading을 써야 한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-counter-hybrid-upper-bound",
        text="31명",
        expected="서른한-명",
        rule="canonical / counter hybrid upper bound",
        reason="명 counter는 1~39에서 native/hybrid reading을 사용한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-range-with-unit",
        text="3~8cm",
        expected="삼에서 팔-센티미터",
        rule="canonical / final_range",
        reason="range owner는 unit residue 없이 full-consume 해야 한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-shared-suffix-range",
        text="1∼11월",
        expected="일월에서 십일월",
        rule="canonical / shared suffix range",
        reason="date shared-suffix range는 양쪽 숫자에 월 reading을 적용한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-acronym-lexical-suffix",
        text="FTA율",
        expected="에프티에이율",
        rule="canonical / acronym lexical suffix",
        reason="pre-rule acronym lexical suffix protection이 generic fallback보다 우선한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-single-letter-hyphen",
        text="K-푸드",
        expected="케이푸드",
        rule="canonical / single-letter hyphen lexical surface",
        reason="관리되는 K-Hangul lexical compound는 K를 읽고 원본 하이픈을 제거한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-speed-compound-unit",
        text="90km/h",
        expected="시속 구십 킬로미터",
        rule="canonical / compound unit",
        reason="speed family compound unit은 dedicated reading을 사용해야 한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-special-unit",
        text="45㎡",
        expected="사십오-제곱미터",
        rule="canonical / special unit",
        reason="registered special unit inventory의 exact canonical output이다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-temperature",
        text="-2.5℃",
        expected='영하 이-쩜-오도',
        rule="canonical / temperature",
        reason="temperature parser는 음수와 decimal precision을 보존해야 한다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-ph",
        text="pH 7.4",
        expected='피에이치 칠-쩜-사',
        rule="canonical / special pH parser",
        reason="special parser canonical output이다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-hyphen-digit-blocks",
        text="123-456-7890",
        expected="일이삼 사오육 칠팔구공",
        rule="canonical / hyphen digit blocks",
        reason="hyphen digit block routing table의 canonical output이다.",
        classification="canonical",
    ),
    TextCase(
        case_id="canonical-hyphen-digit-blocks-119-shape",
        text="1-1-9",
        expected="일 일 구",
        rule="canonical / hyphen digit blocks emergency-shaped",
        reason="1-1-9는 emergency parser가 아니라 digit-block route owner다.",
        classification="canonical",
    ),
)


@pytest.mark.parametrize("case", CANONICAL_OUTPUT_CASES, ids=lambda case: case.case_id)
def test_policy_canonical_outputs(case: TextCase):
    assert_exact(transform(case.text), case)
