import pytest

from engine.pipeline.transform_engine import transform_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 12:30에 시작한다", "회의는 열두시 삼십분에 시작한다"),
        ("도착 시각 13:05", "도착 시각 십삼시 오분"),
        ("오전 3:05에 출발한다", "오전 세시 오분에 출발한다"),
        ("탑승 시간은 24:00이다", "탑승 시간은 이십사시 영분이다"),
    ],
)
def test_hhmm_positive_context_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("한국 vs 일본 3:2", "한국 vs 일본 3:2"),
        ("화면 비율 16:9", "화면 비율 16:9"),
        ("score 12:30", "score 12:30"),
        ("12:30, 14:20, 18:10", "12:30, 14:20, 18:10"),
    ],
)
def test_hhmm_negative_context_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 00:00에 시작한다", "회의는 영시 영분에 시작한다"),
        ("회의는 23:59에 끝난다", "회의는 이십삼시 오십구분에 끝난다"),
        ("회의는 24:01에 끝난다", "회의는 24:01에 끝난다"),
        ("회의는 7:5에 시작한다", "회의는 7:5에 시작한다"),
    ],
)
def test_hhmm_boundary_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:05:09", "세시 오분 구초"),
        ("13:05:09", "십삼시 오분 구초"),
        ("12:30", "12:30"),
        ("0:00", "0:00"),
        ("24:00", "24:00"),
    ],
)
def test_hhmm_standalone_cases(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("기록은 3:05:09이다", "기록은 세시 오분 구초이다"),
        ("기록은 13:05:09이다", "기록은 십삼시 오분 구초이다"),
    ],
)
def test_hhmmss_independent_sentence_cases(text: str, expected: str):
    assert transform_text(text) == expected
