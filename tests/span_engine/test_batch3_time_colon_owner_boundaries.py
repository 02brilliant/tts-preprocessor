from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("오후 2시", "오후 두-시"),
        ("오늘 밤 11시부터", "오늘 밤 열한-시부터"),
        ("13시에는", "십삼-시에는"),
        ("7:05", "일곱시 오분"),
        ("24:00", "이십사시"),
        ("24:01", "이십사시 일분"),
        ("24:09", "이십사시 구분"),
    ],
)
def test_batch3_clock_positive_and_boundary_matrix(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7:5", "칠 대 오"),
        ("16:9", "십육 대 구"),
        ("한국 vs 일본 3:2", "한국 vs 일본 삼 대 이"),
        ("화면 비율 16:9", "화면 비율 십육 대 구"),
    ],
)
def test_batch3_semantic_pair_owner_matrix(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3:05:09",
        "13:05:09",
        "기록은 3:05:09이다",
        "기록은 13:05:09이다",
    ],
)
def test_batch3_timecode_like_multi_colon_preserves_atomically(text: str) -> None:
    output = transform_with_trace(text)
    token = "13:05:09" if "13:05:09" in text else "3:05:09"
    start = text.index(token)

    assert output.normalized_text == text
    assert any(
        claim.owner == "preserve"
        and claim.claim_type == "preserve"
        and claim.surface_type == "RANGE_PRESERVE_SURFACE"
        and claim.reason == "multi_colon_timecode_like_preserve"
        and (claim.span.start, claim.span.end) == (start, start + len(token))
        for claim in output.trace.claim_logs
    )
    assert not any(
        claim.owner in {"time", "colon_semantic_pair"}
        and claim.span.start >= start
        and claim.span.end <= start + len(token)
        for claim in output.trace.claim_logs
    )


def test_batch3_zero_minute_omission_is_owned_by_full_time_claim() -> None:
    text = "회의는 00:00에 시작한다"
    output = transform_with_trace(text)

    assert output.normalized_text == "회의는 영시에 시작한다"
    assert any(
        claim.owner == "time"
        and claim.surface_type == "TIME_SURFACE"
        and (claim.span.start, claim.span.end) == (4, 9)
        for claim in output.trace.claim_logs
    )
    assert not any(piece.text == "영분" for piece in output.render_pieces)


def test_batch3_suffix_clock_spacing_is_generated_by_time_owner() -> None:
    text = "13시에는 문을 닫는다"
    output = transform_with_trace(text)

    assert output.normalized_text == "십삼-시에는 문을 닫는다"
    assert any(
        claim.owner == "time"
        and claim.surface_type == "TIME_SURFACE"
        and claim.reason == "time_hour_korean_context"
        and (claim.span.start, claim.span.end) == (0, 2)
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.owner == "time"
        and piece.provenance == "GENERATED_READING"
        and piece.text == "십삼-"
        for piece in output.render_pieces
    )


@pytest.mark.parametrize(
    "text",
    [
        "https://example.com/a:1",
        "/tmp/a:1",
        '{"time":"13:05:09"}',
        "C:\\tmp\\a:1",
    ],
)
def test_batch3_protected_code_like_colons_do_not_leak_partial_readings(
    text: str,
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == text
    assert not any(
        claim.owner in {"time", "colon_semantic_pair"}
        for claim in output.trace.claim_logs
    )
