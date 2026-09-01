from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시", "세-시"),
        ("3시에 시작", "세-시에 시작"),
        ("3시 5분", "세-시 오분"),
        ("3시 5분 7초", "세-시 오분 칠초"),
        ("오후 3시", "오후 세-시"),
        ("오전 10시 30분", "오전 열-시 삼십분"),
        ("12시", "열두-시"),
        ("12시에", "열두-시에"),
        ("12시를", "열두-시를"),
        ("12시을", "열두-시을"),
        ("12시는", "열두-시는"),
        ("12시은", "열두-시은"),
        ("12시가", "열두-시가"),
        ("12시이", "열두-시이"),
        ("12시로", "열두-시로"),
        ("12시으로", "열두-시으로"),
        ("12시와", "열두-시와"),
        ("12시과", "열두-시과"),
        ("12시도", "열두-시도"),
        ("12시만", "열두-시만"),
        ("12시보다 늦게", "열두-시보다 늦게"),
        ("12시처럼 보인다", "열두-시처럼 보인다"),
        ("12시마다 알림", "열두-시마다 알림"),
        ("12시면 늦다", "열두-시면 늦다"),
        ("12시이면", "열두-시이면"),
        ("12시라면", "열두-시라면"),
        ("12시이라고 했다", "열두-시이라고 했다"),
        ("12시라고 했다", "열두-시라고 했다"),
        ("12시인데", "열두-시인데"),
        ("12시였다", "열두-시였다"),
        ("12시이었다", "열두-시이었다"),
        ("12시이다", "열두-시이다"),
        ("12시에는", "열두-시에는"),
        ("12시에서", "열두-시에서"),
        ("12시에도", "열두-시에도"),
        ("12시보다", "열두-시보다"),
        ("12시인", "열두-시인"),
    ],
)
def test_korean_hour_time(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11시23분", "열한-시 이십삼분"),
        ("11시 23분", "열한-시 이십삼분"),
        ("11시23분45초", "열한-시 이십삼분 사십오초"),
        ("11시 23분45초", "열한-시 이십삼분 사십오초"),
        ("11시23분 45초", "열한-시 이십삼분 사십오초"),
        ("11시 23분 45초", "열한-시 이십삼분 사십오초"),
        ("1시2분3초", "한-시 이분 삼초"),
        ("23시59분59초", "이십삼-시 오십구분 오십구초"),
        ("23분45초", "이십삼분 사십오초"),
        ("23분 45초", "이십삼분 사십오초"),
        ("11시60분", "열한-시 육십분"),
        ("11시23분60초", "열한-시 이십삼분 육십초"),
        ("60분45초", "육십분 사십오초"),
        ("23분60초", "이십삼분 육십초"),
        ("120분45초", "백이십분 사십오초"),
        ("1,200분45초", "천이백분 사십오초"),
        ("3시 99분", "세-시 구십구분"),
        ("3시5분99초", "세-시 오분 구십구초"),
        ("11시23분45초입니다", "열한-시 이십삼분 사십오초입니다"),
        ("23분45초입니다", "이십삼분 사십오초입니다"),
        ("09시", "아홉-시"),
        ("009시", "아홉-시"),
        ("09 시", "09 시"),
        ("0시", "영-시"),
        ("00시", "영-시"),
        ("00시23분45초", "영-시 이십삼분 사십오초"),
        ("09시23분", "아홉-시 이십삼분"),
        ("09시 23분45초", "아홉-시 이십삼분 사십오초"),
        ("09시23분 045초", "아홉-시 이십삼분 사십오초"),
        ("11시005분", "열한-시 오분"),
        ("23분045초", "이십삼분 사십오초"),
        ("123분545초", "백이십삼분 오백사십오초"),
        ("01.5분", "01.5분"),
        ('01.5초', '일쩜오-초'),
    ],
)
def test_korean_time_compact_and_mixed_spacing(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "A11시23분45초",
        "11시23분45초abc",
        "23분45초abc",
        "`11시23분45초`",
        "/11시23분45초/log",
        "https://example.com/11시23분45초",
        '{"time":"11시23분45초"}',
        "23분045초abc",
        "23분045초/log",
        "23분1,00초",
        "23분1..2초",
        "3분개발",
        "3초개발",
    ],
)
def test_compact_korean_time_protected_or_unsafe_surface_preserves(
    text: str,
) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("낮 12시를 기준", "낮 열두-시를 기준"),
        ("낮 12시는 기준", "낮 열두-시는 기준"),
        ("낮 12시가 기준", "낮 열두-시가 기준"),
        ("낮 12시로 기준", "낮 열두-시로 기준"),
        ("낮 12시면 늦다", "낮 열두-시면 늦다"),
        ("오전 12시를 기준", "오전 열두-시를 기준"),
        ("오후 3시는 어렵다", "오후 세-시는 어렵다"),
        ("밤 10시면 늦다", "밤 열-시면 늦다"),
        ("새벽 2시라고 했다", "새벽 두-시라고 했다"),
    ],
)
def test_korean_hour_time_safe_context_tail(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시리즈", "삼-시리즈"),
        ("A3시", "A3시"),
        ("3시abc", "3시abc"),
        ("99시", "구십구 시"),
        ("99시23분45초", "99시23분45초"),
        ("12시리즈", "십이-시리즈"),
        ("12시스템", "십이 시스템"),
        ("12시장", "십이 시장"),
        ("12시험", "십이 시험"),
        ("12시즌", "십이 시즌"),
        ("12시abc", "12시abc"),
        ("낮 12시리즈", "낮 십이-시리즈"),
        ("낮 12시스템", "낮 십이 시스템"),
        ("낮 12시장", "낮 십이 시장"),
        ("낮 12시험", "낮 십이 시험"),
        ("낮 12시즌", "낮 십이 시즌"),
        ("낮 12시abc", "낮 12시abc"),
    ],
)
def test_invalid_or_attached_korean_time_preserve(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_korean_hour_time_safe_tail_trace() -> None:
    output = transform_with_trace("낮 12시를 기준")

    assert output.normalized_text == "낮 열두-시를 기준"
    assert any(
        claim.owner == "time" and claim.reason == "time_hour_korean_context"
        for claim in output.trace.claim_logs
    )
    assert not any(
        claim.reason == "attached_korean_time_preserve"
        for claim in output.trace.claim_logs
    )
    assert output.trace.particle_exception_logs == []


def test_korean_time_markers_remain_original_korean() -> None:
    output = transform_with_trace("3시 5분")

    assert output.normalized_text == "세-시 오분"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("세-", "GENERATED_READING", SourceSpan(0, 1), "time"),
        ("시", "ORIGINAL_KOREAN", SourceSpan(1, 2), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(2, 3), None),
        ("오", "GENERATED_READING", SourceSpan(3, 4), "time"),
        ("분", "ORIGINAL_KOREAN", SourceSpan(4, 5), None),
    ]


