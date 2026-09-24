from __future__ import annotations

import json

import pytest

from LLM.compound_boundary import build_compound_mutations, compound_options
from LLM.pronunciation_lexicon import build_allowed_mutations
from LLM.prompt_template import build_prompt
from LLM.provenance import build_normalization_snapshot
from LLM.response_validation import LLMStageContractError, validate_response
from LLM.selection_pipeline import build_selection_plan, render_selection_response
from LLM.stage3_preprocessor import preprocess_stage3
from LLM.stage4_preprocessor import preprocess_stage4
from engine.main import transform_output


@pytest.mark.parametrize(("word", "expected"), (
    ("개인정보처리방침", ("개인정보-처리방침",)),
    ("인공지능기술개발", ("인공지능-기술개발",)),
    ("신용카드사용내역", ("신용카드-사용내역",)),
    ("도시가스안전관리", ("도시가스-안전관리",)),
    ("국가산업안전지도", ("국가-산업안전지도",)),
    ("서울도시철도공사", ("서울-도시철도공사",)),
    ("한국해양진흥공사", ("한국-해양진흥공사",)),
    ("대한적십자사혈액관리본부", ("대한적십자사-혈액관리본부",)),
    ("국가산업성과평가", ("국가산업-성과평가", "국가-산업성과평가")),
    ("산업용지역전기요금제", (
        "산업용지역-전기요금제", "산업용-지역전기요금제",
    )),
))
def test_only_meaningful_full_word_boundaries_are_exposed(word, expected):
    assert compound_options(word) == expected


@pytest.mark.parametrize("tail", (
    "", "의", "는", "을", "과", "에서", "에서는", "으로부터", "으로는",
    "입니다", "이었다", "이었지만", "이라는", "이라고", "이며",
))
def test_noun_tails_remain_attached_without_stripping_noun_syllables(tail):
    assert compound_options("국가산업안전지도" + tail) == ("국가-산업안전지도" + tail,)


@pytest.mark.parametrize("word", (
    "정보통신기술", "개인정보", "인공지능", "안전관리", "신용카드",
    "가나다라마바사아", "초거대신조어처리방침", "개인정보처리방침미등록",
    "한국방송통신대학교", "대한민국헌법재판소",
    "농림축산식품부", "한국전력공사", "노사정위원회",
    "확인했습니다", "자동화되었습니다", "개인정보처리했습니다",
    "산업안전관리하였습니다", "국가산업안전지도은는", "국가산업안전지도입니다만",
    "개인정보" * 9,
))
def test_unknown_short_predicate_and_unbounded_words_are_preserved(word):
    assert compound_options(word) == ()


def test_crossing_lexical_analyses_do_not_authorize_disputed_boundaries():
    # 개인/정보보호 and 개인정보/보호 disagree on the break inside the first
    # six syllables. The shared boundary before 관리시스템 remains available.
    assert compound_options("개인정보보호관리시스템") == (
        "개인정보보호-관리시스템", "개인정보보호관리-시스템",
    )
    # 재난안전 and 안전관리 overlap; neither disputed boundary is offered.
    assert compound_options("국가재난안전관리시스템") == ("국가-재난안전관리시스템",)


@pytest.mark.parametrize("text", (
    "A개인정보처리방침", "개인정보처리방침2", "개인정보처리방침_v2",
    "기존-개인정보처리방침", "개인정보처리방침-안내", "개인정보처리방침—안내",
    "/개인정보처리방침", "개인정보처리방침/안내", "개인정보처리방침@회사",
))
def test_mixed_identifiers_and_existing_boundaries_are_not_reentered(text):
    assert build_compound_mutations(text) == []


@pytest.mark.parametrize("stage", (3, 4))
@pytest.mark.parametrize("text", (
    "https://example.com/개인정보처리방침", "`개인정보처리방침`",
    '{"문서":"개인정보처리방침"}', "[개인정보처리방침]",
))
def test_protected_surfaces_never_receive_compound_candidates(stage, text):
    output = transform_output(text)
    assert not build_allowed_mutations(
        output.normalized_text, stage=stage, snapshot=build_normalization_snapshot(output),
    )


