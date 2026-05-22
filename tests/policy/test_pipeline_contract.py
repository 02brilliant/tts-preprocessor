from engine.main import transform
from engine.pipeline.transform_engine import transform_text


def test_transform_text_stops_before_prosody():
    text = "그리고 우리는 13:05에 출발한다"
    assert transform_text(text) == "그리고 우리는 십삼시 오분에 출발한다"


def test_transform_applies_prosody_after_normalization_and_phonetic():
    text = "그리고 우리는 13:05에 출발한다"
    assert transform(text) == "그리고, 우리는 십삼시 오분에 출발한다"


def test_transform_text_returns_bracket_processed_text_only_once():
    text = "(비공개) [중요] 일정은 2026-04-17이다"
    assert transform_text(text) == "중요 일정은 이천이십육년 사월 십칠일이다"
