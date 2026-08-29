from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine import SourceSpan, transform_with_trace


def _claims(text: str):
    output = transform_with_trace(text)
    assert output.trace is not None
    return output.trace.claim_logs


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("KB", "케이비", "contextual_acronym"),
        ("KB금융", "케이비금융", "contextual_acronym"),
        ("KB 금융", "케이비 금융", "contextual_acronym"),
        ("10KB", "십-킬로바이트", "simple_unit"),
        ("10 KB", "십-킬로바이트", "simple_unit"),
        ("1,000KB/s", "초당 천 킬로바이트", "compound_slash_unit"),
    ],
)
def test_kb_dual_role_uses_contextual_acronym_or_existing_unit_owner(
    text: str, expected: str, owner: str
) -> None:
    assert transform(text) == expected
    claims = _claims(text)
    assert any(claim.owner == owner for claim in claims)
    if owner == "contextual_acronym":
        claim = next(claim for claim in claims if claim.owner == owner)
        assert claim.reason == "approved_dual_role_acronym_outside_unit_context"
        assert claim.surface_type == "CONTEXTUAL_ACRONYM_SURFACE"


@pytest.mark.parametrize("text", ["KB/s", "KB1", "KB-1", "1,000 KB / s"])
def test_kb_unsafe_or_ownerless_structures_are_not_broadly_expanded(text: str) -> None:
    assert transform(text) == text
    assert not any(claim.owner == "contextual_acronym" for claim in _claims(text))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/KB?q=KB", "https://example.com/KB?q=KB"),
        ("/tmp/KB/file", "/tmp/KB/file"),
        ('{"value":"KB"}', '{"value":"KB"}'),
        ("`KB`", "`KB`"),
        ("[KB]", "KB"),
        ("curl KB", "curl KB"),
    ],
)
def test_kb_protected_contexts_do_not_reenter_contextual_owner(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    assert not any(claim.owner == "contextual_acronym" for claim in _claims(text))


def test_kb_markdown_fence_is_protected_before_contextual_owner() -> None:
    text = "```bash\nKB\n```"
    output = transform_with_trace(text)

    assert "KB" in output.normalized_text
    assert output.trace is not None
    assert [claim.owner for claim in output.trace.claim_logs] == ["preserve"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("M&A", "엠앤에이"),
        ("R&D", "알앤디"),
        ("A&B", "에이앤비"),
        ("Q&A", "큐앤에이"),
        ("S&P", "에스앤피"),
    ],
)
def test_uppercase_ampersand_acronym_full_claim(text: str, expected: str) -> None:
    assert transform(text) == expected
    claim = _claims(text)[0]
    assert claim.owner == "ampersand_acronym"
    assert claim.reason == "safe_uppercase_ampersand_acronym_full_claim"
    assert claim.surface_type == "AMPERSAND_ACRONYM_SURFACE"


def test_ampersand_acronym_retains_character_source_spans() -> None:
    output = transform_with_trace("AB&CD")

    assert output.normalized_text == "에이비앤씨디"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("에이", "GENERATED_READING", SourceSpan(0, 1), "ampersand_acronym"),
        ("비", "GENERATED_READING", SourceSpan(1, 2), "ampersand_acronym"),
        ("앤", "GENERATED_READING", SourceSpan(2, 3), "ampersand_acronym"),
        ("씨", "GENERATED_READING", SourceSpan(3, 4), "ampersand_acronym"),
        ("디", "GENERATED_READING", SourceSpan(4, 5), "ampersand_acronym"),
    ]


@pytest.mark.parametrize("text", ["S&P500", "S&P 500"])
def test_sp_numeric_suffix_remains_finance_index_full_claim(text: str) -> None:
    assert transform(text) == "에스앤피 오백"
    claims = _claims(text)
    assert [claim.owner for claim in claims] == ["finance_index"]
    assert claims[0].reason == "finance_index_numeric_suffix_full_claim"


@pytest.mark.parametrize("text", ["M & A", "a&b", "A&b", "A&1", "x&&y"])
def test_unsupported_ampersand_forms_preserve_atomically(text: str) -> None:
    assert transform(text) == text
    assert not any(claim.owner == "ampersand_acronym" for claim in _claims(text))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/?q=M&A", "https://example.com/?q=M&A"),
        ('{"value":"M&A"}', '{"value":"M&A"}'),
        ("`M&A`", "`M&A`"),
        ("[M&A]", "M&A"),
        ("curl M&A", "curl M&A"),
    ],
)
def test_ampersand_acronym_protected_contexts_do_not_reenter(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    assert not any(claim.owner == "ampersand_acronym" for claim in _claims(text))


def test_ampersand_acronym_markdown_fence_is_protected() -> None:
    text = "```text\nM&A\n```"
    output = transform_with_trace(text)

    assert "M&A" in output.normalized_text
    assert output.trace is not None
    assert [claim.owner for claim in output.trace.claim_logs] == ["preserve"]


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("39대", "39대", "contextual_number_unit"),
        ("40대", "사십-대", "counter_noun"),
        ("41대", "사십일-대", "counter_noun"),
        ("39.9대", "삼십구쩜구-대", "contextual_number_unit"),
        ("40.0대", "사십쩜영-대", "contextual_number_unit"),
        ("40.5대", "사십쩜오-대", "contextual_number_unit"),
        ("1,000대", "천-대", "counter_noun"),
        ("6,700대,", "육천칠백-대,", "counter_noun"),
        ("40대 남성", "사십-대 남성", "contextual_number_unit"),
        ("100대 명소", "백-대 명소", "counter_noun"),
    ],
)
def test_numeric_dae_threshold_boundary(
    text: str, expected: str, owner: str
) -> None:
    assert transform(text) == expected
    claim = next(claim for claim in _claims(text) if claim.owner == owner)
    if owner == "counter_noun":
        assert claim.reason == "dae_counter_sino_threshold_40_plus"