@pytest.mark.parametrize("stage", (3, 4))
def test_rule_generated_reading_remains_locked(stage):
    output = transform_output("산업용 전력은 55MW입니다.")
    snapshot = build_normalization_snapshot(output)
    candidates = build_allowed_mutations(output.normalized_text, stage=stage, snapshot=snapshot)
    assert all(
        not (item.start < span.normalized_end and span.normalized_start < item.end)
        for item in candidates for span in snapshot.spans if span.locked
    )


@pytest.mark.parametrize("stage", (3, 4))
def test_llm_selects_by_occurrence_can_abstain_and_cannot_add_more_breaks(stage):
    source = "개인정보처리방침과 개인정보처리방침을 확인했다."
    plan = build_selection_plan(source, stage=stage)
    compounds = [c for c in plan.candidates if c.kind == "compound_boundary"]
    assert len(compounds) == 2
    assert all(not c.required for c in compounds)
    assert render_selection_response(source, plan=plan, response_text=json.dumps({
        "schema_version": 1, "decisions": [],
    })) == source
    response = json.dumps({"schema_version": 1, "decisions": [
        {"id": compounds[1].candidate_id, "option": 0},
    ]})
    result = render_selection_response(source, plan=plan, response_text=response)
    assert result == "개인정보처리방침과 개인정보-처리방침을 확인했다."
    assert validate_response(source, result, prompt_level=1 if stage == 3 else 3,
                             candidates=plan.to_allowed_mutations()) == result
    assert not build_compound_mutations("개인정보-처리방침")


@pytest.mark.parametrize("prompt_level", (1, 3))
@pytest.mark.parametrize("wrong", (
    "개인정-보처리방침", "개인-정보처리방침", "개인정보처리-방침",
    "개인정보-처리-방침", "개인정보–처리방침", "개인정보-처리방법",
))
def test_validator_rejects_unsafe_breaks_with_and_without_explicit_plan(prompt_level, wrong):
    source = "개인정보처리방침"
    plan = build_selection_plan(source, stage=3 if prompt_level == 1 else 4)
    for candidates in (None, plan.to_allowed_mutations()):
        with pytest.raises(LLMStageContractError):
            validate_response(source, wrong, prompt_level=prompt_level, candidates=candidates)


def test_compound_and_contraction_share_semantic_guidance_but_not_composed_outputs():
    plan = build_selection_plan("산업용지역전기요금제입니다.", stage=4)
    candidate = next(c for c in plan.candidates if "compound_boundary" in c.kind)
    assert candidate.kind == "compound_boundary_or_natural_speech_contraction"
    assert "첫 후보를 자동 선택하지" in candidate.guidance
    assert "고유명사" in candidate.guidance
    assert "결합하지 않는다" in candidate.guidance
    assert "산업용지역-전기요금젭니다" not in candidate.options
    assert "산업용지역전기요금젭니다" in candidate.options


@pytest.mark.parametrize("prompt_level", (1, 3))
def test_prompt_explains_semantic_selection_and_abstention(prompt_level):
    prompt = build_prompt("개인정보처리방침을 확인했다.", prompt_level=prompt_level)
    assert "후보 존재는 적용 명령이 아니다" in prompt
    assert "수식 관계" in prompt
    assert "첫 후보를 자동 선택하지 않는다" in prompt
    assert "개인정보-처리방침" in prompt
    assert "국가-산업안전지도" in prompt
    assert "서울-도시철도공사" in prompt
    assert "한국-해양진흥공사" in prompt
    assert "서울대학교병원-강남-검진센터" in prompt
    assert "초중등교육법-시행령-개정안" in prompt
    assert "한국-수출입은행-무역금융본부" in prompt
    assert "자작" in prompt


def test_candidate_count_and_runtime_work_are_bounded_for_long_repetitions():
    word = "산업지역정보관리시스템" * 2
    options = compound_options(word)
    assert 0 < len(options) <= 6
    assert any(output.count("-") == 1 for output in options)
    assert any(output.count("-") > 1 for output in options)
    for output in options:
        assert output.replace("-", "") == word
        assert min(map(len, output.split("-"))) >= 3
    assert compound_options(word * 1000) == ()


