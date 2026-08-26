from __future__ import annotations

import pytest

from LLM.pronunciation_lexicon import build_allowed_mutations, entries_for_stage
from LLM.provenance import minimal_snapshot


STAGE5_EXACT_CONTRASTS = (
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
STAGE4_EXACT = tuple(
    (entry.surface, entry.pronunciation)
    for entry in entries_for_stage(4)
)


def test_stage_four_keeps_only_existing_closed_pronunciation_entries() -> None:
    surfaces = {entry.surface for entry in entries_for_stage(4)}
    assert {"색연필", "문고리", "국민연금"} <= surfaces
    assert "생산량" not in surfaces
    assert "대가" not in surfaces


@pytest.mark.parametrize(("surface", "pronunciation"), STAGE4_EXACT)
def test_every_stage4_closed_entry_is_detected_exactly(
    surface: str,
    pronunciation: str,
) -> None:
    candidates = build_allowed_mutations(f"{surface}은 확인했습니다.", stage=4)
    assert any(
        item.source_text == surface and pronunciation in item.allowed_outputs
        for item in candidates
    )


def test_stage_five_is_a_controlled_superset() -> None:
    stage4 = set(entries_for_stage(4))
    stage5 = set(entries_for_stage(5))
    assert stage4 < stage5
    assert {"생산량", "입원료", "백분율", "대가"} <= {
        entry.surface for entry in stage5
    }


def test_allowed_mutations_are_monotonic_across_llm_stages() -> None:
    text = "색연필과 문고리를 확인한 기자입니다. 생산량과 노동의 대가를 발표했습니다."
    stage3 = set(build_allowed_mutations(text, stage=3))
    stage4 = set(build_allowed_mutations(text, stage=4))
    stage5 = set(build_allowed_mutations(text, stage=5))

    assert stage3 == set()
    assert stage4 < stage5
    assert {item for item in stage4 if item.kind != "compound_boundary"} <= stage5
    assert {"n_insertion", "lexical_tensification", "natural_speech_contraction"} <= {
        item.kind for item in stage4
    }
    assert {"lexical_n_l", "contextual_homograph"} <= {
        item.kind for item in stage5
    }


def test_exact_entry_allows_particle_but_not_longer_lexical_word() -> None:
    candidates = build_allowed_mutations("생산량은 늘고 증가량은 줄었다.", stage=5)
    assert [(item.source_text, item.allowed_outputs) for item in candidates] == [
        ("생산량", ("생산냥",)),
    ]

    longer_word_candidates = build_allowed_mutations("총생산량지수입니다.", stage=5)
    assert all(item.kind != "lexical_n_l" for item in longer_word_candidates)

    spaced = build_allowed_mutations("국민 연금은 유지됩니다.", stage=4)
    assert ("국민 연금", ("국민 년금",)) in [
        (item.source_text, item.allowed_outputs) for item in spaced
    ]


def test_contextual_homograph_is_stage_five_only() -> None:
    assert build_allowed_mutations("노동의 대가를 지급했다.", stage=4) == ()
    candidate = build_allowed_mutations("노동의 대가를 지급했다.", stage=5)[0]
    assert candidate.kind == "contextual_homograph"
    assert candidate.source_text == "대가"
    assert candidate.allowed_outputs == ("대까",)


def test_contextual_homograph_blocks_expert_and_uncertain_rewrites() -> None:
    expert = build_allowed_mutations("예술계의 대가를 만났습니다.", stage=5)[0]
    uncertain = build_allowed_mutations("그는 대가에 관해 말했습니다.", stage=5)[0]
    assert expert.kind == "contextual_homograph"
    assert expert.allowed_outputs == ("대가",)
    assert uncertain.allowed_outputs == ("대가",)

    expert_contraction = build_allowed_mutations(
        "그는 예술계의 대가입니다.", stage=5
    )[0]
    assert "대깝니다" not in expert_contraction.allowed_outputs


def test_contraction_outputs_are_complete_hangul_syllables() -> None:
    candidate = build_allowed_mutations("기자입니다.", stage=4)[0]
    assert candidate.kind == "natural_speech_contraction"
    assert candidate.allowed_outputs == ("기잡니다",)
    assert all(not ("ㄱ" <= char <= "ㅎ" or "ㅏ" <= char <= "ㅣ") for char in candidate.allowed_outputs[0])


def test_general_g2p_surface_is_not_a_candidate() -> None:
    assert build_allowed_mutations("국물은 같이 읽고 있습니다.", stage=5) == ()


@pytest.mark.parametrize("stage", (3, 4, 5))
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


@pytest.mark.parametrize("stage", (3, 4, 5))
def test_compound_boundary_stays_inside_long_nominal_stem(stage: int) -> None:
    candidates = build_allowed_mutations("산업용지역전기요금제입니다.", stage=stage)
    expected = "산업용지역-전기요금제입니다"
    candidate = next(item for item in candidates if expected in item.allowed_outputs)

    assert candidate.source_text == "산업용지역전기요금제입니다"
    assert candidate.allowed_outputs
    hyphen_outputs = tuple(
        output for output in candidate.allowed_outputs if "-" in output
    )
    assert hyphen_outputs
    assert all("-입니다" not in output for output in hyphen_outputs)
    assert all(output.endswith("입니다") for output in hyphen_outputs)


def test_stage_three_exposes_only_compound_boundary_korean_mutations() -> None:
    candidates = build_allowed_mutations(
        "산업용지역전기요금제의 색연필 담당 기자입니다.",
        stage=3,
    )
    assert candidates
    assert {item.kind for item in candidates} == {"compound_boundary"}


@pytest.mark.parametrize(
    ("surface", "pronunciation", "contrast"),
    STAGE5_EXACT_CONTRASTS,
)
def test_every_stage5_exact_entry_has_positive_negative_and_contrast_coverage(
    surface: str,
    pronunciation: str,
    contrast: str,
) -> None:
    positive = build_allowed_mutations(f"{surface}은 확인했습니다.", stage=5)
    assert any(
        item.source_text == surface and pronunciation in item.allowed_outputs
        for item in positive
    )

    longer_name = build_allowed_mutations(f"신{surface}지수는 고유명사입니다.", stage=5)
    assert all(item.source_text != surface for item in longer_name)

    contrast_candidates = build_allowed_mutations(
        f"{contrast}은 변경하지 않습니다.", stage=5
    )
    assert all(item.kind != "lexical_n_l" for item in contrast_candidates)


@pytest.mark.parametrize("stage", (3, 4, 5))
def test_pronunciation_surface_inside_protected_url_is_not_a_candidate(
    stage: int,
) -> None:
    text = "자료는 https://example.com/생산량/산업용지역전기요금제에 있습니다."
    snapshot = minimal_snapshot(text)
    assert all(
        item.source_text not in {"생산량", "산업용지역전기요금제에"}
        for item in build_allowed_mutations(text, stage=stage, snapshot=snapshot)
    )