@pytest.mark.parametrize(
    ("text", "expected", "reason"),
    [
        (
            "자동차 3대",
            "자동차 세-대",
            "contextual_number_unit_confirmed",
        ),
        (
            "자동차는 모두 3대",
            "자동차는 모두 세-대",
            "contextual_number_unit_confirmed",
        ),
        (
            "차량은 총 5대",
            "차량은 총 다섯-대",
            "contextual_number_unit_confirmed",
        ),
        (
            "자동차 39.9대",
            "자동차 삼십구쩜구-대",
            "contextual_number_unit_confirmed",
        ),
    ],
)
def test_numeric_dae_under_40_requires_registered_quantity_context(
    text: str, expected: str, reason: str
) -> None:
    assert transform(text) == expected
    claim = next(claim for claim in _claims(text) if claim.owner == "contextual_number_unit")
    assert claim.reason == reason


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("가족은 모두 3대", "가족은 모두 3대"),
        ("20대 남성", "이십-대 남성"),
        ("5대 과제", "오대 과제"),
        ("가족 3대", "가족 삼-대"),
        ("가업을 3대째 이어 왔다", "가업을 삼-대째 이어 왔다"),
    ],
)
def test_numeric_dae_under_40_contextual_decisions(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    assert any(claim.owner == "contextual_number_unit" for claim in _claims(text))


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("제40대", "제-사십대", "numeric_suffix"),
        ("40대3", "사십대삼", "korean_da_score_pair"),
        ("경기는 2대 1", "경기는 이 대 일", "korean_da_score_pair"),
        ("점수 2대1", "점수 이대일", "korean_da_score_pair"),
        ("+40대", "플러스 사십 대", "signed_number"),
        ("-40대", "마이너스 사십 대", "signed_number"),
        ("040대", "040대", "contextual_number_unit"),
    ],
)
def test_numeric_dae_structural_owners_and_invalid_forms_keep_precedence(
    text: str, expected: str, owner: str
) -> None:
    assert transform(text) == expected
    assert any(claim.owner == owner for claim in _claims(text))


def test_spaced_threshold_dae_precedes_contextless_independent_pair() -> None:
    text = "40대 3"

    assert transform(text) == "사십-대 삼"
    claims = _claims(text)
    assert [claim.owner for claim in claims] == ["counter_noun", "number"]
    assert not any(claim.owner == "korean_da_score_pair" for claim in claims)


@pytest.mark.parametrize("text", ["4,0대", "1,00대"])
def test_malformed_comma_numeric_dae_is_not_partially_read(text: str) -> None:
    assert transform(text) == text
    assert any(claim.owner == "contextual_number_unit" for claim in _claims(text))
    assert not any(
        claim.owner in {"counter_noun", "decimal_registered_suffix"}
        for claim in _claims(text)
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/40대", "https://example.com/40대"),
        ("/tmp/40대/file", "/tmp/40대/file"),
        ('{"value":"40대"}', '{"value":"40대"}'),
        ("`40대`", "`40대`"),
        ("[40대]", "40대"),
        ("curl 40대", "curl 40대"),
        ("A40대", "A40대"),
        ("40대A", "40대A"),
    ],
)
def test_numeric_dae_protected_and_unsafe_tail_contexts_preserve(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
    assert not any(
        claim.reason == "dae_counter_sino_threshold_40_plus"
        for claim in _claims(text)
    )


def test_numeric_dae_markdown_fence_is_protected() -> None:
    text = "```text\n40대\n```"
    output = transform_with_trace(text)

    assert "40대" in output.normalized_text
    assert output.trace is not None
    assert [claim.owner for claim in output.trace.claim_logs] == ["preserve"]


def test_required_numeric_dae_sentence_uses_counter_and_quantity_sequence() -> None:
    text = (
        "자동차는 모두 6,700대, 12,500입니다. "
        "자동차는 모두 6,700대 12,500입니다."
    )
    expected = (
        "자동차는 모두 육천칠백-대, 만 이천오백입니다. "
        "자동차는 모두 육천칠백-대 만이천오백입니다."
    )

    assert transform(text) == expected
    claims = _claims(text)
    assert any(
        claim.owner == "contextual_number_unit"
        and claim.reason == "contextual_number_unit_confirmed"
        for claim in claims
    )
    assert any(
        claim.owner == "numeric_dae_quantity_sequence"
        and claim.reason
        == "numeric_dae_quantity_sequence_explicit_counter_context"
        for claim in claims
    )
    assert not any(
        claim.owner == "korean_da_score_pair"
        and claim.reason == "korean_da_score_pair_independent_right_number_gate"
        for claim in claims
    )