@pytest.mark.parametrize("stage", (3, 4))
@pytest.mark.parametrize("tail", ("", "을", "에서는", "입니다"))
def test_llm_can_choose_multiple_semantic_boundaries_in_one_word(stage, tail):
    word = "인공지능데이터분석시스템" + tail
    expected = "인공지능-데이터분석-시스템" + tail
    source = word + "."
    plan = build_selection_plan(source, stage=stage)
    candidate = next(c for c in plan.candidates if "compound_boundary" in c.kind)
    assert expected in candidate.options
    assert any(option.count("-") == 1 for option in candidate.options)
    response = json.dumps({"schema_version": 1, "decisions": [
        {"id": candidate.candidate_id, "option": candidate.options.index(expected)},
    ]})
    output = render_selection_response(source, plan=plan, response_text=response)
    assert output == expected + "."
    for candidates in (None, plan.to_allowed_mutations()):
        assert validate_response(
            source, output, prompt_level=1 if stage == 3 else 3, candidates=candidates,
        ) == output
    assert build_compound_mutations(output) == []


@pytest.mark.parametrize("prompt_level", (1, 3))
@pytest.mark.parametrize("wrong", (
    "인공-지능-데이터분석-시스템",  # lexical unit split
    "인공지능-데이터-분석-시스템",  # two-syllable middle fragment
    "인공지능-데이터분석시스-템",  # nonlexical boundary
))
def test_multiple_hyphens_do_not_relax_individual_boundary_checks(prompt_level, wrong):
    source = "인공지능데이터분석시스템"
    plan = build_selection_plan(source, stage=3 if prompt_level == 1 else 4)
    for candidates in (None, plan.to_allowed_mutations()):
        with pytest.raises(LLMStageContractError):
            validate_response(source, wrong, prompt_level=prompt_level, candidates=candidates)


def test_long_compounds_can_offer_more_than_two_pauses_without_an_explicit_count_cap():
    options = compound_options("인공지능데이터분석시스템개발계획")
    assert "인공지능-데이터분석-시스템-개발계획" in options
    assert all("데이터-분석" not in option and "개발-계획" not in option for option in options)


@pytest.mark.parametrize("stage", (3, 4))
@pytest.mark.parametrize("label", ("기관명은 ", "회사명: ", "제품명은 '", "브랜드명은 “", "이름이 "))
def test_named_compounds_can_be_split_at_the_same_semantic_boundaries(stage, label):
    text = label + "국가산업안전지도이다. 개인정보처리방침을 공개했다."
    plan = build_selection_plan(text, stage=stage)
    compounds = [c for c in plan.candidates if "compound_boundary" in c.kind]
    assert [c.surface for c in compounds] == ["국가산업안전지도이다", "개인정보처리방침을"]
    assert compounds[0].options == ("국가-산업안전지도이다",)
    selected = text.replace("국가산업안전지도", "국가-산업안전지도")
    assert validate_response(text, selected, prompt_level=1 if stage == 3 else 3) == selected
    with pytest.raises(LLMStageContractError):
        validate_response(text, text.replace("국가산업안전지도", "국가산업안-전지도"),
                          prompt_level=1 if stage == 3 else 3)


@pytest.mark.parametrize("stage", (3, 4))
@pytest.mark.parametrize(("source", "expected"), (
    ("기관명은 국가산업안전지도입니다.", "기관명은 국가-산업안전지도입니다."),
    ("서울도시철도공사를 안내했다.", "서울-도시철도공사를 안내했다."),
    ("한국해양진흥공사의 자료다.", "한국-해양진흥공사의 자료다."),
    ("대한적십자사혈액관리본부에서 발표했다.", "대한적십자사-혈액관리본부에서 발표했다."),
))
def test_hierarchical_name_boundary_is_rendered_and_validated(stage, source, expected):
    plan = build_selection_plan(source, stage=stage)
    candidate = next(c for c in plan.candidates if "compound_boundary" in c.kind)
    replacement = expected[candidate.start:candidate.start + len(candidate.surface) + 1]
    assert replacement in candidate.options
    response = json.dumps({"schema_version": 1, "decisions": [
        {"id": candidate.candidate_id, "option": candidate.options.index(replacement)},
    ]})
    assert render_selection_response(source, plan=plan, response_text=response) == expected
    assert validate_response(source, expected, prompt_level=1 if stage == 3 else 3,
                             candidates=plan.to_allowed_mutations()) == expected


