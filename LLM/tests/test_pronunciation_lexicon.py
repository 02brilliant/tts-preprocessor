from __future__ import annotations

import pytest

from LLM.pronunciation_lexicon import build_allowed_mutations, entries_for_stage
from LLM.provenance import minimal_snapshot


STAGE4_EXACT_CONTRASTS = (
    ("의견란", "의견난", "질문란"),
    ("임진란", "임진난", "전쟁란"),
    ("생산량", "생산냥", "증가량"),
    ("결단력", "결딴녁", "판단력"),
    ("공권력", "공꿘녁", "사법권력"),
    ("동원령", "동원녕", "소집령"),
    ("상견례", "상견녜", "결혼례"),
    ("횡단로", "횡단노", "종단로"),
    ("이원론", "이원논", "다원론"),
    ("입원료", "이붠뇨", "진료"),
    ("구근류", "구근뉴", "어류"),
    ("백분율", "백뿐뉼", "합격률"),
)


def test_stage_four_registry_contains_only_fixed_entries() -> None:
    surfaces = {entry.surface for entry in entries_for_stage(4)}
    assert {"색연필", "문고리", "생산량", "입원료", "백분율"} <= surfaces
    assert "대가" not in surfaces


def test_fixed_entries_are_not_llm_mutation_candidates_after_overlay_split() -> None:
    text = "색연필과 문고리를 확인했습니다. 생산량과 입원료를 발표했습니다."
    assert all(
        item.kind not in {"n_insertion", "lexical_tensification", "lexical_n_l"}
        for item in build_allowed_mutations(text, stage=4)
    )


def test_contraction_outputs_are_complete_hangul_syllables() -> None:
    candidate = build_allowed_mutations("기자입니다.", stage=4)[0]
    assert candidate.kind == "natural_speech_contraction"
    assert candidate.allowed_outputs == ("기잡니다",)
    assert all(
        not ("ㄱ" <= char <= "ㅎ" or "ㅏ" <= char <= "ㅣ")
        for char in candidate.allowed_outputs[0]
    )


def test_general_g2p_surface_is_not_a_candidate() -> None:
    assert build_allowed_mutations("국물은 같이 읽고 있습니다.", stage=4) == ()


@pytest.mark.parametrize("stage", (3, 4))
@pytest.mark.parametrize(
    "text",
    ("확인했습니다.", "발표했습니다.", "처리되었습니다.", "검토하였습니다."),
)
def test_compound_boundary_does_not_split_predicate_or_ending(
    stage: int,
    text: str,
) -> None:
    assert all(
        item.kind != "compound_boundary"
        for item in build_allowed_mutations(text, stage=stage)
    )


@pytest.mark.parametrize("stage", (3, 4))
def test_compound_boundary_stays_inside_long_nominal_stem(stage: int) -> None:
    candidates = build_allowed_mutations("산업용지역전기요금제입니다.", stage=stage)
    expected = "산업용지역-전기요금제입니다"
    candidate = next(item for item in candidates if expected in item.allowed_outputs)

    assert candidate.source_text == "산업용지역전기요금제입니다"
    hyphen_outputs = tuple(output for output in candidate.allowed_outputs if "-" in output)
    assert all("-입니다" not in output for output in hyphen_outputs)
    assert all(output.endswith("입니다") for output in hyphen_outputs)


def test_stage_three_exposes_only_compound_boundary_korean_mutations() -> None:
    candidates = build_allowed_mutations(
        "산업용지역전기요금제의 색연필 담당 기자입니다.",
        stage=3,
    )
    assert candidates
    assert {item.kind for item in candidates} == {"compound_boundary"}


@pytest.mark.parametrize("stage", (3, 4))
def test_pronunciation_surface_inside_protected_url_is_not_a_candidate(
    stage: int,
) -> None:
    text = "자료는 https://example.com/생산량/산업용지역전기요금제에 있습니다."
    snapshot = minimal_snapshot(text)
    assert all(
        item.source_text not in {"생산량", "산업용지역전기요금제에"}
        for item in build_allowed_mutations(text, stage=stage, snapshot=snapshot)
    )