def test_compact_korean_time_is_fully_owned_without_suffix_fallback() -> None:
    output = transform_with_trace("11시23분 45초")

    assert output.normalized_text == "열한-시 이십삼분 사십오초"
    assert [
        (claim.owner, claim.reason, claim.span)
        for claim in output.trace.claim_logs
        if claim.owner == "time"
    ] == [
        ("time", "time_hour_korean_context", SourceSpan(0, 2)),
        ("time", "time_minute_korean_context", SourceSpan(3, 5)),
        ("time", "time_second_korean_context", SourceSpan(7, 9)),
    ]
    assert not any(
        claim.owner in {"numeric_suffix", "number"}
        for claim in output.trace.claim_logs
    )
    assert all(log.passed for log in output.trace.validation_logs)


def test_compact_minute_second_is_fully_owned_by_time() -> None:
    output = transform_with_trace("23분45초")

    assert output.normalized_text == "이십삼분 사십오초"
    assert [
        (claim.owner, claim.reason, claim.span)
        for claim in output.trace.claim_logs
        if claim.owner == "time"
    ] == [
        ("time", "time_minute_korean_compound", SourceSpan(0, 2)),
        ("time", "time_second_korean_compound", SourceSpan(3, 5)),
    ]
    assert not any(
        claim.owner in {"numeric_suffix", "number"}
        for claim in output.trace.claim_logs
    )
    assert all(log.passed for log in output.trace.validation_logs)


def test_compact_korean_time_generated_boundaries_keep_original_markers() -> None:
    output = transform_with_trace("11시23분45초")

    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("열한-", "GENERATED_READING", SourceSpan(0, 2), "time"),
        ("시", "ORIGINAL_KOREAN", SourceSpan(2, 3), None),
        (" 이십삼", "GENERATED_READING", SourceSpan(3, 5), "time"),
        ("분", "ORIGINAL_KOREAN", SourceSpan(5, 6), None),
        (" 사십오", "GENERATED_READING", SourceSpan(6, 8), "time"),
        ("초", "ORIGINAL_KOREAN", SourceSpan(8, 9), None),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_leading_zero_suffix_time_uses_one_owner_and_common_sino_reader() -> None:
    output = transform_with_trace("09시23분045초")

    assert output.normalized_text == "아홉-시 이십삼분 사십오초"
    assert [
        (claim.owner, claim.reason, claim.span)
        for claim in output.trace.claim_logs
    ] == [
        ("time", "time_hour_korean_context", SourceSpan(0, 2)),
        ("time", "time_minute_korean_context", SourceSpan(3, 5)),
        ("time", "time_second_korean_context", SourceSpan(6, 9)),
    ]
    assert not any(
        claim.owner in {"duration", "numeric_suffix", "counter_noun", "number"}
        for claim in output.trace.claim_logs
    )
    assert all(log.passed for log in output.trace.validation_logs)


@pytest.mark.parametrize(
    "text",
    [
        "23분045초abc",
        "23분045초/log",
        "23분1,00초",
        "23분1..2초",
        "3분개발",
        "3초개발",
    ],
)
def test_unsafe_or_malformed_suffix_time_blocks_partial_fallback(
    text: str,
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert not any(
        claim.owner in {"duration", "numeric_suffix", "counter_noun", "number"}
        for claim in output.trace.claim_logs
    )
    assert all(log.passed for log in output.trace.validation_logs)


def test_out_of_range_hour_compound_preserves_all_numeric_groups() -> None:
    output = transform_with_trace("99시23분45초")

    assert output.normalized_text == "99시23분45초"
    assert all(
        claim.owner == "time"
        and claim.reason == "invalid_korean_time_preserve"
        for claim in output.trace.claim_logs
    )
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)
    assert all(log.passed for log in output.trace.validation_logs)


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("1 시", "일 시", "number"),
        ("3 시", "삼 시", "number"),
        ("09 시", "09 시", None),
        ("3 시간", "삼 시간", "number"),
        ("13 시간", "십삼 시간", "number"),
        ("09 시간", "09 시간", None),
    ],
)
def test_spaced_hour_suffix_uses_ordinary_number_policy(
    text: str, expected: str, owner: str | None
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert not any(
        claim.owner in {"time", "duration", "counter_noun"}
        for claim in output.trace.claim_logs
    )
    if owner is not None:
        assert [claim.owner for claim in output.trace.claim_logs] == [owner]
    else:
        assert output.trace.claim_logs == []
    assert all(log.passed for log in output.trace.validation_logs)
