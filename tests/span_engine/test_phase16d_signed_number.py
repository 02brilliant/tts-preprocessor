import pytest
from engine.span_engine.transform import transform

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("마이너스 숫자 문단에는 -3, -2.5, -1,250", "마이너스 숫자 문단에는 마이너스 삼, 마이너스 이쩜오, 마이너스 천이백오십"),
        ("(-3)", ""),
        ("[ -2.5 ]", " -2.5 "),
        ("값은 -2.5이다", "값은 마이너스 이쩜오이다"),
        ("온도는 -2.5℃다", "온도는 영하 이쩜오도다"),
        ("화씨는 -2.5℉다", "화씨는 화씨 영하 이쩜오도다"),
        ("코드A-3", "코드A-3"),
        ("B-2.5", "비 이쩜오"),
        ("x-3", "엑스 삼"),
        ("3-2", "3-2"),
        ("12-15장", "십이에서 십오 장"),
        ("1-2", "1-2"),
        ("3:2", "삼 대 이"),
        ("1-1 무를 함께 넣었다", "1-1 무를 함께 넣었다"),
    ],
)
def test_signed_number_normalization(text: str, expected: str) -> None:
    assert transform(text) == expected
