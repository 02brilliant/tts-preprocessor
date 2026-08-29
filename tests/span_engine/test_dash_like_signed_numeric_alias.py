from __future__ import annotations

import pytest

from engine.main import transform as canonical_transform
from engine.span_engine import transform, transform_with_trace


def prod(text: str) -> str:
    return canonical_transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-0.11%", "마이너스 영쩜일일-퍼센트"),
        ("–2.03%", "마이너스 이쩜영삼-퍼센트"),
        ("국내채권 –2.03%", "국내채권 마이너스 이쩜영삼-퍼센트"),
        (
            "이 가운데 국내 주식 수익률은 21.67%, 해외 주식 -0.11%, 국내채권 –2.03%, 해외 채권 4.98% 등입니다.",
            "이 가운데 국내 주식 수익률은 이십일쩜육칠-퍼센트, 해외 주식 마이너스 영쩜일일-퍼센트, 국내채권 마이너스 이쩜영삼-퍼센트, 해외 채권 사쩜구팔-퍼센트 등입니다.",
        ),
        ("−2.03%", "마이너스 이쩜영삼-퍼센트"),
        ("－2.03%", "마이너스 이쩜영삼-퍼센트"),
        ("—2.03%", "마이너스 이쩜영삼-퍼센트"),
        ("‒2.03%", "마이너스 이쩜영삼-퍼센트"),
        ("‑2.03%", "마이너스 이쩜영삼-퍼센트"),
        ("–2.03", "마이너스 이쩜영삼"),
        ("–2.03kg", "마이너스 이쩜영삼-킬로그램"),
        ("–2.03℃", "영하 이쩜영삼도"),
        ("–2.5%p", "마이너스 이쩜오-퍼센트포인트"),
    ],
)
def test_dash_like_sign_is_owner_local_signed_numeric_alias(
    text: str, expected: str
) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1–2kg", "일에서 이-킬로그램"),
        ("서울–부산", "서울–부산"),
        ("A–B", "A–B"),
        ("문장 – 부연", "문장 – 부연"),
        ("–2.03abc", "–2.03abc"),
        ("–.5%", "–.5%"),
        ("–1,00.5%", "–1,00.5%"),
        ("–01.5%", "–01.5%"),
        ("––2.03%", "––2.03%"),
        ("/path/–2.03%/log", "/path/–2.03%/log"),
        ("https://example.com?q=–2.03%", "https://example.com?q=–2.03%"),
        ('{"rate":"–2.03%"}', '{"rate":"–2.03%"}'),
        ("`–2.03%`", "`–2.03%`"),
        ("[–2.03%]", "–2.03%"),
    ],
)
def test_dash_like_sign_preserves_ranges_connectors_invalid_and_protected(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_dash_like_signed_percent_full_claims_source_span() -> None:
    output = transform_with_trace("–2.03%")

    assert output.normalized_text == "마이너스 이쩜영삼-퍼센트"
    assert [(claim.owner, claim.span.start, claim.span.end) for claim in output.trace.claim_logs] == [
        ("simple_unit", 0, 6)
    ]
    assert [(piece.text, piece.provenance) for piece in output.render_pieces] == [
        ("마이너스 이쩜영삼-퍼센트", "GENERATED_READING")
    ]
