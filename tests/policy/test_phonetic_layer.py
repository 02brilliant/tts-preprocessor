import pytest

from engine.main import transform
from engine.pipeline.transform_engine import transform_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 13:05에 시작한다", "회의는 십삼시 오분에 시작한다"),
        ("오전 3:05에 출발한다", "오전 세시 오분에 출발한다"),
        ("13시에는 문을 닫는다", "십삼시에는 문을 닫는다"),
        ("5분부터 발언한다", "오분부터 발언한다"),
    ],
)
def test_phonetic_smoothing_positive_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("도시는 밝다", "도시는 밝다"),
        ("시와 분을 구분한다", "시와 분을 구분한다"),
        ("값은 3.14km다", "값은 삼쩜일사 킬로미터다"),
        ("비용은 ₩100이다", "비용은 백 원이다"),
    ],
)
def test_phonetic_smoothing_negative_cases(text: str, expected: str):
    assert transform_text(text) == expected


def test_phonetic_smoothing_interaction_with_prosody():
    text = "그리고 우리는 13:05에 출발하고 비용은 ₩100을 넘지 않는다"
    expected = "그리고, 우리는 십삼시 오분에 출발하고 비용은 백 원을 넘지 않는다"
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-04-17", "이천이십육년 사월 십칠일"),
        ("12.12 사태", "십이십이 사태"),
        ("₩100을 결제했다", "백 원을 결제했다"),
    ],
)
def test_phonetic_smoothing_regression_cases(text: str, expected: str):
    assert transform_text(text) == expected
