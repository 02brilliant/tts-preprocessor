from __future__ import annotations

from engine.main import transform as legacy_transform
from engine.span_engine import transform as span_transform


def test_legacy_entrypoint_remains_callable_for_smoke_cases() -> None:
    for text in [
        "",
        "안녕하세요",
        "AI는 123입니다",
        "회의는 13:05에 시작한다",
    ]:
        result = legacy_transform(text)
        assert isinstance(result, str)


def test_span_engine_and_legacy_entrypoints_are_distinct_callables() -> None:
    assert span_transform is not legacy_transform
    assert span_transform("AI") == "에이아이"
