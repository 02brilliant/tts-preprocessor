from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "유로을 입력했다",
        "엔로 보냈다",
        "배럴으로 계산",
        "알으로 계산",
        "전문가은 말했다",
        "사과을 먹었다",
    ],
)
def test_original_korean_followed_by_particle_is_not_corrected(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("유로을 입력했다", "유로를 입력했다"),
        ("엔로 보냈다", "엔으로 보냈다"),
        ("배럴으로 계산", "배럴로 계산"),
        ("전문가은 말했다", "전문가는 말했다"),
    ],
)
def test_broad_josa_correction_signatures_do_not_appear(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
