from __future__ import annotations

import pytest

from engine.main import transform_with_rollout


def prod(text: str) -> str:
    return transform_with_rollout(text, mode="span_default", include_debug=False)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("`3:4테스트`", "`3:4테스트`"),
        ('{"ratio":"3:4테스트"}', '{"ratio":"3:4테스트"}'),
        ("/path/3:4/log", "/path/3:4/log"),
        ("https://example.com?q=3:4테스트", "https://example.com?q=3:4테스트"),
        ("line 1:23", "line 1:23"),
        ("case 1:23", "case 1:23"),
        ("version 1:23", "version 1:23"),
        ("file 1:23", "file 1:23"),
        ("요한복음 3:16", "요한복음 3:16"),
    ],
)
def test_colon_protected_contexts_precede_broad_nm_claims(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:30", "영시 삼십분"),
        ("01:40", "한시 사십분"),
        ("09:30", "구시 삼십분"),
        ("3:04", "세시 사분"),
        ("13:05", "십삼시 오분"),
        ("24:09", "이십사시 구분"),
    ],
)
def test_strong_time_like_without_context_reads_as_time(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3:40",
        "13:40",
        "24:50",
    ],
)
def test_ambiguous_time_like_without_context_currently_preserves(text: str) -> None:
    assert prod(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:40에", "세시 사십분에"),
        ("24:50까지", "이십사시 오십분까지"),
    ],
)
def test_ambiguous_time_like_with_time_context_reads_as_time(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3:40 비율", "삼 대 사십 비율"),
        ("13:40 스코어", "십삼 대 사십 스코어"),
    ],
)
def test_ambiguous_time_like_ratio_score_context_reads_as_dae(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25:30", "이십오 대 삼십"),
        ("3:4", "삼 대 사"),
        ("13:5", "십삼 대 오"),
        ("1:234", "일 대 이백삼십사"),
        ("123:45", "백이십삼 대 사십오"),
    ],
)
def test_non_time_like_nm_fallback_current_policy(text: str, expected: str) -> None:
    assert prod(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "+01:2",
        "+1.:2",
        "+.5:2",
        "1,00:2",
        "01:2:3",
        "1:+2.:3",
        "1,00:2:3",
    ],
)
def test_invalid_colon_surfaces_preserve_without_partial_fallback(text: str) -> None:
    assert prod(text) == text
