from __future__ import annotations

import pytest

from engine.span_engine import transform


def test_k_pop_fixed_dictionary_inside_lexical_chain() -> None:
    text = "K-푸드·K-뷰티·K-POP 방산"

    assert transform(text) == "케이푸드·케이뷰티·케이팝 방산"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("K-푸드", "케이푸드"),
        ("K-뷰티", "케이뷰티"),
        ("K-컬처", "케이컬처"),
        ("K-콘텐츠", "케이콘텐츠"),
        ("K-방산", "케이방산"),
        ("K-드라마", "케이드라마"),
        ("K-팝", "케이팝"),
        ("오늘 K-푸드 산업", "오늘 케이푸드 산업"),
        ("K-푸드와 K-뷰티", "케이푸드와 케이뷰티"),
        ("K-POP", "케이팝"),
    ],
)
def test_k_hangul_lexical_prefix_policy(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AK-푸드", "AK-푸드"),
        ("model-K-푸드", "model-K-푸드"),
        ("K-푸드-v2", "K-푸드-v2"),
        ("K-푸드_test", "K-푸드_test"),
        ("K-2024", "K-2024"),
        ("K-ABC", "K-ABC"),
        ("K-pop", "K-pop"),
        ("https://example.com/K-푸드", "https://example.com/K-푸드"),
        ("docs/K-푸드/report.md", "docs/K-푸드/report.md"),
    ],
)
def test_k_hangul_lexical_prefix_boundaries_and_unsafe_tails(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_iso_iec_fixed_lexical_compound_and_hangul_middle_dot_preserve() -> None:
    assert transform("ISO·IEC 등") == "아이에스오·아이이씨 등"
    assert transform("자동차·부품") == "자동차·부품"
    assert transform("원목·제재목") == "원목·제재목"


def test_4k_fixed_technical_term_and_unsafe_alnum_preserve() -> None:
    assert transform("4K 장비와 4K 카메라") == "포케이 장비와 포케이 카메라"
    assert transform("USB300") == "USB300"


@pytest.mark.parametrize("unit", ["5Ghz", "5GHz", "5ghz"])
def test_frequency_ghz_alias_numeric_prefix(unit: str) -> None:
    assert transform(f"{unit} 환경") == "오 기가헤르츠 환경"


@pytest.mark.parametrize("text", ["5Hzabc", "5hzabc"])
def test_frequency_unsafe_tail_preserve(text: str) -> None:
    assert transform(text) == text


def test_plain_volume_m3_full_consumes() -> None:
    assert transform("45m3") == "사십오 세제곱미터"
    assert transform("45m²") == "사십오 제곱미터"
    assert transform("45㎥") == "사십오 세제곱미터"
    assert transform("45m3abc") == "45m3abc"


def test_decimal_and_middle_dot_numeric_list_fallbacks() -> None:
    text = "3.14, 12.03, 0.125, 7·25, 10·5, 12 · 3, 12. 3, 12 .3, 1·2·3, 123·456"

    assert (
        transform(text)
        == "삼쩜일사, 십이쩜영삼, 영쩜일이오, 칠 이오, 십 오, 12 · 3, 12. 3, 12 .3, 일 이 삼, 일이삼 사오육"
    )


def test_decimal_trailing_zero_digits_are_preserved() -> None:
    assert transform("승률 0.600, 비율 2:1") == "승률 영쩜육영영, 비율 이 대 일"


def test_calendar_invalid_date_uses_code_separator_fallback() -> None:
    text = "2026-04-17, 2025-13-03, 2025-01-32, 2024-00-10"

    assert (
        transform(text)
        == "이천이십육년 사월 십칠일, 이공이오 일삼 공삼, 이공이오 공일 삼이, 이공이사 공공 일공"
    )


def test_code_context_valid_date_preserve_but_invalid_date_fallbacks() -> None:
    text = "날짜형 코드 2026-04-17, 비정상 날짜 2025-13-03"

    assert transform(text) == "날짜형 코드 2026-04-17, 비정상 날짜 이공이오 일삼 공삼"


def test_spaced_hyphen_numeric_multiblock_with_korean_suffix_full_consumes() -> None:
    text = "공백 포함 표기 010 - 1234 - 5678도 함께 적는다."

    assert transform(text) == "공백 포함 표기 공일공 천이백삼십사 오천육백칠십팔도 함께 적는다."
    assert "010 - 1234 - 오천육백칠십팔도" not in transform(text)


def test_signed_temperature_korean_boundary_full_consumes_or_preserves() -> None:
    assert transform("온도-2.5℃") == "온도영하 이쩜오도"
    assert transform("-2.5℃") == "영하 이쩜오도"
    assert transform("-2.5℉") == "화씨 영하 이쩜오도"
    assert transform("A-2.5℃") == "A-2.5℃"
    assert transform("x-2.5℉") == "x-2.5℉"
    assert transform("30ºCtest") == "30ºCtest"
    assert transform("40℉abc") == "40℉abc"
    assert transform("- 2.5℃") != "영하 이쩜오도"


def test_two_block_hyphen_decimal_code_policy() -> None:
    assert transform("B-2.5") == "비 이쩜오"
    assert transform("x-3") == "엑스 삼"
    assert transform("A-10C") == "에이 십 씨"
    for text in ["3-2", "1-2", "1-1 무", "B-2.5beta", "x-2.5℉", "A-3kg"]:
        assert transform(text) == text
    assert transform("12-15장") == "십이에서 십오 장"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("K-1", "케이 원"),
        ("K1", "케이 원"),
        ("K-2", "케이 투"),
        ("K2", "케이 투"),
        ("K-9", "케이 나인"),
        ("K9", "케이 나인"),
        ("K-10", "케이 십"),
        ("K10", "케이 십"),
        ("K-21", "케이 이십일"),
        ("K21", "케이 이십일"),
        ("A-1", "에이 원"),
        ("A1", "에이 원"),
        ("A-10", "에이 십"),
        ("A10", "에이 십"),
        ("B-1", "비 원"),
        ("B1", "비 원"),
        ("B-10", "비 십"),
        ("B10", "비 십"),
        ("K-1A", "케이 원 에이"),
        ("K1A", "케이 원 에이"),
        ("K-21B", "케이 이십일 비"),
        ("K21B", "케이 이십일 비"),
        ("F-15C", "에프 십오 씨"),
        ("F15C", "에프 십오 씨"),
        ("K-21BC", "케이 이십일 비씨"),
        ("A-10C", "에이 십 씨"),
        ("오늘 K-1 장비", "오늘 케이 원 장비"),
        ("장비는 F-15C입니다", "장비는 에프 십오 씨입니다"),
    ],
)
def test_single_letter_uppercase_alnum_code_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AA-10", "AA-10"),
        ("AB10", "AB10"),
        ("A-10CAT", "A-10CAT"),
        ("A10CAT", "A10CAT"),
        ("A-3kg", "A-3kg"),
        ("A3kg", "A3kg"),
        ("APIv2", "APIv2"),
        ("GPU2X", "GPU2X"),
        ("USB300", "USB300"),
        ("model-X200", "model-X200"),
        ("X-200-beta", "X-200-beta"),
        ("R2D2", "R2D2"),
        ("K-2024", "K-2024"),
        ("K-ABC", "K-ABC"),
        ("K-pop", "K-pop"),
        ("AK-1", "AK-1"),
        ("model-K1", "model-K1"),
        ("model-K-1", "model-K-1"),
        ("https://example.com/K-1", "https://example.com/K-1"),
        ("docs/K-1/report.md", "docs/K-1/report.md"),
    ],
)
def test_single_letter_uppercase_alnum_code_preserve_boundaries(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_ph_case_sensitive_owner_and_decimal_fallback_consistency() -> None:
    text = "pH 검증 pH 7.4, pH7.4, pH 10.25, xpH 7.4, apH7.4, pH 7.4a, pH7.4test"
    assert (
        transform(text)
        == "pH 검증 피에이치 칠쩜사, 피에이치 칠쩜사, 피에이치 십쩜이오, xpH 7.4, apH7.4, pH 7.4a, pH7.4test"
    )

    assert (
        transform("비교용으로 PH 7.4, ph 7.4, pH, 7.4 pH도 넣는다.")
        == "비교용으로 피에이치 칠쩜사, ph 칠쩜사, pH, 칠쩜사 pH도 넣는다."
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "K-POP, ISO·IEC, 4K 장비, 5Ghz 환경, https://example.com/a/b",
            "케이팝, 아이에스오·아이이씨, 포케이 장비, 오 기가헤르츠 환경, https://example.com/a/b",
        ),
        (
            "K-POP, user@example.com, 45m3",
            "케이팝, user@example.com, 사십오 세제곱미터",
        ),
        (
            "docs/2025/01/02/report.md, 온도-2.5℃, pH 7.4",
            "docs/2025/01/02/report.md, 온도영하 이쩜오도, 피에이치 칠쩜사",
        ),
        (
            "C:/Users/test/file.txt, 5Ghz 환경, K-POP",
            "C:/Users/test/file.txt, 오 기가헤르츠 환경, 케이팝",
        ),
        ("https://example.com/a/b", "https://example.com/a/b"),
        ("user@example.com", "user@example.com"),
        ("docs/2025/01/02/report.md", "docs/2025/01/02/report.md"),
    ],
)
def test_embedded_protected_tokens_preserve_only_their_span(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_embedded_protected_token_does_not_trigger_global_bypass() -> None:
    text = "K-POP, ISO·IEC, 4K 장비, 5Ghz 환경, 45m3, 온도-2.5℃, pH 7.4, https://example.com/a/b"

    assert (
        transform(text)
        == "케이팝, 아이에스오·아이이씨, 포케이 장비, 오 기가헤르츠 환경, 사십오 세제곱미터, 온도영하 이쩜오도, 피에이치 칠쩜사, https://example.com/a/b"
    )


@pytest.mark.parametrize(
    "text",
    ["5Hzabc", "USB300", "A-2.5℃", "x-2.5℉", "30ºCtest", "40℉abc"],
)
def test_embedded_protected_token_change_keeps_unsafe_preserve_guards(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6,402억 달러", "육천사백이억 달러"),
        ("6,402억 원", "육천사백이억 원"),
        ("6,402억 유로", "육천사백이억 유로"),
        ("12,300원", "만 이천삼백 원"),
        ("1,250만 원", "천이백오십만 원"),
        ("1,250만 원을 포함한다.", "천이백오십만 원을 포함한다."),
        ("1,250만 원은 필요하다.", "천이백오십만 원은 필요하다."),
        ("2조 3,400억 원", "이조 삼천사백억 원"),
        ("누적 수출액이 6,402억 달러를 기록했다.", "누적 수출액이 육천사백이억 달러를 기록했다."),
        ("일반 숫자 문단에는 2조 3,400억 원을 넣었다.", "일반 숫자 문단에는 이조 삼천사백억 원을 넣었다."),
        ("3조 4,000억 원", "삼조 사천억 원"),
    ],
)
def test_comma_number_large_unit_and_currency_surfaces(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["id_12,300", "v1,250", "ABC12,300"])
def test_comma_number_code_like_guards_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,250", "천이백오십"),
        ("12,345", "만 이천삼백사십오"),
        ("6402", "육천사백이"),
        ("10000", "만"),
        ("1,250, 12,345, 6402, 10000", "천이백오십, 만 이천삼백사십오, 육천사백이, 만"),
    ],
)
def test_bare_integer_and_comma_integer_surfaces(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["id_12345", "ABC123", "USB300", "v1.2.3", "log_2025_01_03"],
)
def test_bare_integer_code_like_guards_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("LLM, WHO, OECD", "엘엘엠, 더블유에이치오, 오이씨디"),
        ("KBS,", "케이비에스,"),
        ("ISO·IEC가", "아이에스오·아이이씨가"),
        ("ISO·IEC 관련", "아이에스오·아이이씨 관련"),
        ("MBC, SBS, EBS, JTBC", "엠비씨, 에스비에스, 이비에스, 제이티비씨"),
        ("USB, HTML", "유에스비, 에이치티엠엘"),
        ("KBS, YTN", "케이비에스, 와이티엔"),
        ("MBC는 보도했다.", "엠비씨는 보도했다."),
        ("HTML을 확인했다.", "에이치티엠엘을 확인했다."),
    ],
)
def test_fixed_acronym_and_lexical_compound_boundaries(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["USB300", "CPU900", "GPU2X", "APIv2", "JSONPath", "HTML5test"])
def test_fixed_acronym_code_like_guards_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("250ml", "이백오십 밀리리터"),
        ("250mL", "이백오십 밀리리터"),
        ("250ML", "이백오십 밀리리터"),
    ],
)
def test_milliliter_unit_aliases(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["250mlabc", "250mLtest"])
def test_milliliter_unit_alias_unsafe_tail_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.5m/s", "초속 영쩜오 미터"),
        ("5m/s", "초속 오 미터"),
        ("8.5m/min", "분속 팔쩜오 미터"),
        ("0.5m/sabc", "0.5m/sabc"),
    ],
)
def test_decimal_compound_slash_unit_surfaces(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_unsupported_duration_range_suffix_does_not_partially_rewrite_time() -> None:
    assert transform("7~9시간 작업") == "일곱 시간에서 아홉 시간 작업"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1대1로 스마트폰 기초부터", "일대일로 스마트폰 기초부터"),
        ("1대1 교육", "일대일 교육"),
        ("1대1 상담", "일대일 상담"),
        ("2대1 구조", "이대일 구조"),
        ("10대1 경쟁률", "십대일 경쟁률"),
    ],
)
def test_compact_dae_relation_reads_both_numbers(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["1-1 무", "1-2", "현대1대1", "A1대1", "1대1beta"],
)
def test_compact_dae_relation_keeps_out_of_scope_and_unsafe_preserve(
    text: str,
) -> None:
    assert transform(text) == text


def test_standalone_colon_score_now_uses_broad_dae_reading() -> None:
    assert transform("3:2 승") == "삼 대 이 승"


def test_colon_semantic_pair_with_approved_context_reads_as_dae_relation() -> None:
    assert transform("2:1 비율") == "이 대 일 비율"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("제5차", "제 오차"),
        ("제5차 한미 표준협력 포럼", "제 오차 한미 표준협력 포럼"),
        ("2025 제5차 한미 표준협력 포럼", "이천이십오 제 오차 한미 표준협력 포럼"),
        ("제15권 안내 문구", "제 십오권 안내 문구"),
        ("제62회 무역의 날", "제 육십이회 무역의 날"),
        ("제10장", "제 십장"),
        ("제4과", "제 사과"),
        ("제 5차", "제 오차"),
        ("제 3명", "제 삼명"),
        ("제 5살", "제 오살"),
        ("3명", "세 명"),
        ("12권", "열두 권"),
        ("제12권", "제 십이권"),
    ],
)
def test_prefixed_numeric_suffix_ordinals_follow_attached_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["A제5차", "A제 5차", "제5G", "제5abc", "제5-차"])
def test_prefixed_numeric_suffix_unsafe_forms_preserve(text: str) -> None:
    assert transform(text) == text
