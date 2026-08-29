from engine.span_engine.transform import transform


def test_plus_general_number_reading_and_invalid_preserve():
    cases = [
        ("+1 올랐다", "플러스 일 올랐다"),
        ("값은 +1.5입니다", "값은 플러스 일쩜오입니다"),
        ("오차는 +0.05다", "오차는 플러스 영쩜영오다"),
        ("+1,000.50 증가", "플러스 천쩜오영 증가"),
    ]
    for source, expected in cases:
        assert transform(source) == expected

    for source in ("+", "++1", "+.5", "+1.", "+01", "+1,00.5"):
        assert transform(source) == source


def test_plus_unit_currency_temperature_percent_full_consume():
    cases = [
        ("+1.5kg", "플러스 일쩜오-킬로그램"),
        ("+2cm", "플러스 이-센티미터"),
        ("-25kg", "마이너스 이십오-킬로그램"),
        ("+25℃", "영상 이십오도"),
        ("+25°C", "영상 이십오도"),
        ("+77℉", "화씨 영상 칠십칠도"),
        ("+77°F", "화씨 영상 칠십칠도"),
        ("-25℃", "영하 이십오도"),
        ("-25°C", "영하 이십오도"),
        ("-77℉", "화씨 영하 칠십칠도"),
        ("-77°F", "화씨 영하 칠십칠도"),
        ("+1.5℃", "영상 일쩜오도"),
        ("-1.5℃", "영하 일쩜오도"),
        ("+0.0℃", "영상 영쩜영도"),
        ("-0.0℃", "영하 영쩜영도"),
        ("+10%", "플러스 십-퍼센트"),
        ("-2%", "마이너스 이-퍼센트"),
        ("+1,000원", "플러스 천-원"),
        ("+3.50달러", "플러스 삼쩜오영-달러"),
        ("+0.05%", "플러스 영쩜영오-퍼센트"),
    ]
    for source, expected in cases:
        assert transform(source) == expected

    for source in (
        "+01kg",
        "+1,00.5kg",
        "/path/+1.5kg/log",
        "`+1.5kg`",
    ):
        assert transform(source) == source


def test_plus_international_phone_full_consume_and_invalid_preserve():
    cases = [
        ("+82-10-1234-5678", "플러스 팔이 일공 일이삼사 오육칠팔"),
        ("+1-800-123-4567", "플러스 일 팔공공 일이삼 사오육칠"),
    ]
    for source, expected in cases:
        assert transform(source) == expected

    for source in (
        "+82-foo",
        "/path/+82-10-1234/log",
        "`+82-10-1234-5678`",
        "email+tag@example.com",
        "https://example.com?q=+82-10",
    ):
        assert transform(source) == source


def test_plus_numeric_delimited_owners():
    cases = [
        ("+1:2 비율", "플러스 일 대 이 비율"),
        ("1:+2 비율", "일 대 플러스 이 비율"),
        ("+1.5:-2.0 경기", "플러스 일쩜오 대 마이너스 이쩜영 경기"),
        ("+0.0:1 배율", "플러스 영쩜영 대 일 배율"),
        ("+1,000.50:2 스케일", "플러스 천쩜오영 대 이 스케일"),
        ("+1:2:3", "플러스 일 대 이 대 삼"),
        ("1:+2:-3:4", "일 대 플러스 이 대 마이너스 삼 대 사"),
        ("+1.2:2.3:+3.0", "플러스 일쩜이 대 이쩜삼 대 플러스 삼쩜영"),
        ("+1,000:2,000:+3,000", "플러스 천 대 이천 대 플러스 삼천"),
        ("+1.5~+2.0kg", "플러스 일쩜오에서 플러스 이쩜영-킬로그램"),
        ("-1~+2kg", "마이너스 일에서 플러스 이-킬로그램"),
        ("+0.0∼1.5cm", "플러스 영쩜영에서 일쩜오-센티미터"),
        (
            "+1,000.50〜+2,000.75원",
            "플러스 천쩜오영에서 플러스 이천쩜칠오-원",
        ),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_plus_numeric_delimited_invalid_and_context_preserve():
    for source in (
        "영상 +1:23",
        "line +1:2",
        "/path/+1:2/log",
        "`+1:2 비율`",
        "+01:2 비율",
        "+1.:2 비율",
        "+.5:2 비율",
        "+01:2:3",
        "1:+2.:3",
        "1:+2:+3:+4:+5:+6:+7:+8:+9",
        "line +10:20:30",
        "/path/+1:2:3/log",
        "+1:02:03",
        "+1.5-2kg",
        "+1.5–2kg",
        "`+1.5~2kg`",
        "/path/+1.5~2kg/log",
        "+01.5~2kg",
        "+1.~2kg",
        "+.5~2kg",
    ):
        assert transform(source) == source
    assert transform("+1.5~2테스트") == "플러스 일쩜오에서 이 테스트"


def test_plus_code_math_url_email_protected_contexts_preserve():
    for source in (
        "C++17",
        "C++",
        "A+B",
        "x+y=3",
        "foo+bar",
        "a+=1",
        "email+tag@example.com",
        "https://example.com?q=+1",
        "/path/+1/log",
        "`+1.5kg`",
        "`+1:2 비율`",
    ):
        assert transform(source) == source