@pytest.mark.parametrize("prompt_level", (1, 3))
@pytest.mark.parametrize(("source", "wrong"), (
    ("국가산업안전지도", "국가산업-안전지도"),
    ("서울도시철도공사", "서울도시-철도공사"),
    ("한국해양진흥공사", "한국해양-진흥공사"),
    ("농림축산식품부", "농림축산-식품부"),
    ("한국전력공사", "한국-전력공사"),
    ("노사정위원회", "노사정-위원회"),
    ("인공지능기술개발", "인공-지능기술개발"),
))
def test_hierarchical_name_guard_rejects_internal_or_lexicalized_breaks(prompt_level, source, wrong):
    with pytest.raises(LLMStageContractError):
        validate_response(source, wrong, prompt_level=prompt_level)


@pytest.mark.parametrize(("source", "boundary", "contraction"), (
    ("국가산업안전지도입니다.", "국가-산업안전지도입니다.", "국가산업안전지돕니다."),
    ("서울도시철도공사입니다.", "서울-도시철도공사입니다.", "서울도시철도공삽니다."),
))
def test_single_clear_name_boundary_takes_priority_over_optional_contraction(
    source, boundary, contraction,
):
    plan = build_selection_plan(source, stage=4)
    candidate = next(c for c in plan.candidates if "compound_boundary" in c.kind)
    assert candidate.kind == "compound_boundary"
    assert candidate.options == (boundary[:-1],)
    assert validate_response(source, boundary, prompt_level=3) == boundary
    with pytest.raises(LLMStageContractError):
        validate_response(source, contraction, prompt_level=3)


@pytest.mark.parametrize(("word", "readings"), (
    ("서울대학교병원강남검진센터", ("서울대학교병원-강남-검진센터",)),
    ("대한적십자사서울특별지사혈액원", ("대한적십자사-서울특별지사-혈액원",)),
    ("국민건강보험공단부산울산경남지역본부", ("국민건강보험공단-부산울산경남-지역본부",)),
    ("국가균형발전특별회계운용계획", ("국가-균형발전특별회계-운용계획",)),
    ("소상공인경영지원자금사업", ("소상공인-경영지원자금-사업",)),
    ("초중등교육법시행령개정안", ("초중등교육법-시행령-개정안",)),
    ("인공지능기반자율주행차량안전기준", ("인공지능기반-자율주행차량-안전기준",)),
    ("차세대지능형교통시스템구축사업", ("차세대-지능형교통시스템-구축사업",)),
    ("국가초고성능컴퓨팅활용체계", ("국가-초고성능컴퓨팅-활용체계",)),
    ("생명공학연구원바이오나노연구단", (
        "생명공학연구원-바이오나노연구단",
        "생명공학연구원-바이오나노-연구단",
    )),
    ("양자컴퓨팅기술개발사업", ("양자컴퓨팅-기술개발사업",)),
    ("유전체데이터기반정밀의료시스템", ("유전체-데이터기반-정밀의료시스템",)),
    ("한국전자통신연구원소프트웨어연구소", ("한국-전자통신연구원-소프트웨어연구소",)),
    ("한국수출입은행무역금융본부", ("한국-수출입은행-무역금융본부",)),
    ("주택담보대출상환유예제도", ("주택담보대출-상환유예제도",)),
    ("글로벌자산배분펀드운용전략", (
        "글로벌자산배분-펀드운용전략",
        "글로벌-자산배분-펀드운용전략",
    )),
    ("소비자물가지수개편방안", ("소비자물가지수-개편방안",)),
    ("국립현대미술관덕수궁관", ("국립현대미술관-덕수궁관",)),
    ("한국예술종합학교연극원", ("한국예술종합학교-연극원",)),
    ("세계문화유산등재추진위원회", ("세계문화유산-등재추진위원회",)),
    ("평생학습도시인증평가", ("평생학습도시-인증평가",)),
    ("한국수자원공사수질개선사업단", ("한국-수자원공사-수질개선사업단",)),
    ("탄소중립녹색성장기본계획", ("탄소중립-녹색성장-기본계획",)),
    ("해양생태계보전지역지정안", ("해양생태계-보전지역-지정안",)),
    ("인공지능자율주행", ("인공지능-자율주행",)),
))
@pytest.mark.parametrize("stage", (3, 4))
def test_reviewed_domain_compounds_render_only_registered_semantic_groupings(
    word, readings, stage,
):
    source = f"{word}을 검토했다."
    plan = build_selection_plan(source, stage=stage)
    candidate = next(c for c in plan.candidates if c.kind == "compound_boundary")
    assert candidate.surface == word + "을"
    assert candidate.options == tuple(reading + "을" for reading in readings)
    for reading in readings:
        response = json.dumps({"schema_version": 1, "decisions": [
            {"id": candidate.candidate_id, "option": candidate.options.index(reading + "을")},
        ]})
        result = render_selection_response(source, plan=plan, response_text=response)
        assert result == f"{reading}을 검토했다."
        assert validate_response(
            source, result, prompt_level=1 if stage == 3 else 3,
            candidates=plan.to_allowed_mutations(),
        ) == result


