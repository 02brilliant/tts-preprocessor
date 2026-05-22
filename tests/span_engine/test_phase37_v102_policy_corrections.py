from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.14", "삼쩜일사"),
        ("12.03", "십이쩜영삼"),
        ("13.3 비상계엄", "십삼쩜삼 비상계엄"),
        ("12.32 사태", "십이쩜삼이 사태"),
        ("12.3수치", "십이쩜삼수치"),
    ],
)
def test_phase37_event_failure_falls_back_to_decimal(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("12·3 비상계엄", "십이삼 비상계엄"),
        ("12.12 사태", "십이십이 사태"),
        ("4.19 혁명", "사일구 혁명"),
        ("5·18 민주화 운동", "오일팔 민주화 운동"),
        ("6.27 부동산대책", "육이칠 부동산대책"),
    ],
)
def test_phase37_event_numbers_pass_strict_event_gate(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.19 혁명", "영쩜일구 혁명"),
        ("4.0 혁명", "사쩜영 혁명"),
        ("14.35 대책", "십사쩜삼오 대책"),
        ("12.3-비상계엄", "십이쩜삼-비상계엄"),
        ("12.3 은 비상계엄", "십이쩜삼 은 비상계엄"),
    ],
)
def test_phase37_event_rejects_out_of_range_or_bad_context_decimal_fallback(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7·25", "칠 이오"),
        ("10·5", "십 오"),
        ("15·40 운동", "십오 사영 운동"),
        ("12·3수치", "십이 삼수치"),
        ("12·3-비상계엄", "십이 삼-비상계엄"),
    ],
)
def test_phase37_middle_dot_event_failure_falls_back_to_numeric_blocks(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.2km", "일쩜이 킬로미터"),
        ("1.2 km", "일쩜이 킬로미터"),
        ("0.8초", "영쩜팔초"),
        ("2,645.35선", "이천육백사십오쩜삼오선"),
        ("제15권", "제 십오권"),
    ],
)
def test_phase37_decimal_units_and_numeric_korean_suffix(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("60Hz", "육십 헤르츠"),
        ("60hz", "육십 헤르츠"),
        ("120 Hz", "백이십 헤르츠"),
        ("120 hz", "백이십 헤르츠"),
        ("1Gbps", "일 기가비피에스"),
        ("1Gb/s", "초당 일 기가바이트"),
    ],
)
def test_phase37_frequency_and_data_rate_aliases(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["5Hzabc", "5hzabc"])
def test_phase37_frequency_unsafe_tail_preserves(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.5만 원", "삼쩜오 만 원"),
        ("1.2억 원", "일쩜이 억 원"),
        ("2.75억 원", "이쩜칠오 억 원"),
        ("3.5만", "삼쩜오 만"),
    ],
)
def test_phase37_decimal_large_unit_krw_expansion(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6월", "유월"),
        ("2026년 6월 17일", "이천이십육년 유월 십칠일"),
        ("2026-06-17", "이천이십육년 유월 십칠일"),
        ("2026/06/17", "이천이십육년 유월 십칠일"),
        ("10월", "시월"),
        ("2026년 10월 1일", "이천이십육년 시월 일일"),
        ("2026년 10월 17일", "이천이십육년 시월 십칠일"),
        ("2026-10-17", "이천이십육년 시월 십칠일"),
        ("2026/10/17", "이천이십육년 시월 십칠일"),
        ("10월 21일", "시월 이십일일"),
        ("10개월", "십개월"),
        ("십월", "십월"),
        ("16월", "십육월"),
        ("A6월", "A6월"),
    ],
)
def test_phase37_date_month_special_cases(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2차례", "두 차례"),
        ("20차례", "스무 차례"),
        ("30차례", "서른 차례"),
        ("31차례", "서른한 차례"),
        ("39차례", "서른아홉 차례"),
        ("40차례", "사십 차례"),
        ("2 차례", "두 차례"),
        ("20 차례", "스무 차례"),
        ("39 차례", "서른아홉 차례"),
        ("40 차례", "사십 차례"),
        ("21명", "스물한 명"),
        ("31명", "서른한 명"),
        ("39명", "서른아홉 명"),
        ("40명", "사십 명"),
        ("31권", "서른한 권"),
        ("39권", "서른아홉 권"),
        ("40권", "사십 권"),
        ("31장", "서른한 장"),
        ("39장", "서른아홉 장"),
        ("40장", "사십 장"),
        ("31개", "서른한 개"),
        ("39개", "서른아홉 개"),
        ("40개", "사십 개"),
        ("39마리", "서른아홉 마리"),
        ("40마리", "사십 마리"),
        ("39그루", "서른아홉 그루"),
        ("40그루", "사십 그루"),
        ("39송이", "서른아홉 송이"),
        ("40송이", "사십 송이"),
        ("20자루", "스무 자루"),
        ("31자루", "서른한 자루"),
        ("39자루", "서른아홉 자루"),
        ("40자루", "사십 자루"),
        ("39알", "서른아홉 알"),
        ("40알", "사십 알"),
        ("39벌", "서른아홉 벌"),
        ("40벌", "사십 벌"),
        ("39켤레", "서른아홉 켤레"),
        ("40켤레", "사십 켤레"),
        ("39그릇", "서른아홉 그릇"),
        ("40그릇", "사십 그릇"),
        ("39공기", "서른아홉 공기"),
        ("40공기", "사십 공기"),
        ("39잔", "서른아홉 잔"),
        ("40잔", "사십 잔"),
        ("39병", "서른아홉 병"),
        ("40병", "사십 병"),
        ("39조각", "서른아홉 조각"),
        ("40조각", "사십 조각"),
        ("40사람", "마흔 사람"),
        ("99사람", "아흔아홉 사람"),
        ("40살", "마흔 살"),
        ("99살", "아흔아홉 살"),
        ("100명", "백 명"),
        ("101명", "백일 명"),
        ("112명", "백십이 명"),
        ("139명", "백삼십구 명"),
        ("140명", "백사십 명"),
        ("100살", "백 살"),
        ("101살", "백일 살"),
        ("139살", "백삼십구 살"),
        ("140살", "백사십 살"),
        ("100건", "백 건"),
        ("101건", "백일 건"),
        ("119건", "백십구 건"),
        ("139건", "백삼십구 건"),
        ("140건", "백사십 건"),
        ("101차례", "백일 차례"),
        ("101편", "백일 편"),
        ("101권", "백일 권"),
        ("101장", "백일 장"),
        ("101개", "백일 개"),
        ("2대", "두 대"),
        ("39대", "서른아홉 대"),
        ("40대", "사십 대"),
        ("101대", "백일 대"),
        ("2항목", "두 항목"),
        ("40항목", "사십 항목"),
        ("101항목", "백일 항목"),
        ("2사례", "두 사례"),
        ("40사례", "사십 사례"),
        ("101사례", "백일 사례"),
        ("제2문항", "제 이문항"),
        ("제2항목", "제 이항목"),
        ("제2대", "제 이대"),
        ("제5차", "제 오차"),
        ("제 5차", "제 오차"),
        ("제15권", "제 십오권"),
        ("제12권", "제 십이권"),
        ("3명", "세 명"),
        ("12권", "열두 권"),
        ("21권", "스물한 권"),
        ("A2차례", "A2차례"),
        ("2차례abc", "2차례abc"),
    ],
)
def test_phase37_charye_hybrid_counter(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1∼11월", "일월에서 십일월"),
        ("2024~2026년", "이천이십사년에서 이천이십육년"),
        ("3~5일", "삼일에서 오일"),
        ("2~5시", "두 시에서 다섯 시"),
        ("10~30분", "십분에서 삼십분"),
        ("3~8초", "삼초에서 팔초"),
        ("3~8cm", "삼에서 팔 센티미터"),
    ],
)
def test_phase37_date_time_suffix_range_expands_both_sides(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5~7쪽", "오에서 칠쪽"),
        ("8∼12장", "팔에서 십이장"),
        ("12-15장", "십이에서 십오 장"),
    ],
)
def test_phase37_page_document_tilde_range_and_hyphen_non_goal(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("010 - 1234 - 5678", "공일공 천이백삼십사 오천육백칠십팔"),
        ("001 - 23 - 456", "공공일 이십삼 사백오십육"),
        ("0.5 - 1.2 - 3", "영쩜오 일쩜이 삼"),
    ],
)
def test_phase37_spaced_hyphen_numeric_multiblock(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("K-POP", "케이팝"),
        ("A1-B2", "에이 일 비 이"),
        ("A1·B2", "에이 일 비 이"),
    ],
)
def test_phase37_mixed_alnum_code_separator_after_dictionary(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_phase37_bare_korean_degree_keeps_current_signed_policy() -> None:
    assert transform("서울 -1.3도") == "서울 마이너스 일쩜삼도"
