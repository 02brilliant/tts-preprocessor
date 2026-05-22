from __future__ import annotations

from engine.span_engine import transform


def test_phase18a_existing_punctuation_is_preserved() -> None:
    assert transform("안녕하세요, 반갑습니다.") == "안녕하세요, 반갑습니다."
    assert transform("안녕하세요 , 반갑습니다") == "안녕하세요 , 반갑습니다"
    assert transform("KBS 오후 10시 뉴스입니다.") == "케이비에스 오후 열 시 뉴스입니다."


def test_phase18a_no_new_comma_or_newline_before_adapter() -> None:
    text = "오늘 우리는 새로운 시스템을 테스트하고 결과를 확인합니다"
    output = transform(text)

    assert output == text
    assert "," not in output
    assert "\n" not in output


def test_phase18a_no_paragraph_split_before_adapter() -> None:
    text = "첫 번째 문장입니다. 두 번째 문장입니다."
    output = transform(text)

    assert output == text
    assert "\n" not in output
