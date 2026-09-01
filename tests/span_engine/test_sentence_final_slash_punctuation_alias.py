from __future__ import annotations

import pytest

from engine.main import transform, transform_debug
from engine.span_engine.models import SourceSpan
from engine.span_engine.transform import transform_with_trace


def production_transform(text: str) -> str:
    return transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안녕하세요/", "안녕하세요."),
        ("안녕하세요//", "안녕하세요."),
        ("안녕하세요///", "안녕하세요."),
        ("오늘 온도는 25℃입니다/", "오늘 온도는 이십오도입니다."),
        ("KBS 11시뉴스입니다//", "케이비에스 열한시뉴스입니다."),
    ],
)
def test_sentence_final_slash_alias_positive_production_path(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected


def test_sentence_final_slash_alias_line_ending_uses_existing_paragraph_policy() -> None:
    text = "안녕하세요/\n다음 문장입니다//"
    expected = "안녕하세요.\n\n다음 문장입니다."
    assert production_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/a//b", "https://example.com/a//b"),
        ("/path/to/file//", "/path/to/file//"),
        ("`안녕하세요/`", "`안녕하세요/`"),
        ('{"text":"안녕하세요/"}', '{"text":"안녕하세요/"}'),
        ("[안녕하세요/]", "안녕하세요/"),
        ("1/3", "삼분의 일"),
        ("2026/06/01", "이천이십육년 유월 일일"),
        ('15.2km/L', '리터당 십오쩜이 킬로미터'),
        ("A / B", "A / B"),
    ],
)
def test_sentence_final_slash_alias_preserves_existing_slash_policies(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안녕하세요/반갑습니다", "안녕하세요/반갑습니다"),
        ("문장 / 다음", "문장 / 다음"),
    ],
)
def test_sentence_final_slash_alias_does_not_apply_to_middle_slash(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected


def test_sentence_final_slash_alias_uses_generated_punct_source_span() -> None:
    output = transform_with_trace("안녕하세요///")
    slash_piece = next(
        piece for piece in output.render_pieces if piece.owner == "sentence_final_slash"
    )

    assert slash_piece.text == "."
    assert slash_piece.provenance == "GENERATED_PUNCT"
    assert slash_piece.source_span == SourceSpan(5, 8)
    assert slash_piece.metadata["reason"] == "sentence_final_slash"


def test_sentence_final_slash_alias_debug_trace_records_reason() -> None:
    output = transform_debug("안녕하세요//")
    render_logs = output["debug"]["trace"]["render_logs"]

    assert any(
        log["event"] == "sentence_final_slash_alias_applied"
        and log["reason"] == "sentence_final_slash"
        and log["raw"] == "//"
        and log["provenance"] == "GENERATED_PUNCT"
        for log in render_logs
    )
