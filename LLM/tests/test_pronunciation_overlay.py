from __future__ import annotations

import pytest

from LLM.pronunciation_lexicon import entries_for_stage
from LLM.pronunciation_overlay import apply_pronunciation_overlay
from LLM.provenance import minimal_snapshot
from LLM.response_validation import LLMStageContractError, validate_response
from LLM.validation_models import NormalizationSnapshot, NormalizedSpan


STAGE4_FIXED = tuple(
    (entry.surface, entry.pronunciation)
    for entry in entries_for_stage(4)
)
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
    ("한여름", "한녀름", "늦여름"),
    ("직행열차", "직행녈차", "급행열차"),
    ("영업용", "영업뇽", "업무용"),
    ("서울역", "서울력", "부산역"),
    ("휘발유", "휘발류", "경유"),
    ("눈동자", "눈똥자", "눈동작"),
    ("신바람", "신빠람", "새바람"),
    ("강가", "강까", "건강가정"),
    ("강줄기", "강쭐기", "산줄기"),
)

STAGE4_APPROVED_EXPANSION = (
    ("한여름", "한녀름", "한여름밤"),
    ("직행열차", "직행녈차", "직행열차표"),
    ("영업용", "영업뇽", "영업용차량"),
    ("서울역", "서울력", "서울역사박물관"),
    ("휘발유", "휘발류", "휘발유가격"),
    ("눈동자", "눈똥자", "눈동자색"),
    ("신바람", "신빠람", "신바람축제"),
    ("강가", "강까", "강가마을"),
    ("강줄기", "강쭐기", "강줄기지도"),
)


@pytest.mark.parametrize(("surface", "pronunciation"), STAGE4_FIXED)
def test_stage4_fixed_entry_is_applied_before_llm_with_particle(
    surface: str,
    pronunciation: str,
) -> None:
    result = apply_pronunciation_overlay(f"{surface}은 확인했습니다.", stage=4)
    assert result.text == f"{pronunciation}은 확인했습니다."
    assert any(
        span.text == pronunciation
        and span.locked
        and span.provenance == "GENERATED_STAGE4_PRONUNCIATION"
        for span in result.snapshot.spans
    )
    assert validate_response(
        result.text,
        result.text,
        prompt_level=2,
        snapshot=result.snapshot,
    ) == result.text


@pytest.mark.parametrize(("surface", "pronunciation", "contrast"), STAGE4_EXACT_CONTRASTS)
def test_stage4_fixed_entry_has_positive_negative_and_contrast_coverage(
    surface: str,
    pronunciation: str,
    contrast: str,
) -> None:
    assert apply_pronunciation_overlay(f"{surface}을 확인했다.", stage=4).text.startswith(pronunciation)
    assert apply_pronunciation_overlay(f"신{surface}지수입니다.", stage=4).text.startswith(f"신{surface}")
    assert apply_pronunciation_overlay(f"{contrast}은 유지한다.", stage=4).text.startswith(contrast)


def test_overlay_is_stage_four_only() -> None:
    text = "생산량은 늘었습니다."
    assert apply_pronunciation_overlay(text, stage=3).text == text
    assert apply_pronunciation_overlay(text, stage=4).text == "생산냥은 늘었습니다."


@pytest.mark.parametrize(
    ("surface", "pronunciation", "longer_surface"),
    STAGE4_APPROVED_EXPANSION,
)
def test_stage4_approved_expansion_exact_boundary_and_stage_isolation(
    surface: str,
    pronunciation: str,
    longer_surface: str,
) -> None:
    assert apply_pronunciation_overlay(f"{surface}에서", stage=4).text == f"{pronunciation}에서"
    assert apply_pronunciation_overlay(longer_surface, stage=4).text == longer_surface
    assert apply_pronunciation_overlay(f"{surface}에서", stage=3).text == f"{surface}에서"


@pytest.mark.parametrize(
    ("surface", "pronunciation", "_longer_surface"),
    STAGE4_APPROVED_EXPANSION,
)
def test_stage4_approved_expansion_excludes_protected_and_locked_spans(
    surface: str,
    pronunciation: str,
    _longer_surface: str,
) -> None:
    protected_text = f"https://example.com/{surface}/file"
    protected_result = apply_pronunciation_overlay(
        protected_text,
        stage=4,
        snapshot=minimal_snapshot(protected_text),
    )
    assert protected_result.text == protected_text

    locked_snapshot = NormalizationSnapshot(
        normalized_text=surface,
        spans=(
            NormalizedSpan(
                normalized_start=0,
                normalized_end=len(surface),
                text=surface,
                source_start=0,
                source_end=len(surface),
                owner="rule_engine",
                provenance="GENERATED_READING",
                locked=True,
                protected=False,
            ),
        ),
    )
    locked_result = apply_pronunciation_overlay(
        surface,
        stage=4,
        snapshot=locked_snapshot,
    )
    assert locked_result.text == surface
    assert pronunciation not in locked_result.text


def test_unregistered_daega_is_never_changed_by_deterministic_overlay() -> None:
    assert apply_pronunciation_overlay(
        "노동의 대가를 지급했다.", stage=4
    ).text == "노동의 대가를 지급했다."


def test_ambiguous_ingi_is_not_registered() -> None:
    text = "인기가 높고 개인기가 뛰어난 무인기 선수입니다."
    assert apply_pronunciation_overlay(text, stage=4).text == text


def test_overlay_does_not_touch_protected_or_longer_surface() -> None:
    protected = "https://example.com/생산량/file"
    text = f"{protected}와 신생산량지수입니다."
    snapshot = minimal_snapshot(text)
    result = apply_pronunciation_overlay(text, stage=4, snapshot=snapshot)
    assert result.text == text


def test_overlay_is_idempotent_and_locked_against_llm_reversal() -> None:
    first = apply_pronunciation_overlay("생산량은 늘었습니다.", stage=4)
    second = apply_pronunciation_overlay(first.text, stage=4, snapshot=first.snapshot)
    assert second.text == first.text
    assert second.applied_mutations == ()

    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response(
            first.text,
            "생산량은 늘었습니다.",
            prompt_level=2,
            snapshot=first.snapshot,
        )
    assert exc_info.value.code == "LOCKED_READING_MUTATION"
