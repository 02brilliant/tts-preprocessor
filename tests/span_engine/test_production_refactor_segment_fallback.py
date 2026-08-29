from __future__ import annotations

import importlib

import pytest

from engine.span_engine import RenderPiece, SourceSpan
from engine.span_engine.trace import output_to_debug_dict, trace_log_entry_to_dict


def _install_selective_core_failure(monkeypatch: pytest.MonkeyPatch):
    transform_module = importlib.import_module("engine.span_engine.transform")
    original_core = transform_module._transform_core_with_trace
    calls: list[str] = []

    def fail_selected(text: str):
        calls.append(text)
        if "FAIL" in text:
            raise RuntimeError(f"selected failure:{text}")
        return original_core(text)

    monkeypatch.setattr(transform_module, "_transform_core_with_trace", fail_selected)
    return transform_module, calls


@pytest.mark.parametrize(
    ("text", "expected", "failed_tokens"),
    [
        ("FAIL앞 45m²", "FAIL앞 사십오-제곱미터", ["FAIL앞"]),
        ("45m² FAIL중 60Hz", "사십오-제곱미터 FAIL중 육십-헤르츠", ["FAIL중"]),
        ("45m² FAIL끝", "사십오-제곱미터 FAIL끝", ["FAIL끝"]),
        ("FAIL하나 FAIL둘 3kg", "FAIL하나 FAIL둘 삼-킬로그램", ["FAIL하나", "FAIL둘"]),
    ],
)
def test_segment_fallback_preserves_only_ordered_failed_subsegments(
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    expected: str,
    failed_tokens: list[str],
) -> None:
    transform_module, _ = _install_selective_core_failure(monkeypatch)

    output = transform_module.transform_with_trace(text)
    failures = output.trace.fallback_logs[0].metadata["segment_failures"]

    assert output.normalized_text == expected
    assert failures == [
        {
            "start": text.index(token),
            "end": text.index(token) + len(token),
            "error_type": "RuntimeError",
            "error_message": f"selected failure:{token}",
        }
        for token in failed_tokens
    ]
    assert [piece.text for piece in output.render_pieces if piece.text in failed_tokens] == failed_tokens
    assert all(
        piece.provenance == "ORIGINAL_BOUNDARY"
        for piece in output.render_pieces
        if piece.text in failed_tokens
    )


