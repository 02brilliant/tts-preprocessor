from engine.span_engine.transform import transform


def assert_precedence_case(
    text: str,
    expected_transformed: list[str],
    expected_preserved: list[str],
) -> None:
    out = transform(text)
    assert out != text
    for item in expected_transformed:
        assert item in out, f"missing transformed substring: {item!r}\nOUT={out}"
    for item in expected_preserved:
        assert item in out, f"missing preserved substring: {item!r}\nOUT={out}"


def test_date_wins_over_code_separator_and_invalid_dates_degrade_locally():
    text = (
        "날짜 검증입니다. 2025-01-03과 2026/06/17은 날짜로 처리해야 합니다. "
        "2025-13-03과 2025-01-32는 날짜 조건을 벗어나 code separator fallback 경계를 봅니다. "
        "docs/2025/01/02/report.md는 보존하고 주변 온도 25℃는 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "이천이십오년 일월 삼일",
            "이천이십육년 유월 십칠일",
            "이공이오 일삼 공삼",
            "이공이오 공일 삼이",
            "이십오도",
        ],
        expected_preserved=["docs/2025/01/02/report.md"],
    )


def test_event_wins_over_decimal_and_middle_dot_when_event_context_matches():
    text = (
        "사건 검증입니다. 12.3 비상계엄, 12·3 비상계엄, 12.12 사태, "
        "5·18 민주화 운동은 사건 owner가 처리해야 합니다. "
        "13.3 비상계엄, 12.32 사태, 12.3수치는 사건 조건을 벗어나고 12 · 3은 독립 숫자로 읽습니다. "
        "동시에 pH 7.4도 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "십이삼 비상계엄",
            "십이십이 사태",
            "오일팔 민주화 운동",
            "십삼쩜삼 비상계엄",
            "십이쩜삼이 사태",
            "십이쩜삼수치",
            "십이 · 삼",
            "피에이치 칠쩜사",
        ],
        expected_preserved=[],
    )


def test_currency_wins_over_number_and_code_like_invalid_tokens_preserve():
    text = (
        "통화 검증입니다. ₩12,300, $25.99, 300EUR, EUR300, USD25.50은 통화로 처리합니다. "
        "EURA 300, 300EURabc, USDX 300, USB300은 preserve되어야 합니다. "
        "주변 무게 3kg도 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "만 이천삼백-원",
            "이십오쩜구구-달러",
            "삼백-유로",
            "이십오쩜오영-달러",
            "삼-킬로그램",
        ],
        expected_preserved=["EURA 300", "300EURabc", "USDX 300", "USB300"],
    )


def test_units_and_compound_units_do_not_enter_path_or_code_like_spans():
    text = (
        "단위 검증입니다. 3kg, 45㎡, 60Hz, 15.2km/L은 단위 owner가 처리합니다. "
        "docs/2025/01/02/report.md와 C:/Users/test/file.txt, 15.2km/La는 preserve되어야 합니다. "
        "주변 pH 7.4도 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "삼-킬로그램",
            "사십오-제곱미터",
            "육십-헤르츠",
            "리터당 십오쩜이 킬로미터",
            "피에이치 칠쩜사",
        ],
        expected_preserved=[
            "docs/2025/01/02/report.md",
            "C:/Users/test/file.txt",
            "15.2km/La",
        ],
    )


def test_emergency_counter_phone_and_hyphen_precedence_boundaries():
    text = (
        "번호 검증입니다. 112, 119, 1-1-2, 1-1-9는 번호로 읽고 "
        "112명, 119건, 112번 버스, 119번 버스는 counter와 suffix 정책을 따릅니다. "
        "010-1234-5678과 12-34-56도 처리하지만 1-2와 1-1 무는 preserve되어야 합니다. "
        "주변 25℃도 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "백십이",
            "백십구",
            "일 일 이",
            "일 일 구",
            "백십이-명",
            "백십구-건",
            "백십이번 버스",
            "백십구번 버스",
            "공일공 일이삼사 오육칠팔",
            "일이 삼사 오육",
            "이십오도",
        ],
        expected_preserved=["1-2", "1-1 무"],
    )


def test_signed_temperature_wins_unless_hyphen_code_prefix_blocks_it():
    text = (
        "온도 검증입니다. -2.5℃, -2.5℉, +3℃, 온도-2.5℃는 signed temperature로 처리합니다. "
        "A-2.5℃, x-2.5℉, B-2.5º는 hyphen code-like prefix 때문에 preserve되어야 합니다. "
        "주변 $25.99도 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "영하 이쩜오도",
            "화씨 영하 이쩜오도",
            "영상 삼도",
            "온도영하 이쩜오도",
            "이십오쩜구구-달러",
        ],
        expected_preserved=["A-2.5℃", "x-2.5℉", "B-2.5º"],
    )


def test_prefixed_ordinal_wins_over_counter_but_plain_counter_remains_counter():
    text = (
        "ordinal 검증입니다. 제2문항과 제 15권은 prefixed ordinal로 처리합니다. "
        "2문항, 40문항, 101문항은 plain counter로 처리합니다. "
        "제2문항abc와 제2.5문항도 한자어로 읽습니다. "
        "주변 pH 7.4도 처리해야 합니다."
    )
    assert_precedence_case(
        text,
        expected_transformed=[
            "제-이문항",
            "제-십오권",
            "두-문항",
            "사십-문항",
            "백일-문항",
            "피에이치 칠쩜사",
            "제-이문항abc",
            "제-이쩜오문항",
        ],
        expected_preserved=[],
    )
