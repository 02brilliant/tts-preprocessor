from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_hyphen_phone_provenance_validation() -> None:
    output = transform_with_trace("번호는 123-456-7890입니다")

    assert output.normalized_text == "번호는 일이삼 사오육 칠팔구공입니다"
    assert any(
        piece.owner == "hyphen_digit_blocks" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phone_route_provenance_validation() -> None:
    output = transform_with_trace("전화 1234-5678을 눌러")

    assert output.normalized_text == "전화 일이삼사 오육칠팔을 눌러"
    assert any(
        piece.owner == "phone" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_two_block_hyphen_code_provenance_validation() -> None:
    output = transform_with_trace("A-1")

    assert output.normalized_text == "에이 원"
    assert any(
        piece.owner == "single_letter_alnum_code"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_k_hangul_lexical_render_preserves_hangul_piece() -> None:
    output = transform_with_trace("K-푸드")

    assert output.normalized_text == "케이푸드"
    assert [
        (piece.text, piece.provenance, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("케이", "GENERATED_READING", "k_hangul_lexical"),
        ("푸드", "ORIGINAL_KOREAN", "k_hangul_lexical"),
    ]
    assert any(claim.owner == "k_hangul_lexical" for claim in output.trace.claim_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_prefixed_ordinal_numeric_suffix_trace_owner() -> None:
    output = transform_with_trace("제5차")

    assert output.normalized_text == "제 오차"
    assert any(claim.owner == "numeric_suffix" for claim in output.trace.claim_logs)
    assert any(
        piece.owner == "numeric_suffix" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_single_letter_alnum_code_trace_owner_for_tail_code() -> None:
    output = transform_with_trace("A-10C")

    assert output.normalized_text == "에이 십 씨"
    assert any(
        claim.owner == "single_letter_alnum_code"
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.owner == "single_letter_alnum_code"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_k_year_code_preserve_has_no_surface_claim() -> None:
    output = transform_with_trace("K-2024")

    assert output.normalized_text == "K-2024"
    assert not any(
        claim.owner == "single_letter_alnum_code"
        for claim in output.trace.claim_logs
    )
    assert not any(
        claim.owner == "two_block_hyphen_code"
        for claim in output.trace.claim_logs
    )
    assert [
        (piece.text, piece.provenance, piece.owner)
        for piece in output.render_pieces
    ] == [("K-2024", "ORIGINAL_BOUNDARY", None)]


def test_range_with_unit_trace_owner() -> None:
    output = transform_with_trace("3~5km")

    assert output.normalized_text == "삼에서 오 킬로미터"
    assert any(claim.owner == "range_with_unit" for claim in output.trace.claim_logs)
    assert any(
        piece.owner == "range_with_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_ph_unsafe_tail_preserve_trace() -> None:
    output = transform_with_trace("pH7.4test")

    assert output.normalized_text == "pH7.4test"
    assert any(
        claim.owner == "preserve"
        and claim.surface_type == "PH_PRESERVE_SURFACE"
        and claim.reason == "ph_unsafe_tail_preserve"
        for claim in output.trace.claim_logs
    )
    assert [
        (piece.text, piece.provenance, piece.owner)
        for piece in output.render_pieces
    ] == [("pH7.4test", "ORIGINAL_BOUNDARY", None)]


def test_simple_unit_contamination_preserve_trace() -> None:
    output = transform_with_trace("45m3abc")

    assert output.normalized_text == "45m3abc"
    assert any(
        claim.owner == "preserve"
        and claim.surface_type == "UNIT_CONTAMINATION_PRESERVE_SURFACE"
        and claim.reason == "unit_like_ascii_tail_contamination"
        for claim in output.trace.claim_logs
    )
    assert [
        (piece.text, piece.provenance, piece.owner)
        for piece in output.render_pieces
    ] == [("45m3abc", "ORIGINAL_BOUNDARY", None)]


def test_korean_unit_contamination_preserve_trace() -> None:
    output = transform_with_trace("30kgtest")

    assert output.normalized_text == "30kgtest"
    assert any(
        claim.owner == "preserve"
        and claim.surface_type == "UNIT_CONTAMINATION_PRESERVE_SURFACE"
        and claim.reason == "unit_like_ascii_tail_contamination"
        for claim in output.trace.claim_logs
    )
    assert [
        (piece.text, piece.provenance, piece.owner)
        for piece in output.render_pieces
    ] == [("30kgtest", "ORIGINAL_BOUNDARY", None)]


def test_compound_unit_contamination_preserve_trace() -> None:
    output = transform_with_trace("90km/hour")

    assert output.normalized_text == "90km/hour"
    assert any(
        claim.owner == "preserve"
        and claim.surface_type == "UNIT_CONTAMINATION_PRESERVE_SURFACE"
        and claim.reason == "compound_unit_like_ascii_tail_contamination"
        for claim in output.trace.claim_logs
    )
    assert [
        (piece.text, piece.provenance, piece.owner)
        for piece in output.render_pieces
    ] == [("90km/hour", "ORIGINAL_BOUNDARY", None)]
