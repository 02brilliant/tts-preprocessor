from __future__ import annotations

from engine.span_engine import transform


def test_phone_route_4_4_expected_output() -> None:
    assert transform("1234-5678") == "일이삼사 오육칠팔"
    assert transform("전화 1234-5678입니다") == "전화 일이삼사 오육칠팔입니다"