def test_segment_fallback_keeps_exact_piece_and_trace_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transform_module, _ = _install_selective_core_failure(monkeypatch)
    text = "FAIL앞 45m² 정상 FAIL뒤 60Hz 자료"

    output = transform_module.transform_with_trace(text)
    piece_rows = [
        (
            piece.text,
            piece.provenance,
            None
            if piece.source_span is None
            else (piece.source_span.start, piece.source_span.end),
            piece.owner,
            piece.metadata,
        )
        for piece in output.render_pieces
    ]

    assert output.normalized_text == "FAIL앞 사십오-제곱미터 정상 FAIL뒤 육십-헤르츠 자료"
    assert piece_rows == [
        ("FAIL앞", "ORIGINAL_BOUNDARY", (0, 5), None, {}),
        (" ", "ORIGINAL_BOUNDARY", (5, 6), None, {}),
        (
            "사십오-제곱미터",
            "GENERATED_READING",
            (6, 10),
            "special_unit",
            {"surface_type": "SPECIAL_UNIT_SURFACE"},
        ),
        (" ", "ORIGINAL_BOUNDARY", (10, 11), None, {}),
        ("정상", "ORIGINAL_KOREAN", (11, 13), None, {}),
        (" ", "ORIGINAL_BOUNDARY", (13, 14), None, {}),
        ("FAIL뒤", "ORIGINAL_BOUNDARY", (14, 19), None, {}),
        (" ", "ORIGINAL_BOUNDARY", (19, 20), None, {}),
        (
            "육십-헤르츠",
            "GENERATED_READING",
            (20, 24),
            "simple_unit",
            {"surface_type": "SIMPLE_UNIT_SURFACE"},
        ),
        (" ", "ORIGINAL_BOUNDARY", (24, 25), None, {}),
        ("자료", "ORIGINAL_KOREAN", (25, 27), None, {}),
    ]
    assert [trace_log_entry_to_dict(log) for log in output.trace.fallback_logs] == [
        {
            "stage": "fallback",
            "event": "blocked_whole_input_fallback_for_hangul_input",
            "span": {"start": 0, "end": 27, "length": 27},
            "raw": text,
            "owner": None,
            "surface_type": None,
            "decision": "blocked",
            "reason": "hangul_input_whole_fallback_prohibited",
            "action": "segment_fallback",
            "provenance": None,
            "expected": None,
            "actual": None,
            "metadata": {
                "status": "segment_fallback",
                "fallback_stage": "transform_with_trace",
                "fallback_reason": "RuntimeError",
                "fallback_error_message": f"selected failure:{text}",
                "fallback_span": [0, 27],
                "fallback_raw": text,
                "whole_input_fallback_attempted": True,
                "whole_input_fallback_allowed": False,
                "blocked_whole_input_fallback_for_hangul_input": True,
                "segment_failures": [
                    {
                        "start": 0,
                        "end": 5,
                        "error_type": "RuntimeError",
                        "error_message": "selected failure:FAIL앞",
                    },
                    {
                        "start": 14,
                        "end": 19,
                        "error_type": "RuntimeError",
                        "error_message": "selected failure:FAIL뒤",
                    },
                ],
                "segment_recoveries": [
                    {"start": 5, "end": 6, "status": "preserved_boundary"},
                    {"start": 6, "end": 10, "status": "recovered"},
                    {"start": 10, "end": 11, "status": "preserved_boundary"},
                    {"start": 11, "end": 13, "status": "recovered"},
                    {"start": 13, "end": 14, "status": "preserved_boundary"},
                    {"start": 19, "end": 20, "status": "preserved_boundary"},
                    {"start": 20, "end": 24, "status": "recovered"},
                    {"start": 24, "end": 25, "status": "preserved_boundary"},
                    {"start": 25, "end": 27, "status": "recovered"},
                ],
            },
        }
    ]
    assert output.trace.parser_logs == []
    assert output.trace.render_logs == []
    assert output.trace.validation_logs == []


def test_sentence_retry_preserves_generated_punctuation_none_span_and_call_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transform_module, calls = _install_selective_core_failure(monkeypatch)
    text = "그리고 우리는 확인했다. FAIL구간 자료 60Hz"

    output = transform_module.transform_with_trace(text)
    generated_comma = next(
        piece
        for piece in output.render_pieces
        if piece.text == "," and piece.owner == "prosody"
    )

    assert output.normalized_text == "그리고, 우리는 확인했다. FAIL구간 자료 육십-헤르츠"
    assert generated_comma.provenance == "GENERATED_PUNCT"
    assert generated_comma.source_span is None
    assert calls == [
        text,
        "그리고 우리는 확인했다. ",
        "FAIL구간 자료 60Hz",
        "FAIL구간",
        "자료",
        "60Hz",
    ]
    assert output.trace.fallback_logs[0].metadata["segment_recoveries"] == [
        {"start": 0, "end": 14, "status": "recovered"},
        {"start": 20, "end": 21, "status": "preserved_boundary"},
        {"start": 21, "end": 23, "status": "recovered"},
        {"start": 23, "end": 24, "status": "preserved_boundary"},
        {"start": 24, "end": 28, "status": "recovered"},
    ]


def test_paragraph_split_runs_after_segment_piece_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transform_module, _ = _install_selective_core_failure(monkeypatch)
    text = "45m² 정상.\nFAIL구간 자료.\n60Hz 정상"

    output = transform_module.transform_with_trace(text)

    assert output.normalized_text == (
        "사십오-제곱미터 정상.\n\nFAIL구간 자료.\n\n육십-헤르츠 정상"
    )
    assert "".join(piece.text for piece in output.render_pieces) == (
        "사십오-제곱미터 정상.\nFAIL구간 자료.\n육십-헤르츠 정상"
    )
    assert output.trace.fallback_logs[0].span == SourceSpan(0, len(text))
    assert all(
        piece.source_span is None
        or 0 <= piece.source_span.start <= piece.source_span.end <= len(text)
        for piece in output.render_pieces
    )


