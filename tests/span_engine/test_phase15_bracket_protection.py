from __future__ import annotations

from engine.span_engine import transform


def test_bracket_protection_for_hyphen_phone() -> None:
    assert transform("[123-456-7890]") == "123-456-7890"
    assert transform("번호는 [123-456-7890]입니다") == "번호는 123-456-7890입니다"
    assert transform("(123-456-7890)") == ""
    assert transform("번호는 (123-456-7890)입니다") == "번호는 입니다"
    assert transform("[1234-5678]") == "1234-5678"
    assert transform("(1234-5678)") == ""

