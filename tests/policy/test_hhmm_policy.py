import pytest

from engine.main import transform
from tests._policy_case import assert_text_exact


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 12:30에 시작한다", "회의는 열두시 삼십분에 시작한다"),
        ("도착 시각 13:05", "도착 시각 십삼시 오분"),
        ("오전 3:05에 출발한다", "오전 세시 오분에 출발한다"),
        pytest.param(
            "탑승 시간은 24:00이다",
            "탑승 시간은 이십사시이다",
            id="canonical-24-00-zero-minute-omission",
        ),
    ],
)
def test_hhmm_positive_context_cases(text: str, expected: str):
    assert_text_exact(transform(text), text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "한국 vs 일본 3:2",
            "한국 vs 일본 삼 대 이",
            id="canonical-score-semantic-pair",
        ),
        pytest.param(
            "화면 비율 16:9",
            "화면 비율 십육 대 구",
            id="canonical-ratio-semantic-pair",
        ),
        ("score 12:30", "score 12:30"),
        ("12:30, 14:20, 18:10", "12:30, 14:20, 18:10"),
    ],
)
def test_hhmm_negative_context_cases(text: str, expected: str):
    assert_text_exact(transform(text), text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "회의는 00:00에 시작한다",
            "회의는 영시에 시작한다",
            id="canonical-00-00-zero-minute-omission",
        ),
        ("회의는 23:59에 끝난다", "회의는 이십삼시 오십구분에 끝난다"),
        pytest.param(
            "회의는 24:01에 끝난다",
            "회의는 이십사시 일분에 끝난다",
            id="canonical-24-mm-strong-time",
        ),
        pytest.param(
            "회의는 7:5에 시작한다",
            "회의는 칠 대 오에 시작한다",
            id="canonical-one-digit-minute-semantic-pair",
        ),
    ],
)
def test_hhmm_boundary_cases(text: str, expected: str):
    assert_text_exact(transform(text), text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "3:05:09",
            "3:05:09",
            id="canonical-standalone-short-hour-timecode-preserve",
        ),
        pytest.param(
            "13:05:09",
            "13:05:09",
            id="canonical-standalone-timecode-preserve",
        ),
        ("12:30", "12:30"),
        ("0:00", "영시"),
        ("24:00", "이십사시"),
    ],
)
def test_hhmm_standalone_cases(text: str, expected: str):
    assert_text_exact(transform(text), text, expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "기록은 3:05:09이다",
            "기록은 3:05:09이다",
            id="canonical-contextual-short-hour-timecode-preserve",
        ),
        pytest.param(
            "기록은 13:05:09이다",
            "기록은 13:05:09이다",
            id="canonical-contextual-timecode-preserve",
        ),
    ],
)
def test_hhmmss_independent_sentence_cases(text: str, expected: str):
    assert_text_exact(transform(text), text, expected)
