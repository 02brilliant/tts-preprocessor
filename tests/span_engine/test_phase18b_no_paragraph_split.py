from __future__ import annotations

from engine.span_engine import transform


def test_phase18b_short_text_has_no_paragraph_newline() -> None:
    output = transform("그리고 우리는 결과를 확인했다. 다음 문장을 계속 확인했다")

    assert "\n" not in output
    assert output == "그리고, 우리는 결과를 확인했다. 다음 문장을 계속 확인했다"


def test_phase18b_short_multi_sentence_paragraph_has_no_newline() -> None:
    output = transform("첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.")

    assert "\n" not in output
    assert output == "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
