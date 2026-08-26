from __future__ import annotations

import pytest

from engine.span_engine.transform import transform


def assert_not_whole_preserved(text: str, expected_substrings: list[str]) -> str:
    out = transform(text)
    assert (
        out != text
    ), "Hangul-containing input with transformable surfaces must not be returned unchanged"
    for substring in expected_substrings:
        assert substring in out
    return out


def test_inline_json_shell_does_not_preserve_whole_korean_paragraph() -> None:
    text = (
        '개발팀은 curl -X POST http://localhost:8010/api/transform 명령과 '
        '{"text":"25℃"} JSON 조각도 설명했습니다. '
        "반면 오늘 온도는 25℃이고 실험 조건은 pH 7.4였습니다."
    )
    out = transform(text)
    assert out != text
    assert "curl -X POST http://localhost:8010/api/transform" in out
    assert '{"text":"25℃"}' in out
    assert "이십오도" in out
    assert "피에이치 칠쩜사" in out


def test_prefixed_ordinal_invalid_candidates_do_not_preserve_whole_paragraph() -> None:
    text = (
        "법제처 검토 자료에는 제2문항과 제 15권이 들어 있습니다. "
        "하지만 제2.5문항, 제2-문항, 제2문항abc, A제 2문항도 함께 확인합니다."
    )
    out = transform(text)
    assert out != text
    assert "제 이문항" in out
    assert "제 십오권" in out
    assert "제 이쩜오문항" in out
    assert "제2-문항" in out
    assert "제 이문항abc" in out
    assert "A제 두 문항" in out


def test_currency_invalid_candidates_do_not_preserve_whole_paragraph() -> None:
    text = (
        "결제 금액은 ₩12,300이고 해외 가격표에는 $25.99, €1,234, 300EUR, EUR300, $300이 있습니다. "
        "반면 300$, EURA 300, 300EURabc, USDX 300, USB300, KRWabc, €abc, $abc는 preserve 경계를 확인합니다."
    )
    out = transform(text)
    assert out != text
    assert "만 이천삼백 원" in out
    assert "이십오쩜구구 달러" in out
    assert "천이백삼십사 유로" in out
    assert "삼백 유로" in out
    assert "300EURabc" in out
    assert "USDX 300" in out
    assert "USB300" in out
    assert "KRWabc" in out
    assert "€abc" in out
    assert "$abc" in out


