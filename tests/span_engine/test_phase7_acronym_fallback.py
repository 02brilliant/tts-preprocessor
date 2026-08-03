from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ABC", "에이비씨"),
        ("XYZ", "엑스와이지"),
        ("NLP", "엔엘피"),
        ("OSP", "오에스피"),
        ("원익IPS는", "원익아이피에스는"),
        ("AB는", "에이비는"),
    ],
)
def test_safe_uppercase_acronym_fallback(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["A", "OpenAI", "USB3", "mL", "km", "AI3", "abc"])
def test_acronym_fallback_preserves_unsafe_tokens(text: str) -> None:
    assert transform(text) == text


def test_two_block_hyphen_code_handles_single_letter_prefix() -> None:
    assert transform("A-1") == "에이 원"


def test_dictionary_owner_wins_before_acronym_fallback() -> None:
    output = transform_with_trace("JSON")

    assert output.normalized_text == "제이슨"
    assert any(claim.owner == "dictionary" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "acronym_fallback" for claim in output.trace.claim_logs)


def test_embedded_short_dictionary_entry_does_not_block_full_acronym_fallback() -> None:
    output = transform_with_trace("OSP")

    assert output.normalized_text == "오에스피"
    assert any(claim.owner == "acronym_fallback" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "dictionary" for claim in output.trace.claim_logs)


def test_financial_news_acronyms_do_not_remain_unread() -> None:
    source = (
        "에쓰오일은 원유 대부분을 사우디아라비아에서 조달하고 있어 OSP 하락이 마진 개선으로 연결된다. "
        "8월 선적분 OSP는 전월보다 배럴당 11달러 낮아져 역대 최대 인하 폭을 기록했다.\n"
        "원익IPS는 오늘 5.2% 상승했다"
    )

    assert transform(source) == (
        "에쓰오일은 원유 대부분을 사우디아라비아에서 조달하고 있어 오에스피 하락이 마진 개선으로 연결된다. "
        "팔월 선적분 오에스피는 전월보다 배럴당 십일 달러 낮아져 역대 최대 인하 폭을 기록했다.\n\n"
        "원익아이피에스는 오늘 오쩜이 퍼센트 상승했다"
    )