@pytest.mark.parametrize(("word", "wrong"), (
    ("국가산업안전지도", "국가-산업-안전-지도"),
    ("서울도시철도공사", "서울-도시-철도-공사"),
    ("한국수출입은행", "한국-수출입은행"),
    ("인공지능자율주행", "인공-지능-자율-주행"),
    ("초중등교육법시행령개정안", "초중등교육법-시행-령개정안"),
    ("소상공인자작경영지원자금사업", "소상공인-경영지원자금-사업"),
))
def test_over_split_or_source_letter_deletion_is_rejected(word, wrong):
    with pytest.raises(LLMStageContractError):
        validate_response(word, wrong, prompt_level=1)


@pytest.mark.parametrize(("source", "expected", "count"), (
    (
        "한국토지주택공사LH토지주택연구원",
        "한국토지주택공사-엘에이치-토지주택연구원",
        2,
    ),
    (
        "수도권광역급행철도GTX노선",
        "수도권-광역급행철도-지티엑스-노선",
        2,
    ),
))
@pytest.mark.parametrize("stage", (3, 4))
def test_reviewed_acronym_compounds_preserve_locked_reading(source, expected, count, stage):
    output = transform_output(source + "을 확인했다.")
    prepared = (preprocess_stage3 if stage == 3 else preprocess_stage4)(
        output.normalized_text, snapshot=build_normalization_snapshot(output),
    )
    snapshot = prepared.snapshot
    plan = prepared.work_plan
    compounds = [c for c in plan.candidates if c.kind == "compound_boundary"]
    assert len(compounds) == count
    assert all(not c.required for c in compounds)
    assert all(
        not (c.start < span.normalized_end and span.normalized_start < c.end)
        for c in compounds for span in snapshot.spans if span.locked
    )
    response = json.dumps({"schema_version": 1, "decisions": [
        {"id": c.candidate_id, "option": 0} for c in compounds
    ]})
    result = render_selection_response(prepared.text, plan=plan, response_text=response)
    assert result == expected + "을 확인했다."
    assert validate_response(
        prepared.text, result,
        prompt_level=1 if stage == 3 else 3,
        snapshot=snapshot, candidates=plan.to_allowed_mutations(),
    ) == result
    assert all(
        span.text in result for span in snapshot.spans if span.locked
    )
    assert not build_compound_mutations(result)


@pytest.mark.parametrize("stage", (3, 4))
def test_gtx_no_suffix_pause_remains_an_allowed_choice(stage):
    output = transform_output("수도권광역급행철도GTX노선을 확인했다.")
    prepared = (preprocess_stage3 if stage == 3 else preprocess_stage4)(
        output.normalized_text, snapshot=build_normalization_snapshot(output),
    )
    compounds = [c for c in prepared.work_plan.candidates if c.kind == "compound_boundary"]
    assert [c.surface for c in compounds] == ["수도권광역급행철도", "노선"]
    response = json.dumps({"schema_version": 1, "decisions": [
        {"id": compounds[0].candidate_id, "option": 0},
    ]})
    result = render_selection_response(
        prepared.text, plan=prepared.work_plan, response_text=response,
    )
    assert result == "수도권-광역급행철도-지티엑스노선을 확인했다."
    assert validate_response(
        prepared.text, result, prompt_level=1 if stage == 3 else 3,
        snapshot=prepared.snapshot, candidates=prepared.work_plan.to_allowed_mutations(),
    ) == result


@pytest.mark.parametrize("source", (
    "한국토지주택공사엘에이치토지주택연구원",
    "수도권광역급행철도지티엑스노선",
))
def test_acronym_grouping_requires_confirmed_rule_engine_provenance(source):
    assert not [
        c for c in build_selection_plan(source, stage=3).candidates
        if c.kind == "compound_boundary"
    ]
