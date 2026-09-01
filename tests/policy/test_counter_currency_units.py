import pytest

from engine.main import transform as transform_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21명", "스물한-명"),
        ("22권", "22권"),
        ("23장", "23장"),
        ("24개", "스물네-개"),
        ("29명", "스물아홉-명"),
        ("30명", "서른-명"),
        ("30권", "30권"),
        ("31명", "서른한-명"),
        ("31권", "31권"),
        ("사과 21개는 남았다", "사과 스물한-개는 남았다"),
        ("책 30권을 정리했다", "책 서른-권을 정리했다"),
    ],
)
def test_hybrid_counter_positive_and_boundary_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21층", "21층"),
        ("21원", "이십일-원"),
        ("57개", "오십칠-개"),
        ("100명", "백-명"),
        ("101권", "백일-권"),
    ],
)
def test_hybrid_counter_negative_and_regression_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("₩100", "백-원"),
        ("100 KRW", "백-원"),
        ("KRW100", "백-원"),
        ('$10.50', '십-쩜-오영-달러'),
        ("€100", "백-유로"),
        ("¥100", "백-엔"),
        ("£100", "백-파운드"),
        ("10억 원", "십억 원"),
        ('1.5조 원', '일-쩜-오-조 원'),
        ('₩100.5', '백-쩜-오-원'),
        ("300USDabc", "300USDabc"),
        ("EURA 300", "EURA 300"),
        ("300KRWa", "300KRWa"),
    ],
)
def test_currency_policy_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10km/h", "시속 십 킬로미터"),
        ("5m/s", "초속 오 미터"),
        ('15.2km/L', '리터당 십오쩜이 킬로미터'),
        ("60Hz", "육십-헤르츠"),
        ('2.4GHz', '이-쩜-사-기가헤르츠'),
        ("45㎡", "사십오-제곱미터"),
        ("220V", "220V"),
        ("m/L", "m/L"),
        ("15.2km/La", "15.2km/La"),
        ("3km/speed", "3km/speed"),
    ],
)
def test_unit_policy_cases(text: str, expected: str):
    assert transform_text(text) == expected