def test_protected_subsegments_do_not_reenter_owners_during_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transform_module, _ = _install_selective_core_failure(monkeypatch)
    text = '문서 {"text":"25℃"} [3kg] `60Hz` FAIL구간 45m² 자료'

    output = transform_module.transform_with_trace(text)

    assert output.normalized_text == (
        '문서 {"text":"25℃"} 3kg `60Hz` FAIL구간 사십오-제곱미터 자료'
    )
    assert any(piece.text == '"25℃"' and piece.owner is None for piece in output.render_pieces)
    assert any(piece.text == "3kg" and piece.owner is None for piece in output.render_pieces)
    assert any(piece.text == "`60Hz`" and piece.owner is None for piece in output.render_pieces)
    assert any(
        piece.text == "사십오-제곱미터" and piece.owner == "special_unit"
        for piece in output.render_pieces
    )


def test_no_hangul_recovery_keeps_exact_whole_preserve_debug_shape() -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")

    output = transform_module.recover_transform_output(
        "ASCII only", ValueError("outer failure")
    )
    debug = output_to_debug_dict(output)

    assert output.normalized_text == "ASCII only"
    assert debug["render_pieces"] == [
        {
            "text": "ASCII only",
            "provenance": "ORIGINAL_BOUNDARY",
            "source_span": {"start": 0, "end": 10, "length": 10},
            "owner": None,
            "metadata": {},
        }
    ]
    assert debug["trace"]["fallback_logs"] == [
        {
            "stage": "fallback",
            "event": "whole_input_preserve_allowed",
            "span": {"start": 0, "end": 10, "length": 10},
            "raw": "ASCII only",
            "owner": None,
            "surface_type": None,
            "decision": "preserve",
            "reason": "global_no_hangul_bypass",
            "action": "preserve_original",
            "provenance": None,
            "expected": None,
            "actual": None,
            "metadata": {
                "status": "whole_input_preserve",
                "fallback_reason": "ValueError",
                "error_message": "outer failure",
            },
        }
    ]


def test_absolute_preserve_and_blocked_whole_preserve_keep_exception_contract() -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")
    absolute = RuntimeError("absolute")

    output = transform_module._whole_input_preserve_output(
        "전체보존", absolute, reason="whole_input_absolute_preserve"
    )

    assert output.normalized_text == "전체보존"
    assert output.trace.fallback_logs[0].reason == "whole_input_absolute_preserve"
    assert output.trace.fallback_logs[0].metadata == {
        "status": "whole_input_preserve",
        "fallback_reason": "RuntimeError",
        "error_message": "absolute",
    }

    blocked = RuntimeError("same object")
    with pytest.raises(RuntimeError) as exc_info:
        transform_module._whole_input_preserve_output(
            "한글", blocked, reason="global_no_hangul_bypass"
        )
    assert exc_info.value is blocked


def test_segment_boundaries_and_piece_offset_are_exact_private_primitives() -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")
    text = "첫 문장. 둘째 문장!\n셋째"

    assert transform_module._fallback_segments(text) == [(0, 6), (6, 13), (13, 15)]
    assert transform_module._fallback_segments("") == [(0, 0)]
    assert transform_module._fallback_subsegments("가  나\n다", 0, 6) == [
        (0, 1),
        (1, 3),
        (3, 4),
        (4, 5),
        (5, 6),
    ]

    nested: list[str] = []
    metadata = {"surface_type": "TEST", "nested": nested}
    shifted = transform_module._offset_render_piece(
        RenderPiece(
            "생성",
            "GENERATED_READING",
            SourceSpan(1, 3),
            owner="test",
            metadata=metadata,
        ),
        5,
    )
    unmapped = transform_module._offset_render_piece(
        RenderPiece(",", "GENERATED_PUNCT", None, owner="prosody"), 5
    )

    assert shifted.source_span == SourceSpan(6, 8)
    assert shifted.metadata == metadata
    assert shifted.metadata is not metadata
    assert shifted.metadata["nested"] is nested
    assert unmapped.source_span is None

