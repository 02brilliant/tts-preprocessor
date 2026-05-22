from __future__ import annotations

import re

import pytest

from engine.pipeline import transform_engine
from engine.pipeline.transform_engine import normalize_text, transform_text
from engine.prosody.comma import insert_commas


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("전문가", "전문가"),
        ("있는", "있는"),
        ("하지만", "하지만"),
        ("있습니다", "있습니다"),
    ],
)
def test_korean_text_immutability(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("전문 가", "전문 가"),
        ("이 억", "이 억"),
        ("전문  가", "전문  가"),
        ("이  억", "이  억"),
    ],
)
def test_spacing_preservation_between_hangul_tokens(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안녕하세요.", "안녕하세요."),
        ("안녕하세요,", "안녕하세요,"),
        ("하지만,", "하지만,"),
        ("있습니다,", "있습니다,"),
        ("안녕하세요 , 반갑습니다", "안녕하세요 , 반갑습니다"),
        ("하지만 , 우리는 간다", "하지만 , 우리는 간다"),
    ],
)
def test_punctuation_preservation_after_hangul(text: str, expected: str):
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FTA은", "에프티에이은"),
        ("AI이", "에이아이이"),
        ("FTA으로", "에프티에이으로"),
        ("AI과", "에이아이과"),
        ("유로을", "유로을"),
        ("엔로", "엔로"),
        ("배럴으로", "배럴으로"),
        ("알으로", "알으로"),
    ],
)
def test_particle_preservation(text: str, expected: str):
    assert transform_text(text) == expected


def test_postprocessing_does_not_receive_hangul_plain_segments(monkeypatch: pytest.MonkeyPatch):
    seen: list[str] = []
    original = transform_engine._fix_numeric_postpositions

    def guarded(text: str) -> str:
        seen.append(text)
        assert re.search(r"[가-힣]", text) is None, text
        return original(text)

    monkeypatch.setattr(transform_engine, "_fix_numeric_postpositions", guarded)

    normalize_text("전문가 유로을 AI가 FTA은")
    assert seen


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안녕하세요, 그리고 갑니다", "안녕하세요, 그리고 갑니다"),
        ("있습니다, 그러나 진행합니다", "있습니다, 그러나 진행합니다"),
        ("하지만, 우리는 간다", "하지만, 우리는 간다"),
    ],
)
def test_prosody_preserves_existing_punctuation(text: str, expected: str):
    assert insert_commas(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("FTA은", "에프티에이는"),
        ("AI이", "에이아이가"),
        ("유로을", "유로를"),
        ("엔로", "엔으로"),
        ("배럴으로", "배럴로"),
        ("알으로", "알로"),
        ("전문  가", "전문 가"),
        ("안녕하세요 , 반갑습니다", "안녕하세요, 반갑습니다"),
    ],
)
def test_forbidden_core_invariance_regressions(text: str, forbidden: str):
    assert transform_text(text) != forbidden