def test_symbol_alias_and_square_bracket_do_not_preserve_whole_paragraph() -> None:
    text = (
        "기술 부록에는 1／3, 1⁄3, 1∕3, 90km／h, 15.2km／L, 2025／01／03, "
        "33.3％, 2.5％p, 2.5﹪p, 13：05, −2.5℃, －2.5℉, −2.5%p, −1/3이 들어 있습니다. "
        "2.5％pa, 2.5﹪point, 15.2km/La, 3km/speed, 250m/Lite는 preserve되어야 합니다. "
        "마지막으로 [pH 7.4], [010-1234-5678], [2025-01-03], [ -2.5 ]는 보호 대상이고, "
        "괄호 밖 pH 7.4, 010-1234-5678, 2025-01-03, -2.5는 처리되어야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "삼분의 일" in out
    assert "시속 구십 킬로미터" in out
    assert "리터당 십오쩜이 킬로미터" in out
    assert "이천이십오년 일월 삼일" in out
    assert "삼십삼쩜삼 퍼센트" in out
    assert "이쩜오 퍼센트포인트" in out
    assert "십삼시 오분" in out
    assert "영하 이쩜오도" in out
    assert "마이너스 삼분의 일" in out
    assert "2.5％pa" in out
    assert "2.5﹪point" in out
    assert "15.2km/La" in out
    assert "3km/speed" in out
    assert "250m/Lite" in out
    assert "pH 7.4" in out
    assert "피에이치 칠쩜사" in out


def test_no_hangul_global_bypass_still_preserves_english_prose() -> None:
    assert transform("The temperature is 25℃.") == "The temperature is 25℃."
    assert transform('{"text":"25℃"}') == '{"text":"25℃"}'
    assert (
        transform("curl -X POST http://localhost:8010/api/transform")
        == "curl -X POST http://localhost:8010/api/transform"
    )


def test_no_hangul_standalone_supported_token_still_transforms() -> None:
    assert transform("25℃") == "이십오도"
    assert transform("$25.99") == "이십오쩜구구 달러"
    assert transform("pH 7.4") == "피에이치 칠쩜사"
    assert transform("60Hz") == "육십 헤르츠"


def test_pure_korean_without_transformable_surface_can_remain_same() -> None:
    text = "안녕하세요. 오늘 회의는 정상적으로 진행됩니다."
    assert transform(text) == text


PROBLEM_PARAGRAPH_1 = (
    "원문 인용 검증도 함께 진행합니다. The temperature is 25℃. 라는 영어 문장은 한글 문맥 사이에 놓여 있어도 "
    "영어 prose line이므로 exact preserve되어야 하고, pH 7.4 was maintained for 3 hours. 역시 pH와 숫자와 시간이 "
    "들어 있어도 영어 문장 전체가 보존되어야 합니다. 개발팀은 curl -X POST http://localhost:8010/api/transform "
    '명령과 {"text":"25℃"} JSON 조각도 shell 또는 code-like line으로 처리되어야 한다고 설명했습니다. 반면 같은 '
    "문서의 한국어 문장 안에 들어간 오늘 온도는 25℃이고 실험 조건은 pH 7.4였다는 표현은 각각 온도 owner와 pH owner가 "
    "처리해야 하므로, 영어 preserve line과 한국어 transform line을 정확히 구분하는지 확인해야 합니다."
)

PROBLEM_PARAGRAPH_2 = (
    "법제처 검토 자료에는 제2차 회의, 제15권 안내서, 제3장 요약, 제2차례 발표, 제2편 해설, 제2판 인쇄본, "
    "제2줄 오류, 제2칸 입력값이 들어 있고, 교육 자료에는 제2문항, 제2문제, 제2항목, 제2사례, 제2장면, 제2곡, "
    "제2대, 제2석, 제2표, 제2매, 제2세트, 제2팩, 제2봉, 제2종류가 차례로 배치됐습니다. spaced form 검증을 "
    "위해 제 2문항과 제 15권도 같은 문단에 넣었으며, 이들은 등록된 한글표기단위에 한정된 ordinal-like prefixed "
    "numeric suffix 정책으로 처리되어야 합니다. 하지만 A제2문항, A제 2문항, 제2문항abc, 제2문항A, 제2항목abc, "
    "제2-문항, 제2G, 제2.5문항은 각각 ASCII/code-like prefix, unsafe tail 또는 "
    "비대상 구조이므로 preserve 또는 fallback 경계를 확인해야 합니다. 제2아무말은 "
    "미등록 한글이어도 제 접두 한자어로 읽습니다."
)

PROBLEM_PARAGRAPH_3 = (
    "결제 금액은 ₩12,300으로 표시됐고, 같은 금액을 12,300원으로 적은 영수증도 함께 제출됐습니다. 후원금 모집 문서에는 "
    "3.5만 원, 3.5만원, 1.2억 원, 2.75억 원, 1,250만 원, 12,345,678원, ₩12,345,678이 들어 있어 원화 large-unit "
    "currency expansion과 comma integer currency가 모두 검증됩니다. 해외 가격표에는 $25.99, €1,234, ￥1,500, "
    "300EUR, EUR300, €300, 300 €, USD25.50, 25.50USD, 300 USD, USD 300, 300$, $300이 한 줄에 들어갔습니다. "
    "반면 EURA 300, 300EURabc, USDX 300, USB300, KRWabc, €abc, $abc는 currency owner가 앞부분만 소비하면 안 되는 "
    "preserve 케이스라고 회계팀은 명시했습니다."
)

PROBLEM_PARAGRAPH_4 = (
    "종합 스트레스 테스트 세 번째 문단입니다. 수출 보고서에는 12,345,678,901, 12,345,678,901,234, "
    "12,345,678,901,234,567 같은 큰 수와 8만 9천 개 기업, 3만 5천 명 고용, 1억 2천만 원 지원금, "
    "2조 3,400억 원 투자 계획이 동시에 들어 있고, 결제 표에는 3.5만 원, 3.5만원, 1.2억 원, 2.75억 원, "
    "USD25.50, 25.50USD, 300EUR, EUR300, ＄25.99, ﹩25.99가 함께 적혀 있습니다. 기술 부록에는 1／3, "
    "1⁄3, 1∕3, 90km／h, 15.2km／L, 2025／01／03, 33.3％, 2.5％p, 2.5﹪p, 13：05, −2.5℃, "
    "－2.5℉, −2.5%p, −1/3이 들어 있고, 2.5％pa, 2.5﹪point, 15.2km/La, 3km/speed, 250m/Lite는 "
    "preserve guard가 우선되어야 합니다. 마지막으로 [pH 7.4], [010-1234-5678], [2025-01-03], [ -2.5 ]는 "
    "square bracket 내부 보호 대상이고, 괄호 밖 pH 7.4, 010-1234-5678, 2025-01-03, -2.5는 각각의 owner 정책으로 "
    "처리되어야 합니다."
)


@pytest.mark.parametrize(
    ("paragraph", "expected_substrings"),
    [
        (PROBLEM_PARAGRAPH_1, ["이십오도", "피에이치 칠쩜사", '{"text":"25℃"}']),
        (PROBLEM_PARAGRAPH_2, ["제 이차", "제 십오권", "제 이쩜오문항"]),
        (PROBLEM_PARAGRAPH_3, ["만 이천삼백 원", "이십오쩜구구 달러", "300EURabc"]),
        (PROBLEM_PARAGRAPH_4, ["삼분의 일", "시속 구십 킬로미터", "피에이치 칠쩜사"]),
    ],
)
def test_problem_paragraphs_do_not_return_raw(
    paragraph: str, expected_substrings: list[str]
) -> None:
    out = assert_not_whole_preserved(paragraph, expected_substrings)
    if paragraph == PROBLEM_PARAGRAPH_4:
        assert "[pH 7.4]" not in out


def test_hangul_input_with_transformable_surface_and_preserve_fragment_not_raw() -> None:
    surfaces = [
        "25℃",
        "pH 7.4",
        "$25.99",
        "3kg",
        "2025-01-03",
        "010-1234-5678",
        "제2문항",
        "1／3",
        "90km／h",
    ]
    preserve_fragments = [
        '{"text":"25℃"}',
        "curl -X POST http://localhost:8010/api/transform",
        "user@example.com",
        "docs/2025/01/02/report.md",
        "제2.5문항",
        "300EURabc",
        "2.5％pa",
        "[pH 7.4]",
    ]
    for surface in surfaces:
        for preserve in preserve_fragments:
            text = f"검증 문장입니다. {preserve} 조각은 보존하고, {surface} 값은 처리해야 합니다."
            assert transform(text) != text
