from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    "text",
    [
        "연구팀 운영 계획은 이번 분기부터 전면 조정된다",
        "대외 협력 운영 방안은 이후 단계에서 다시 검토된다",
        "한편 마지막 설명은 다른 주제로 전환된다",
    ],
)
def test_batch7_unregistered_topic_and_leading_hanpyeon_preserve(
    text: str,
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == text
    assert output.trace.prosody_logs == []
    assert not any(
        piece.provenance == "GENERATED_PUNCT" for piece in output.render_pieces
    )


def test_batch7_jiman_comma_has_generated_source_mapped_provenance() -> None:
    text = "시장은 크게 흔들렸지만 전략은 계속 유지됐다"
    output = transform_with_trace(text)

    assert output.normalized_text == "시장은 크게 흔들렸지만, 전략은 계속 유지됐다"
    commas = [
        piece
        for piece in output.render_pieces
        if piece.text == "," and piece.provenance == "GENERATED_PUNCT"
    ]
    assert len(commas) == 1
    assert commas[0].owner == "prosody_extra"
    assert commas[0].source_span is None
    assert commas[0].metadata == {
        "prosody_type": "extra_comma",
        "rule": "subordinate_marker",
        "reason": "subordinate_jiman",
    }
    assert [
        (log.event, log.owner, log.reason, log.action, log.metadata["insert_after"])
        for log in output.trace.prosody_logs
    ] == [
        (
            "insert_extra_comma",
            "prosody_extra",
            "subordinate_jiman",
            "insert_generated_punct",
            12,
        )
    ]


@pytest.mark.parametrize(
    "text",
    [
        "흔들렸지만 전략은 유지됐다",
        "시장은 흔들렸지만전략은 유지됐다",
        "[시장은 흔들렸지만 전략은 유지됐다]",
        "코드 `시장은 흔들렸지만 전략은 유지됐다`",
    ],
)
def test_batch7_jiman_requires_two_clauses_space_and_unprotected_boundary(
    text: str,
) -> None:
    assert transform(text).count(",") == text.count(",")


def test_batch7_sentence_initial_hajiman_and_hanpyeon_are_distinct() -> None:
    assert transform("하지만 전략은 유지됐다") == "하지만, 전략은 유지됐다"
    assert transform("한편 전략은 유지됐다") == "한편 전략은 유지됐다"


@pytest.mark.parametrize(
    ("text", "owners"),
    [
        (
            "12·12 사태 이후 시장은 흔들렸지만 FTA 요건과 AI·반도체 전략은 유지됐다",
            ["dictionary", "acronym_fallback", "event"],
        ),
        (
            "기온은 -1.3도까지 떨어졌지만 3~8cm 적설은 유지됐다",
            ["range_with_unit", "signed_number"],
        ),
    ],
)
def test_batch7_numeric_lexical_claims_and_prosody_are_independent(
    text: str, owners: list[str]
) -> None:
    output = transform_with_trace(text)
    assert [claim.owner for claim in output.trace.claim_logs] == owners
    assert len(output.trace.prosody_logs) == 1
    assert output.trace.prosody_logs[0].reason == "subordinate_jiman"
    assert output.trace.prosody_logs[0].action == "insert_generated_punct"
    comma = next(
        piece
        for piece in output.render_pieces
        if piece.provenance == "GENERATED_PUNCT"
    )
    assert comma.owner == "prosody_extra"
    assert comma.source_span is None
