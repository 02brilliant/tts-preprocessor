from engine.main import transform
from engine.span_engine.transform import transform_with_trace


def test_transform_applies_prosody_after_normalization_and_phonetic():
    text = "그리고 우리는 13:05에 출발한다"
    assert transform(text) == "그리고, 우리는 십삼시 오분에 출발한다"

    output = transform_with_trace(text)
    assert output.normalized_text == transform(text)
    assert any(
        log.action == "insert_generated_punct"
        for log in output.trace.prosody_logs
    )


def test_transform_returns_bracket_processed_text_only_once():
    text = "(비공개) [중요] 일정은 2026-04-17이다"
    assert transform(text) == "중요 일정은 이천이십육년 사월 십칠일이다"
