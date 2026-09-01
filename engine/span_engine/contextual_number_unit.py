from __future__ import annotations

import re
from typing import Any

from engine.span_engine.counter import (
    counter_number_reading,
    native_number_under_100,
)
from engine.span_engine.models import (
    ContextualDecision,
    ContextualDecisionKind,
    RenderPiece,
    SourceSpan,
    Surface,
    SurfaceCandidate,
)
from engine.span_engine.numeric_reading import (
    normalize_integer_text,
    read_sino_time_suffix_number_text,
    read_spaced_integer_text,
)
from engine.span_engine.residual_spacing import valid_unary_sign_left_boundary
from engine.span_engine.sign_aliases import SIGNED_NUMERIC_SIGN_ALIASES
from engine.span_engine.signed_numeric import (
    parse_signed_numeric_core,
    render_signed_numeric,
)
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY

RULE_VERSION = "contextual-number-unit-v1"
OWNER = "contextual_number_unit"
OWNER_PRIORITY = 70

_SUPPORTED_UNITS = (
    "가지",
    "분",
    "번",
    "점",
    "조",
    "대",
    "부",
    "동",
    "호",
    "판",
    "단",
    "등",
    "척",
    "장",
    "권",
    "편",
    "층",
    "차",
    "위",
)
_NATIVE_THROUGH_99_RESIDUAL_UNITS = frozenset({"가지", "분"})
_DEFAULT_RESIDUAL_SINO_THRESHOLD = 40
_NATIVE_THROUGH_99_RESIDUAL_SINO_THRESHOLD = 100
_UNIT_PATTERN = "|".join(sorted(_SUPPORTED_UNITS, key=len, reverse=True))
_SIGN_PATTERN = re.escape("".join(sorted(SIGNED_NUMERIC_SIGN_ALIASES)))
_BROAD_SURFACE_RE = re.compile(
    rf"(?P<prefix>제|[{_SIGN_PATTERN}])?"
    rf"(?P<number>\d[\d,]*(?:\.\d+)?(?:[A-Za-z]+)?)"
    rf"(?P<space> ?)(?P<unit>{_UNIT_PATTERN})(?P<tail>[가-힣]*)"
)
_RANGE_DELIMITERS = frozenset("~∼～〜-–—")
_IDENTIFIER_BOUNDARY_BLOCKERS = frozenset("_/.")
_COMMON_TAILS = frozenset(
    {
        "",
        "가",
        "이",
        "은",
        "는",
        "을",
        "를",
        "에",
        "에게",
        "도",
        "만",
        "의",
        "로",
        "으로",
        "와",
        "과",
        "에서",
        "부터",
        "까지",
        "쯤",
        "정도",
        "꼴",
        "당",
        "마다",
        "다",
        "이다",
        "입니다",
        "였다",
        "였습니다",
        "이었습니다",
        "였지만",
        "였고",
        "이었다",
        "이었고",
        "이며",
        "이고",
    }
)
_GAJI_TAILS = _COMMON_TAILS | {"씩"}
_BEON_TAILS = _COMMON_TAILS | {"씩", "이나"}
_BEON_FIXED_SUFFIXES = ("지", "길", "선", "대", "가")
_CHA_FIXED_SUFFIXES = ("원", "량", "로")
_WI_FIXED_SUFFIXES = ("권", "자")

PERSON_BUN_NOUNS = frozenset(
    {
        "손님",
        "고객",
        "내빈",
        "참석자",
        "참가자",
        "지원자",
        "후보자",
        "위원",
        "심사위원",
        "선생님",
        "교수님",
        "어르신",
        "환자",
        "승객",
    }
)
BEON_IDENTIFIER_NOUNS = frozenset(
    {
        "버스",
        "출구",
        "문제",
        "문항",
        "질문",
        "후보",
        "좌석",
        "객실",
        "창구",
        "게이트",
        "트랙",
        "채널",
        "노선",
        "테이블",
        "파일",
        "항목",
        "선택지",
        "버튼",
        "메뉴",
        "승강장",
        "선수",
        "타자",
        "주자",
        "국도",
    }
)
BEON_OCCURRENCE_MARKERS = frozenset({"총", "모두"})
BEON_OCCURRENCE_ACTIONS = frozenset(
    {
        "반복",
        "재시도",
        "방문",
        "시도",
        "호출",
        "클릭",
        "재생",
        "확인",
        "우회",
    }
)
BUN_TIME_REMAINING_ACTIONS = frozenset({"남"})
JEOM_SCORE_ANCHORS = frozenset(
    {
        "점수",
        "평점",
        "만점",
        "득점",
        "실점",
        "감점",
        "가점",
        "별점",
        "획득",
        "기록",
        "차이",
        "격차",
        "평균",
        "평가",
    }
)
JEOM_ITEM_NOUNS = frozenset(
    {
        "신작",
        "작품",
        "출품작",
        "전시품",
        "미술품",
        "유물",
        "문화재",
        "소장품",
        "물품",
        "상품",
        "수집품",
    }
)
JEOM_ITEM_ACTIONS = frozenset(
    {"전시", "공개", "출품", "기증", "소장", "선정", "판매", "반입", "확보"}
)
JO_FINANCIAL_ANCHORS = frozenset(
    {"금액", "예산", "매출", "자산", "부채", "투자", "규모"}
)
JO_GROUP_MARKERS = frozenset({"총", "모두"})
JO_GROUP_ACTIONS = frozenset(
    {"나누", "나눴", "편성", "구성", "배정", "만들", "발표"}
)
DAE_GENERATION_NOUNS = frozenset(
    {"가족", "가문", "가계", "가업", "집안", "왕조", "세습"}
)
DAE_AGE_NOUNS = frozenset(
    {
        "남성",
        "여성",
        "청년",
        "직장인",
        "소비자",
        "유권자",
        "환자",
        "인구",
        "세대",
        "연령층",
        "초반",
        "중반",
        "후반",
    }
)
DAE_MAJOR_ITEM_NOUNS = frozenset({"과제", "전략", "추진전략"})
DAE_MACHINE_LOCATION_NOUNS = frozenset({"주차장"})
DAE_MACHINE_LOCATION_ACTIONS = frozenset({"남"})
BU_SEQUENCE_NOUNS = frozenset({"행사", "공연", "책의"})
BU_DOCUMENT_NOUNS = frozenset(
    {
        "자료",
        "복사본",
        "신문",
        "서류",
        "문서",
        "보고서",
        "신청서",
        "계약서",
        "책자",
        "인쇄물",
        "안내문",
        "자료집",
        "원고",
    }
)
BU_QUANTITY_ACTIONS = frozenset(
    {
        "인쇄",
        "복사",
        "제출",
        "배포",
        "준비",
        "발급",
        "보관",
        "냈",
        "남",
        "사용",
    }
)
DONG_IDENTIFIER_NOUNS = frozenset(
    {"아파트", "주민", "사무소", "행정동", "주소"}
)
DONG_PREVIOUS_IDENTIFIER_NOUNS = frozenset({"아파트", "주소"})
DONG_BUILDING_NOUNS = frozenset(
    {"건물", "주택", "공장", "창고", "시설"}
)
DONG_QUANTITY_ACTIONS = frozenset(
    {"신축", "건설", "철거", "붕괴", "피해", "증축", "지었", "무너졌"}
)
HO_IDENTIFIER_NOUNS = frozenset(
    {"대기표", "차량", "태풍", "선박", "열차", "위성"}
)
HO_HOUSEHOLD_NOUNS = frozenset({"농가", "가구", "세대", "피해가구"})
HO_QUANTITY_ACTIONS = frozenset(
    {"지원", "피해", "조사", "선정", "복구", "확인"}
)
PAN_GAME_NOUNS = frozenset(
    {"바둑", "장기", "체스", "경기", "대국", "게임", "승부"}
)
PAN_GAME_ACTIONS = frozenset({"겨뤘", "겨루"})
PAN_EDITION_NOUNS = frozenset({"개정", "증보", "책", "사전", "교재"})
DAN_GRADE_NOUNS = frozenset(
    {"태권도", "유도", "검도", "바둑", "기어", "계단", "단계"}
)
DAN_STACK_ACTIONS = frozenset({"쌓", "적재", "올리"})
DAN_STACK_NOUNS = frozenset({"선반", "상자"})
DEUNG_RANK_NOUNS = frozenset(
    {"대회", "경기", "평가", "시험", "순위", "결과"}
)
DEUNG_LIGHT_NOUNS = frozenset({"조명", "전등", "등불", "램프"})
DEUNG_LIGHT_ACTIONS = frozenset(
    {"설치", "점등", "소등", "교체", "켜", "끄"}
)
CHEOK_SHIP_NOUNS = frozenset(
    {"선박", "배", "함정", "어선", "화물선", "여객선", "군함", "잠수함"}
)
CHEOK_LENGTH_NOUNS = frozenset(
    {"길이", "폭", "너비", "높이", "깊이", "둘레"}
)
CHEOK_SHIP_LOCATION_NOUNS = frozenset({"항구"})
JANG_SHEET_NOUNS = frozenset(
    {
        "종이",
        "사진",
        "표",
        "티켓",
        "카드",
        "문서",
        "인쇄물",
        "포스터",
        "전단",
        "명함",
    }
)
JANG_CHAPTER_NOUNS = frozenset(
    {"책", "보고서", "교재", "논문", "목차"}
)
GWON_BOOK_NOUNS = frozenset(
    {"책", "도서", "사전", "교재", "소설", "만화책", "자료집"}
)
GWON_VOLUME_NOUNS = frozenset({"전집", "시리즈", "서지"})
PYEON_WORK_NOUNS = frozenset(
    {
        "영화",
        "드라마",
        "논문",
        "시",
        "소설",
        "기사",
        "영상",
        "다큐멘터리",
        "광고",
    }
)
PYEON_STRUCTURE_NOUNS = frozenset(
    {"시리즈", "법전", "문서", "상편", "하편"}
)
CHEUNG_LOCATION_NOUNS = frozenset(
    {"회의실", "사무실", "로비", "식당"}
)
CHEUNG_LOCATION_PREFIXES = frozenset({"지하", "지상"})
CHEUNG_ACCESS_NOUNS = frozenset({"계단"})
CHEUNG_MOVEMENT_ACTIONS = frozenset({"올라", "내려"})


def scan_contextual_malformed_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Claim unsupported number forms before signed/decimal/generic fallback."""
    _ensure_text(raw_text)
    candidates: list[SurfaceCandidate] = []
    for match in _BROAD_SURFACE_RE.finditer(raw_text):
        if not _eligible_match_boundary(raw_text, match):
            continue
        unit = match.group("unit")
        if not _is_supported_tail(unit, match.group("tail")):
            continue
        if _is_existing_specific_decimal(raw_text, unit, match):
            continue
        if match.group("prefix") == "제":
            continue
        if unit == "분" and _is_structured_duration_minute(raw_text, match.start()):
            continue
        if _preceded_by_spaced_ordinal(
            raw_text, match.start()
        ):
            continue
        if _is_valid_supported_number_match(match):
            continue
        candidates.append(
            _candidate(
                raw_text,
                match,
                decision_kind=ContextualDecisionKind.DEFERRED,
                semantic_type=_ambiguous_semantic_type(unit),
                blocking_reason=_blocking_reason(match),
            )
        )
    return candidates


def scan_contextual_large_unit_malformed_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    return [
        candidate
        for candidate in scan_contextual_malformed_candidates(raw_text)
        if _candidate_unit(candidate) == "조"
    ]


def scan_contextual_non_large_unit_malformed_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    return [
        candidate
        for candidate in scan_contextual_malformed_candidates(raw_text)
        if _candidate_unit(candidate) != "조"
    ]


def scan_contextual_large_unit_collision_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    """Handle group `조` before the existing generic large-unit owner."""
    _ensure_text(raw_text)
    return _scan_standard_candidates(raw_text, units=frozenset({"조"}))


def scan_contextual_number_unit_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    _ensure_text(raw_text)
    return _scan_standard_candidates(
        raw_text, units=frozenset(_SUPPORTED_UNITS) - {"조"}
    )


def _scan_standard_candidates(
    raw_text: str, *, units: frozenset[str]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _BROAD_SURFACE_RE.finditer(raw_text):
        unit = match.group("unit")
        if unit not in units or not (
            _eligible_match_boundary(raw_text, match)
            or _eligible_embedded_fixed_suffix(raw_text, match)
        ):
            continue
        if not _is_supported_tail(unit, match.group("tail")):
            continue
        if unit == "점" and _match_has_decimal(match):
            # Decimal `점` already has one shared Sino/spacing canonical under
            # the existing registered-suffix owner.
            continue
        if not _is_valid_supported_number_match(match):
            continue
        if match.group("prefix") == "제":
            # Existing explicit ordinal/preserve owners keep their canonical.
            continue
        if _preceded_by_spaced_ordinal(
            raw_text, match.start()
        ):
            continue
        decision = _evaluate_standard_match(raw_text, match)
        if decision is not None:
            candidates.append(decision)
    return candidates


def _evaluate_standard_match(
    raw_text: str, match: re.Match[str]
) -> SurfaceCandidate | None:
    unit = match.group("unit")
    tail = match.group("tail")
    previous = _previous_word(raw_text, match.start())
    following = _next_word(raw_text, match.end())

    if unit == "조" and (
        _is_existing_jo_owner_context(raw_text, match)
        or _jo_specific_owner_context(
            previous,
            following,
            tail,
            match.end() == len(raw_text),
        )
        or _is_followed_by_large_unit_number(raw_text, match)
    ):
        return None

    if unit == "가지":
        if tail not in _GAJI_TAILS:
            return _deferred(raw_text, match, "number_plus_gaji_unresolved", "unsupported_attached_tail")
        return _confirmed(
            raw_text,
            match,
            "kind_or_item_count",
            "native",
            "가지_direct_count_structure",
        )

    if unit == "분":
        if previous in PERSON_BUN_NOUNS:
            return _confirmed(
                raw_text,
                match,
                "honorific_person_count",
                "native_1_to_99",
                f"person_noun:{previous}",
            )
        if _starts_with_anchor(following, BUN_TIME_REMAINING_ACTIONS):
            return _confirmed(
                raw_text,
                match,
                "duration_minute",
                "sino",
                f"remaining_action:{following}",
            )
        return _deferred(raw_text, match, "time_or_person", "exact_anchor_missing")

    if unit == "번":
        fixed_suffix = _matching_fixed_suffix(unit, tail)
        if fixed_suffix is not None:
            return _confirmed(
                raw_text,
                match,
                "fixed_identifier_suffix",
                "sino",
                f"fixed_suffix:번{fixed_suffix}",
            )
        identifier_noun = _matching_noun_anchor(
            following, BEON_IDENTIFIER_NOUNS
        )
        if identifier_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "identifier",
                "sino",
                f"identifier_noun:{identifier_noun}",
            )
        if (
            previous in BEON_OCCURRENCE_MARKERS
            or tail in {"씩", "이나"}
            or _starts_with_anchor(following, BEON_OCCURRENCE_ACTIONS)
        ):
            anchor = (
                f"occurrence_marker:{previous}"
                if previous in BEON_OCCURRENCE_MARKERS
                else f"occurrence_tail:{tail}"
                if tail in {"씩", "이나"}
                else f"occurrence_action:{following}"
            )
            return _confirmed(
                raw_text, match, "occurrence", "native", anchor
            )
        return _deferred(
            raw_text, match, "occurrence_or_identifier", "exact_anchor_missing"
        )

    if unit == "차":
        fixed_suffix = _matching_fixed_suffix(unit, tail)
        if fixed_suffix is not None:
            return _confirmed(
                raw_text,
                match,
                "fixed_numeric_compound",
                "sino",
                f"fixed_suffix:차{fixed_suffix}",
            )
        return _confirmed(
            raw_text,
            match,
            "sequence_number",
            "sino",
            "bare_sequence_unit:차",
        )

    if unit == "위":
        fixed_suffix = _matching_fixed_suffix(unit, tail)
        if fixed_suffix is not None:
            return _confirmed(
                raw_text,
                match,
                "fixed_numeric_compound",
                "sino",
                f"fixed_suffix:위{fixed_suffix}",
            )
        return _confirmed(
            raw_text,
            match,
            "rank_number",
            "sino",
            "bare_rank_unit:위",
        )

    if unit == "점":
        previous_score_anchor = _matching_noun_anchor(
            previous, JEOM_SCORE_ANCHORS
        )
        following_score_anchor = _matching_noun_anchor(
            following, JEOM_SCORE_ANCHORS
        )
        if previous_score_anchor is not None or following_score_anchor is not None:
            anchor = (
                f"score_anchor:{previous_score_anchor}"
                if previous_score_anchor is not None
                else f"score_anchor:{following_score_anchor}"
            )
            return _confirmed(raw_text, match, "score", "sino", anchor)
        item_noun = _matching_noun_anchor(previous, JEOM_ITEM_NOUNS)
        item_action = _starts_with_anchor(following, JEOM_ITEM_ACTIONS)
        if item_action and (
            item_noun is not None or tail.startswith(("이", "가", "을", "를"))
        ):
            return _confirmed(
                raw_text,
                match,
                "item_count",
                "native",
                (
                    f"item_noun_action:{item_noun}+{following}"
                    if item_noun is not None
                    else f"item_action:{following}"
                ),
            )
        if _match_has_decimal(match):
            return _confirmed(
                raw_text,
                match,
                "decimal_score_or_item",
                "sino",
                "decimal_shared_reading_and_spacing",
            )
        return _deferred(
            raw_text, match, "score_or_item", "exact_anchor_pair_missing"
        )

    if unit == "조":
        if _is_existing_jo_owner_context(raw_text, match) or _jo_specific_owner_context(
            previous, following, tail, match.end() == len(raw_text)
        ) or _is_followed_by_large_unit_number(raw_text, match):
            return None
        if (
            previous in JO_GROUP_MARKERS
            or tail in {"로", "으로"} and _starts_with_anchor(following, JO_GROUP_ACTIONS)
            or _starts_with_anchor(following, JO_GROUP_ACTIONS)
        ):
            anchor = (
                f"group_marker:{previous}"
                if previous in JO_GROUP_MARKERS
                else f"group_action:{following}"
            )
            return _confirmed(
                raw_text, match, "group_count", "native", anchor
            )
        return _deferred(
            raw_text, match, "large_number_or_group", "financial_or_group_anchor_missing"
        )

    if unit == "대":
        from engine.span_engine.numeric_dae import (
            explicit_numeric_dae_counter_context_reason,
        )

        machine_reason = explicit_numeric_dae_counter_context_reason(
            raw_text, SourceSpan(match.start(), match.end("unit"))
        )
        if machine_reason is not None:
            return _confirmed(
                raw_text,
                match,
                "machine_count",
                "native",
                machine_reason,
            )
        machine_location = _matching_noun_anchor(
            previous, DAE_MACHINE_LOCATION_NOUNS
        )
        if machine_location is not None and _starts_with_anchor(
            following, DAE_MACHINE_LOCATION_ACTIONS
        ):
            return _confirmed(
                raw_text,
                match,
                "machine_count",
                "native",
                f"machine_location_action:{machine_location}+{following}",
            )
        generation_noun = _matching_noun_anchor(
            previous, DAE_GENERATION_NOUNS
        )
        if tail.startswith("째") or generation_noun is not None:
            anchor = (
                "generation_suffix:째"
                if tail.startswith("째")
                else f"generation_noun:{generation_noun}"
            )
            return _confirmed(
                raw_text, match, "generation", "sino", anchor
            )
        normalized = normalize_integer_text(match.group("number"))
        value = int(normalized) if normalized is not None else -1
        age_noun = _matching_noun_anchor(following, DAE_AGE_NOUNS)
        if value > 0 and value % 10 == 0 and age_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "age_band",
                "sino",
                f"age_anchor:{age_noun}",
            )
        major_item_noun = _matching_noun_anchor(
            following, DAE_MAJOR_ITEM_NOUNS
        )
        if major_item_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "major_item",
                "sino",
                f"major_item_noun:{major_item_noun}",
            )
        if value >= 40:
            # Existing approved threshold owner and renderer remain canonical.
            return None
        return _deferred(
            raw_text, match, "dae_ambiguous", "exact_dae_anchor_missing"
        )

    if unit == "부":
        sequence_noun = _matching_noun_anchor(previous, BU_SEQUENCE_NOUNS)
        if tail.startswith("작") or sequence_noun is not None:
            anchor = (
                "fixed_suffix:부작"
                if tail.startswith("작")
                else f"sequence_noun:{sequence_noun}"
            )
            return _confirmed(
                raw_text, match, "part_or_sequence", "sino", anchor
            )
        document_noun = _matching_noun_anchor(previous, BU_DOCUMENT_NOUNS)
        if document_noun is not None and _starts_with_anchor(
            following, BU_QUANTITY_ACTIONS
        ):
            return _confirmed(
                raw_text,
                match,
                "document_copy_count",
                "native",
                f"document_noun_action:{document_noun}+{following}",
            )
        return _deferred(
            raw_text, match, "copy_or_sequence", "exact_anchor_pair_missing"
        )

    if unit == "동":
        following_identifier = _matching_noun_anchor(
            following, DONG_IDENTIFIER_NOUNS
        )
        previous_identifier = _matching_noun_anchor(
            previous, DONG_IDENTIFIER_NOUNS
        )
        if (
            _is_dong_ho_structure(raw_text, match)
            or following_identifier is not None
            or previous_identifier in DONG_PREVIOUS_IDENTIFIER_NOUNS
        ):
            anchor = (
                "fixed_structure:N동_N호"
                if _is_dong_ho_structure(raw_text, match)
                else f"identifier_noun:{following_identifier or previous_identifier}"
            )
            return _confirmed(
                raw_text, match, "building_identifier", "sino", anchor
            )
        building_noun = _matching_noun_anchor(
            previous, DONG_BUILDING_NOUNS
        )
        if building_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "building_count",
                "native",
                f"building_noun:{building_noun}",
            )
        return _deferred(
            raw_text, match, "identifier_or_building_count", "exact_anchor_pair_missing"
        )

    if unit == "호":
        identifier_noun = _matching_noun_anchor(
            following, HO_IDENTIFIER_NOUNS
        )
        previous_identifier_noun = _matching_noun_anchor(
            previous, HO_IDENTIFIER_NOUNS
        )
        if (
            tail.startswith(("실", "선"))
            or _is_dong_ho_structure(raw_text, match)
            or _is_gwon_ho_structure(raw_text, match)
            or identifier_noun is not None
            or previous_identifier_noun is not None
        ):
            anchor = (
                f"fixed_suffix:호{tail[:1]}"
                if tail.startswith(("실", "선"))
                else "fixed_structure:N동_N호"
                if _is_dong_ho_structure(raw_text, match)
                else "fixed_structure:N권_N호"
                if _is_gwon_ho_structure(raw_text, match)
                else f"identifier_noun:{identifier_noun or previous_identifier_noun}"
            )
            return _confirmed(
                raw_text, match, "identifier", "sino", anchor
            )
        household_noun = _matching_noun_anchor(
            previous, HO_HOUSEHOLD_NOUNS
        )
        if household_noun is not None and _starts_with_anchor(
            following, HO_QUANTITY_ACTIONS
        ):
            return _confirmed(
                raw_text,
                match,
                "household_count",
                "native",
                f"household_noun_action:{household_noun}+{following}",
            )
        return _deferred(
            raw_text, match, "identifier_or_household_count", "exact_anchor_pair_missing"
        )

    if unit == "판":
        game_noun = _matching_noun_anchor(previous, PAN_GAME_NOUNS)
        exact_game_action = (
            tail in {"을", "를"}
            and _starts_with_anchor(following, PAN_GAME_ACTIONS)
        )
        if game_noun is not None or exact_game_action:
            return _confirmed(
                raw_text,
                match,
                "game_count",
                "native",
                (
                    f"game_noun:{game_noun}"
                    if game_noun is not None
                    else f"fixed_game_action:{following}"
                ),
            )
        edition_noun = _matching_noun_anchor(previous, PAN_EDITION_NOUNS)
        if edition_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "edition",
                "sino",
                f"edition_noun:{edition_noun}",
            )
        return _deferred(
            raw_text, match, "game_or_edition", "exact_anchor_missing"
        )

    if unit == "단":
        grade_noun = _matching_noun_anchor(previous, DAN_GRADE_NOUNS)
        if tail.startswith("계") or grade_noun is not None:
            anchor = (
                "fixed_suffix:단계"
                if tail.startswith("계")
                else f"grade_noun:{grade_noun}"
            )
            return _confirmed(
                raw_text, match, "grade_or_stage", "sino", anchor
            )
        stack_noun = _matching_noun_anchor(previous, DAN_STACK_NOUNS)
        if following == "선반" or stack_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "stack_count",
                "native",
                (
                    "fixed_structure:N단_선반"
                    if following == "선반"
                    else f"stack_noun:{stack_noun}"
                ),
            )
        if (
            previous == "총"
            or tail.startswith(("로", "으로"))
            and _starts_with_anchor(following, DAN_STACK_ACTIONS)
        ):
            anchor = (
                "quantity_marker:총"
                if previous == "총"
                else f"stack_action:{following}"
            )
            return _confirmed(
                raw_text, match, "stack_count", "native", anchor
            )
        return _deferred(
            raw_text, match, "grade_or_stack_count", "exact_anchor_missing"
        )

    if unit == "등":
        rank_noun = _matching_noun_anchor(previous, DEUNG_RANK_NOUNS)
        if tail.startswith("급") or rank_noun is not None:
            anchor = (
                "fixed_suffix:등급"
                if tail.startswith("급")
                else f"rank_noun:{rank_noun}"
            )
            return _confirmed(
                raw_text, match, "rank_or_grade", "sino", anchor
            )
        light_noun = _matching_noun_anchor(previous, DEUNG_LIGHT_NOUNS)
        if light_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "light_count",
                "native",
                (
                    f"light_noun_action:{light_noun}+{following}"
                    if _starts_with_anchor(following, DEUNG_LIGHT_ACTIONS)
                    else f"light_noun:{light_noun}"
                ),
            )
        return _deferred(
            raw_text, match, "rank_or_light_count", "exact_anchor_pair_missing"
        )

    if unit == "척":
        ship_noun = _matching_noun_anchor(previous, CHEOK_SHIP_NOUNS)
        if ship_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "ship_count",
                "native",
                f"ship_noun:{ship_noun}",
            )
        ship_location = _matching_noun_anchor(
            previous, CHEOK_SHIP_LOCATION_NOUNS
        )
        if ship_location is not None:
            return _confirmed(
                raw_text,
                match,
                "ship_count",
                "native",
                f"ship_location:{ship_location}",
            )
        length_noun = _matching_noun_anchor(previous, CHEOK_LENGTH_NOUNS)
        if length_noun is not None or _has_left_clause_anchor(
            raw_text, match.start(), CHEOK_LENGTH_NOUNS
        ):
            return _confirmed(
                raw_text,
                match,
                "length_measure",
                "sino",
                (
                    f"length_noun:{length_noun}"
                    if length_noun is not None
                    else "left_clause_length_noun"
                ),
            )
        return _deferred(
            raw_text, match, "ship_or_length", "exact_anchor_missing"
        )

    if unit == "장":
        if _is_followed_by_numbered_unit(raw_text, match, "절"):
            return _confirmed(
                raw_text,
                match,
                "chapter_number",
                "sino",
                "fixed_structure:N장_N절",
            )
        chapter_noun = _matching_noun_anchor(
            previous, JANG_CHAPTER_NOUNS
        )
        if chapter_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "chapter_number",
                "sino",
                f"chapter_noun:{chapter_noun}",
            )
        sheet_noun = _matching_noun_anchor(previous, JANG_SHEET_NOUNS)
        if sheet_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "sheet_count",
                "native",
                f"sheet_noun:{sheet_noun}",
            )
        return _deferred(
            raw_text, match, "sheet_or_chapter", "exact_anchor_missing"
        )

    if unit == "권":
        if _is_followed_by_numbered_unit(raw_text, match, "호"):
            return _confirmed(
                raw_text,
                match,
                "volume_number",
                "sino",
                "fixed_structure:N권_N호",
            )
        volume_noun = _matching_noun_anchor(
            previous, GWON_VOLUME_NOUNS
        )
        if volume_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "volume_number",
                "sino",
                f"volume_noun:{volume_noun}",
            )
        book_noun = _matching_noun_anchor(previous, GWON_BOOK_NOUNS)
        if book_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "book_count",
                "native",
                f"book_noun:{book_noun}",
            )
        return _deferred(
            raw_text, match, "book_or_volume", "exact_anchor_missing"
        )

    if unit == "편":
        structure_noun = _matching_noun_anchor(
            previous, PYEON_STRUCTURE_NOUNS
        )
        if structure_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "part_number",
                "sino",
                f"structure_noun:{structure_noun}",
            )
        work_noun = _matching_noun_anchor(previous, PYEON_WORK_NOUNS)
        if work_noun is not None:
            return _confirmed(
                raw_text,
                match,
                "work_count",
                "native",
                f"work_noun:{work_noun}",
            )
        return _deferred(
            raw_text, match, "work_or_part_number", "exact_anchor_missing"
        )

    if unit == "층":
        location_noun = _matching_noun_anchor(
            following, CHEUNG_LOCATION_NOUNS
        )
        if (
            tail.startswith(("에", "에서"))
            or previous in CHEUNG_LOCATION_PREFIXES
            or location_noun is not None
            or (
                _matching_noun_anchor(previous, CHEUNG_ACCESS_NOUNS)
                is not None
                and _starts_with_anchor(
                    following, CHEUNG_MOVEMENT_ACTIONS
                )
            )
        ):
            anchor = (
                f"location_particle:{tail}"
                if tail.startswith(("에", "에서"))
                else f"location_prefix:{previous}"
                if previous in CHEUNG_LOCATION_PREFIXES
                else f"access_movement:{previous}+{following}"
                if _matching_noun_anchor(previous, CHEUNG_ACCESS_NOUNS)
                is not None
                else f"location_noun:{location_noun}"
            )
            return _confirmed(
                raw_text, match, "floor_location", "sino", anchor
            )
        return _deferred(
            raw_text, match, "floor_location_or_count", "location_anchor_missing"
        )
    return None


def parse_contextual_number_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != OWNER:
        return None
    decision = candidate.metadata.get("contextual_decision")
    number_span = candidate.metadata.get("number_span")
    amount_span = candidate.metadata.get("amount_span")
    unit_tail_span = candidate.metadata.get("unit_tail_span")
    if (
        not isinstance(decision, ContextualDecision)
        or not isinstance(number_span, SourceSpan)
        or not isinstance(amount_span, SourceSpan)
        or not isinstance(unit_tail_span, SourceSpan)
    ):
        return None
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    if decision.decision is ContextualDecisionKind.DEFERRED:
        pieces = _original_pieces(raw_text, candidate)
        return Surface(
            surface_type=candidate.surface_type or "CONTEXTUAL_NUMBER_UNIT_DEFERRED_SURFACE",
            owner=OWNER,
            raw=raw,
            span=candidate.core_span,
            reading=raw,
            render_pieces=pieces,
            metadata={"reason": candidate.reason, "contextual_decision": decision},
        )

    number_reading = candidate.metadata.get("number_reading")
    separator = candidate.metadata.get("separator")
    if not isinstance(number_reading, str) or not isinstance(separator, str):
        return None
    pieces = [
        RenderPiece(
            text=number_reading,
            provenance="GENERATED_READING",
            source_span=amount_span,
            owner=OWNER,
            metadata={"surface_type": candidate.surface_type},
        )
    ]
    if separator:
        pieces.append(
            RenderPiece(
                text=separator,
                provenance=(
                    "GENERATED_PUNCT"
                    if separator == SPOKEN_NUMERIC_BOUNDARY
                    else "GENERATED_READING"
                ),
                source_span=candidate.metadata.get("source_space_span") or number_span,
                owner=OWNER,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    pieces.append(
        RenderPiece(
            text=raw_text[unit_tail_span.start : unit_tail_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=unit_tail_span,
            owner=OWNER,
            metadata={"surface_type": candidate.surface_type},
        )
    )
    return Surface(
        surface_type=candidate.surface_type or "CONTEXTUAL_NUMBER_UNIT_CONFIRMED_SURFACE",
        owner=OWNER,
        raw=raw,
        span=candidate.core_span,
        reading="".join(piece.text for piece in pieces),
        render_pieces=pieces,
        metadata={"reason": candidate.reason, "contextual_decision": decision},
    )


def build_contextual_decision_logs(
    candidates: list[SurfaceCandidate], actual_final_output: str
) -> list[dict[str, Any]]:
    if not isinstance(candidates, list):
        raise TypeError("candidates must be list[SurfaceCandidate]")
    if not isinstance(actual_final_output, str):
        raise TypeError("actual_final_output must be str")
    logs: list[dict[str, Any]] = []
    for candidate in candidates:
        decision = candidate.metadata.get("contextual_decision")
        if candidate.owner != OWNER or not isinstance(decision, ContextualDecision):
            continue
        logs.append(
            {
                "rule_version": decision.rule_version,
                "input_surface": candidate.metadata.get("input_surface"),
                "source_span": candidate.core_span,
                "unit": decision.unit,
                "decision": decision.decision.value,
                "semantic_type": decision.semantic_type,
                "confirmed_reading": decision.confirmed_reading,
                "candidate_readings": list(decision.candidate_readings),
                "matched_anchor": decision.matched_anchor,
                "blocking_reason": decision.blocking_reason,
                "owner": OWNER,
                "owner_priority": decision.owner_priority,
                "reentry_blocked": decision.reentry_blocked,
                "existing_engine_result": decision.existing_engine_result,
                "new_rule_result": decision.new_rule_result,
                "actual_final_output": actual_final_output,
            }
        )
    return logs


def _confirmed(
    raw_text: str,
    match: re.Match[str],
    semantic_type: str,
    reading_mode: str,
    matched_anchor: str,
) -> SurfaceCandidate | None:
    unit = match.group("unit")
    raw_number = match.group("number")
    number_reading = _number_reading(
        raw_number,
        unit,
        reading_mode,
        prefix=match.group("prefix"),
    )
    if number_reading is None:
        return None
    if _eligible_embedded_fixed_suffix(raw_text, match):
        number_reading = f" {number_reading}"
    separator = _canonical_separator(match, semantic_type)
    claim_end: int | None = None
    fixed_suffix = _matching_fixed_suffix(unit, match.group("tail"))
    if semantic_type in {"fixed_identifier_suffix", "fixed_numeric_compound"}:
        if fixed_suffix is None:
            return None
        # Claim only the registered lexical suffix.  A following particle or
        # ending remains an independent, source-exact Korean span.
        claim_end = match.end("unit") + len(fixed_suffix)
    return _candidate(
        raw_text,
        match,
        decision_kind=ContextualDecisionKind.CONFIRMED,
        semantic_type=semantic_type,
        number_reading=number_reading,
        separator=separator,
        matched_anchor=matched_anchor,
        claim_end=claim_end,
    )


def _deferred(
    raw_text: str,
    match: re.Match[str],
    semantic_type: str,
    blocking_reason: str,
) -> SurfaceCandidate | None:
    if _uses_residual_sino_reading(match):
        confirmed = _confirmed(
            raw_text,
            match,
            "residual_numeric_unit",
            "sino",
            "residual_numeric_policy",
        )
        if confirmed is not None:
            return confirmed
    return _candidate(
        raw_text,
        match,
        decision_kind=ContextualDecisionKind.DEFERRED,
        semantic_type=semantic_type,
        blocking_reason=blocking_reason,
    )


def _candidate(
    raw_text: str,
    match: re.Match[str],
    *,
    decision_kind: ContextualDecisionKind,
    semantic_type: str,
    number_reading: str | None = None,
    separator: str = "",
    matched_anchor: str | None = None,
    blocking_reason: str | None = None,
    claim_end: int | None = None,
) -> SurfaceCandidate:
    effective_end = match.end() if claim_end is None else claim_end
    span = SourceSpan(match.start(), effective_end)
    prefix_span = (
        SourceSpan(match.start("prefix"), match.end("prefix"))
        if match.group("prefix")
        else None
    )
    number_span = SourceSpan(match.start("number"), match.end("number"))
    amount_span = SourceSpan(
        match.start("prefix") if match.group("prefix") else match.start("number"),
        match.end("number"),
    )
    source_space_span = (
        SourceSpan(match.start("space"), match.end("space"))
        if match.group("space")
        else None
    )
    unit_tail_span = SourceSpan(match.start("unit"), effective_end)
    unit = match.group("unit")
    tail = raw_text[match.end("unit") : effective_end]
    raw_surface = raw_text[match.start() : effective_end]
    new_result = (
        f"{number_reading}{separator}{unit}{tail}"
        if decision_kind is ContextualDecisionKind.CONFIRMED
        and number_reading is not None
        else raw_surface
    )
    legacy_result = _legacy_result(match, semantic_type)
    candidate_readings = (
        ({"reading": new_result, "semantic_type": semantic_type},)
        if decision_kind is ContextualDecisionKind.CONFIRMED
        else _ambiguous_candidates(match)
    )
    decision = ContextualDecision(
        rule_version=RULE_VERSION,
        unit=unit,
        decision=decision_kind,
        semantic_type=semantic_type,
        confirmed_reading=(
            new_result
            if decision_kind is ContextualDecisionKind.CONFIRMED
            else None
        ),
        candidate_readings=candidate_readings,
        matched_anchor=matched_anchor,
        blocking_reason=blocking_reason,
        owner_priority=OWNER_PRIORITY,
        reentry_blocked=True,
        existing_engine_result=legacy_result,
        new_rule_result=new_result,
    )
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner=OWNER,
        surface_type=(
            "CONTEXTUAL_NUMBER_UNIT_CONFIRMED_SURFACE"
            if decision_kind is ContextualDecisionKind.CONFIRMED
            else "CONTEXTUAL_NUMBER_UNIT_DEFERRED_SURFACE"
        ),
        reason=(
            "contextual_number_unit_confirmed"
            if decision_kind is ContextualDecisionKind.CONFIRMED
            else "contextual_number_unit_deferred"
        ),
        metadata={
            "claim_type": (
                "preserve"
                if decision_kind is ContextualDecisionKind.DEFERRED
                else "surface"
            ),
            "contextual_decision": decision,
            "input_surface": raw_surface,
            "prefix_span": prefix_span,
            "number_span": number_span,
            "amount_span": amount_span,
            "source_space_span": source_space_span,
            "unit_tail_span": unit_tail_span,
            "number_reading": number_reading,
            "separator": separator,
        },
    )


def _original_pieces(
    raw_text: str, candidate: SurfaceCandidate
) -> list[RenderPiece]:
    prefix_span = candidate.metadata.get("prefix_span")
    number_span = candidate.metadata["number_span"]
    source_space_span = candidate.metadata.get("source_space_span")
    unit_tail_span = candidate.metadata["unit_tail_span"]
    pieces: list[RenderPiece] = []
    if isinstance(prefix_span, SourceSpan):
        pieces.append(
            RenderPiece(
                text=raw_text[prefix_span.start : prefix_span.end],
                provenance=(
                    "ORIGINAL_KOREAN"
                    if raw_text[prefix_span.start : prefix_span.end] == "제"
                    else "ORIGINAL_BOUNDARY"
                ),
                source_span=prefix_span,
                owner=OWNER,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    pieces.append(
        RenderPiece(
            text=raw_text[number_span.start : number_span.end],
            provenance="ORIGINAL_BOUNDARY",
            source_span=number_span,
            owner=OWNER,
            metadata={"surface_type": candidate.surface_type},
        )
    )
    if isinstance(source_space_span, SourceSpan):
        pieces.append(
            RenderPiece(
                text=raw_text[source_space_span.start : source_space_span.end],
                provenance="ORIGINAL_SPACE",
                source_span=source_space_span,
                owner=OWNER,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    pieces.append(
        RenderPiece(
            text=raw_text[unit_tail_span.start : unit_tail_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=unit_tail_span,
            owner=OWNER,
            metadata={"surface_type": candidate.surface_type},
        )
    )
    return pieces


def _number_reading(
    raw_number: str,
    unit: str,
    mode: str,
    *,
    prefix: str | None = None,
) -> str | None:
    if prefix in SIGNED_NUMERIC_SIGN_ALIASES or "." in raw_number:
        raw_amount = f"{prefix or ''}{raw_number}"
        core = parse_signed_numeric_core(raw_amount)
        if core is None:
            return None
        return render_signed_numeric(core)
    if mode == "sino":
        if unit == "분":
            return read_sino_time_suffix_number_text(raw_number)
        return read_spaced_integer_text(raw_number)
    if mode == "native_1_to_99":
        reading = counter_number_reading(raw_number, "사람")
        return reading.removesuffix(SPOKEN_NUMERIC_BOUNDARY) if reading is not None else None
    if unit == "가지":
        normalized = normalize_integer_text(raw_number)
        if normalized is None:
            return None
        value = int(normalized)
        if value == 0:
            return read_spaced_integer_text(raw_number)
        if value <= 99:
            return native_number_under_100(value)
        reading = counter_number_reading(raw_number, "가지")
        return reading.removesuffix(SPOKEN_NUMERIC_BOUNDARY) if reading is not None else None
    reading = counter_number_reading(raw_number, "개")
    return reading.removesuffix(SPOKEN_NUMERIC_BOUNDARY) if reading is not None else None


def _canonical_separator(match: re.Match[str], semantic_type: str) -> str:
    unit = match.group("unit")
    if semantic_type == "residual_numeric_unit":
        return SPOKEN_NUMERIC_BOUNDARY
    if semantic_type == "major_item":
        return match.group("space")
    if semantic_type in {"fixed_identifier_suffix", "fixed_numeric_compound"}:
        return SPOKEN_NUMERIC_BOUNDARY
    if semantic_type == "duration_minute":
        return (
            SPOKEN_NUMERIC_BOUNDARY
            if _match_has_decimal(match)
            else match.group("space")
        )
    if semantic_type in {
        "kind_or_item_count",
        "honorific_person_count",
        "occurrence",
        "item_count",
        "group_count",
        "document_copy_count",
        "building_count",
        "household_count",
        "game_count",
        "stack_count",
        "light_count",
        "ship_count",
        "sheet_count",
        "book_count",
        "work_count",
    }:
        return SPOKEN_NUMERIC_BOUNDARY
    if unit in {"번", "분", "조", "부", "단", "등"}:
        return match.group("space")
    if unit == "대":
        return SPOKEN_NUMERIC_BOUNDARY
    return SPOKEN_NUMERIC_BOUNDARY


def _legacy_result(
    match: re.Match[str], semantic_type: str
) -> str:
    unit = match.group("unit")
    raw_number = match.group("number")
    tail = match.group("tail")
    if unit in {"판", "척", "장", "권", "편"}:
        reading = counter_number_reading(raw_number, unit)
        return (
            f"{reading}{unit}{tail}"
            if reading is not None
            else match.group(0)
        )
    if unit == "대":
        if semantic_type == "machine_count":
            reading = counter_number_reading(raw_number, unit)
            return (
                f"{reading}{unit}{tail}"
                if reading is not None
                else match.group(0)
            )
        return match.group(0)
    reading = (
        read_sino_time_suffix_number_text(raw_number)
        if unit == "분"
        else read_spaced_integer_text(raw_number)
    )
    if reading is None:
        return match.group(0)
    separator = (
        " "
        if unit in {"점", "동", "호", "층"}
        else match.group("space")
    )
    return f"{reading}{separator}{unit}{tail}"


def _ambiguous_candidates(
    match: re.Match[str],
) -> tuple[dict[str, str], ...]:
    unit = match.group("unit")
    number = match.group("number")
    tail = match.group("tail")
    source_space = match.group("space")
    native_mode = "native_1_to_99" if unit == "분" else "native"
    prefix = match.group("prefix")
    native = _number_reading(number, unit, native_mode, prefix=prefix)
    sino = _number_reading(number, unit, "sino", prefix=prefix)
    if native is None or sino is None:
        return ()
    semantics = {
        "분": ("honorific_person_count", "time"),
        "번": ("occurrence", "identifier"),
        "점": ("item_count", "score"),
        "조": ("group_count", "large_number"),
        "대": ("machine_count", "generation_or_age"),
        "가지": ("kind_or_item_count", "unresolved"),
        "부": ("document_copy_count", "part_or_sequence"),
        "동": ("building_count", "building_identifier"),
        "호": ("household_count", "identifier"),
        "판": ("game_count", "edition"),
        "단": ("stack_count", "grade_or_stage"),
        "등": ("light_count", "rank_or_grade"),
        "척": ("ship_count", "length_measure"),
        "장": ("sheet_count", "chapter_number"),
        "권": ("book_count", "volume_number"),
        "편": ("work_count", "part_number"),
        "층": ("floor_count", "floor_location"),
        "차": ("sequence_number", "sequence_number"),
        "위": ("rank_number", "rank_number"),
    }
    native_semantic, sino_semantic = semantics[unit]
    sino_separator = (
        source_space
        if unit in {"분", "번", "조", "부", "단", "등"}
        else SPOKEN_NUMERIC_BOUNDARY
    )
    return (
        {
            "reading": f"{native}{SPOKEN_NUMERIC_BOUNDARY}{unit}{tail}",
            "semantic_type": native_semantic,
        },
        {
            "reading": f"{sino}{sino_separator}{unit}{tail}",
            "semantic_type": sino_semantic,
        },
    )


def _ambiguous_semantic_type(unit: str) -> str:
    return {
        "가지": "number_plus_gaji_unresolved",
        "분": "time_or_person",
        "번": "occurrence_or_identifier",
        "점": "score_or_item",
        "조": "large_number_or_group",
        "대": "dae_ambiguous",
        "부": "copy_or_sequence",
        "동": "identifier_or_building_count",
        "호": "identifier_or_household_count",
        "판": "game_or_edition",
        "단": "grade_or_stack_count",
        "등": "rank_or_light_count",
        "척": "ship_or_length",
        "장": "sheet_or_chapter",
        "권": "book_or_volume",
        "편": "work_or_part_number",
        "층": "floor_location_or_count",
        "차": "sequence_number",
        "위": "rank_number",
    }[unit]


def _is_existing_specific_decimal(
    raw_text: str, unit: str, match: re.Match[str]
) -> bool:
    if (
        unit == "점"
        and match.group("prefix") is None
        and "." in match.group("number")
        and not any(char.isalpha() for char in match.group("number"))
        and normalize_integer_text(match.group("number").split(".", 1)[0])
        is not None
    ):
        return True
    return (
        unit == "조"
        and "." in match.group("number")
        and _is_existing_jo_owner_context(raw_text, match)
    )


def _is_valid_unsigned_integer_match(match: re.Match[str]) -> bool:
    if match.group("prefix") is not None:
        return False
    number = match.group("number")
    if "." in number or any(char.isalpha() for char in number):
        return False
    normalized = normalize_integer_text(number)
    if normalized is None:
        return False
    return normalized == "0" or not normalized.startswith("0")


def _is_valid_supported_number_match(match: re.Match[str]) -> bool:
    if _is_valid_unsigned_integer_match(match):
        return True
    prefix = match.group("prefix")
    number = match.group("number")
    if prefix == "제" or any(char.isalpha() for char in number):
        return False
    core = parse_signed_numeric_core(f"{prefix or ''}{number}")
    return core is not None


def _uses_residual_sino_reading(match: re.Match[str]) -> bool:
    prefix = match.group("prefix")
    if prefix == "제":
        return False
    number = match.group("number")
    if any(char.isalpha() for char in number):
        return False
    core = parse_signed_numeric_core(f"{prefix or ''}{number}")
    if core is None:
        return False
    if prefix in SIGNED_NUMERIC_SIGN_ALIASES or core.has_decimal:
        return True
    value = int(core.integer_digits)
    if value == 0:
        return True
    threshold = (
        _NATIVE_THROUGH_99_RESIDUAL_SINO_THRESHOLD
        if match.group("unit") in _NATIVE_THROUGH_99_RESIDUAL_UNITS
        else _DEFAULT_RESIDUAL_SINO_THRESHOLD
    )
    return value >= threshold


def _match_has_decimal(match: re.Match[str]) -> bool:
    return "." in match.group("number")


def _blocking_reason(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    number = match.group("number")
    if prefix == "제":
        return "ordinal_prefix_not_supported"
    if prefix in SIGNED_NUMERIC_SIGN_ALIASES:
        return "signed_number_not_supported"
    if any(char.isalpha() for char in number):
        return "alphanumeric_numeric_surface"
    if "." in number:
        return "decimal_not_supported"
    normalized = normalize_integer_text(number)
    if normalized is None:
        return "malformed_integer_surface"
    if len(normalized) > 1 and normalized.startswith("0"):
        return "leading_zero_not_supported"
    return "unsupported_numeric_surface"


def _eligible_match_boundary(
    raw_text: str, match: re.Match[str]
) -> bool:
    start, end = match.start(), match.end()
    prev = raw_text[start - 1] if start > 0 else None
    following = raw_text[end] if end < len(raw_text) else None
    if match.group("prefix") in SIGNED_NUMERIC_SIGN_ALIASES and not valid_unary_sign_left_boundary(
        raw_text, start
    ):
        return False
    if prev in _RANGE_DELIMITERS:
        before_delimiter = raw_text[start - 2] if start >= 2 else None
        if before_delimiter is None or (
            before_delimiter.isascii() and before_delimiter.isdigit()
        ):
            return False
    if prev is not None and (
        prev in _IDENTIFIER_BOUNDARY_BLOCKERS
        or prev.isascii() and prev.isalnum()
    ):
        return False
    if following is not None:
        if following in {"_", "/"}:
            return False
        if following == ".":
            after_dot = raw_text[end + 1] if end + 1 < len(raw_text) else None
            if after_dot is not None and (
                after_dot == "."
                or after_dot.isascii()
                and after_dot.isalnum()
            ):
                return False
        elif following.isascii() and following.isalnum():
            return False
    return True


def _eligible_embedded_fixed_suffix(
    raw_text: str, match: re.Match[str]
) -> bool:
    if match.group("unit") != "번" or match.group("prefix") is not None:
        return False
    if _matching_fixed_suffix("번", match.group("tail")) is None:
        return False
    start, end = match.start(), match.end()
    if start == 0 or not ("가" <= raw_text[start - 1] <= "힣"):
        return False
    if raw_text[start - 1] == "제":
        return False
    following = raw_text[end] if end < len(raw_text) else None
    return following is None or not (
        following.isascii() and following.isalnum()
    )


def _previous_word(raw_text: str, start: int) -> str:
    end = start
    while end > 0 and raw_text[end - 1].isspace():
        end -= 1
    word_start = end
    while word_start > 0 and "가" <= raw_text[word_start - 1] <= "힣":
        word_start -= 1
    return raw_text[word_start:end]


def _next_word(raw_text: str, end: int) -> str:
    start = end
    while start < len(raw_text) and raw_text[start].isspace():
        start += 1
    word_end = start
    while word_end < len(raw_text) and "가" <= raw_text[word_end] <= "힣":
        word_end += 1
    return raw_text[start:word_end]


def _starts_with_anchor(word: str, anchors: frozenset[str]) -> bool:
    return any(word.startswith(anchor) for anchor in anchors)


def _matching_noun_anchor(
    word: str, anchors: frozenset[str]
) -> str | None:
    particles = (
        "에서",
        "에서는",
        "으로",
        "에게",
        "에는",
        "의",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "로",
        "도",
        "만",
        "와",
        "과",
    )
    for anchor in anchors:
        if word == anchor or any(word == f"{anchor}{particle}" for particle in particles):
            return anchor
    return None


def _has_left_clause_anchor(
    raw_text: str,
    start: int,
    anchors: frozenset[str],
) -> bool:
    boundary = max(
        raw_text.rfind(delimiter, 0, start)
        for delimiter in (".", "!", "?", ",", ";")
    )
    clause = raw_text[boundary + 1 : start]
    return any(
        re.search(
            rf"(?<![가-힣]){re.escape(anchor)}"
            r"(?:은|는|이|가|을|를|의|에|에서|으로|로|도|만)?"
            r"(?![가-힣])",
            clause,
        )
        is not None
        for anchor in anchors
    )


def _jo_specific_owner_context(
    previous: str, following: str, tail: str, at_end: bool
) -> bool:
    financial = _matching_noun_anchor(previous, JO_FINANCIAL_ANCHORS)
    return (
        financial is not None
        or following == "원"
        or tail == "" and following == "" and at_end
    )


def _is_existing_jo_owner_context(
    raw_text: str, match: re.Match[str]
) -> bool:
    if match.group("unit") != "조":
        return False
    previous_char = raw_text[match.start() - 1] if match.start() > 0 else ""
    return (
        bool(previous_char)
        and previous_char in "$€£¥₩"
        or match.group("tail").startswith("원")
        or _next_word(raw_text, match.end()) == "원"
        or _matching_noun_anchor(
            _previous_word(raw_text, match.start()), JO_FINANCIAL_ANCHORS
        )
        is not None
    )


def _is_followed_by_large_unit_number(
    raw_text: str, match: re.Match[str]
) -> bool:
    tail = raw_text[match.end() :]
    if re.match(r"\s+\d[\d,]*(?:\.\d+)? ?(?:만|억|조|경)", tail):
        return True
    index = match.end()
    while index < len(raw_text) and raw_text[index].isspace():
        index += 1
    if index >= len(raw_text):
        return False
    from engine.span_engine.large_unit import (
        LARGE_UNIT_ATOMIC_INVENTORY,
        _parse_numeric_large_unit_at,
        _parse_small_group,
    )

    if _parse_numeric_large_unit_at(raw_text, index) is not None:
        return True
    group = _parse_small_group(raw_text, index)
    if group is None or not group.saw_small_unit:
        return False
    return (
        group.end < len(raw_text)
        and raw_text[group.end] in LARGE_UNIT_ATOMIC_INVENTORY
    )


def _is_structured_duration_minute(raw_text: str, start: int) -> bool:
    previous = raw_text[:start].rstrip()
    return previous.endswith("시간")


def _is_supported_tail(unit: str, tail: str) -> bool:
    if unit == "가지":
        return tail in _GAJI_TAILS
    if unit in {"번", "차", "위"}:
        if _matching_fixed_suffix(unit, tail) is not None:
            return True
        return tail in (_BEON_TAILS if unit == "번" else _COMMON_TAILS)
    if unit == "대" and tail.startswith("째"):
        return True
    if unit == "부" and tail.startswith("작"):
        return True
    if unit == "호" and tail.startswith(("실", "선")):
        return True
    if unit == "단" and tail.startswith("계"):
        return True
    if unit == "등" and tail.startswith("급"):
        return True
    if unit == "조" and tail.startswith("원"):
        return True
    if tail.startswith(("이었", "였")):
        return True
    return tail in (_BEON_TAILS if unit == "번" else _COMMON_TAILS)


def _matching_fixed_suffix(unit: str, tail: str) -> str | None:
    suffixes = {
        "번": _BEON_FIXED_SUFFIXES,
        "차": _CHA_FIXED_SUFFIXES,
        "위": _WI_FIXED_SUFFIXES,
    }.get(unit, ())
    for suffix in suffixes:
        if not tail.startswith(suffix):
            continue
        remainder = tail[len(suffix) :]
        if remainder in _COMMON_TAILS or remainder.startswith(("이었", "였")):
            return suffix
    return None


def _preceded_by_spaced_ordinal(raw_text: str, start: int) -> bool:
    return raw_text[:start].endswith("제 ")


def _is_dong_ho_structure(
    raw_text: str, match: re.Match[str]
) -> bool:
    unit = match.group("unit")
    if unit == "동":
        suffix = raw_text[match.end() :]
        return re.match(r"\s+\d[\d,]* ?호(?:[가-힣]*)", suffix) is not None
    if unit == "호":
        prefix = raw_text[: match.start()]
        return re.search(r"\d[\d,]* ?동\s+$", prefix) is not None
    return False


def _is_gwon_ho_structure(
    raw_text: str, match: re.Match[str]
) -> bool:
    unit = match.group("unit")
    if unit == "권":
        return _is_followed_by_numbered_unit(raw_text, match, "호")
    if unit == "호":
        return (
            re.search(r"\d[\d,]* ?권\s+$", raw_text[: match.start()])
            is not None
        )
    return False


def _is_followed_by_numbered_unit(
    raw_text: str, match: re.Match[str], unit: str
) -> bool:
    suffix = raw_text[match.end() :]
    return (
        re.match(rf"\s+\d[\d,]* ?{re.escape(unit)}(?:[가-힣]*)", suffix)
        is not None
    )


def _ensure_text(raw_text: str) -> None:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")


def _candidate_unit(candidate: SurfaceCandidate) -> str | None:
    decision = candidate.metadata.get("contextual_decision")
    return decision.unit if isinstance(decision, ContextualDecision) else None


__all__ = [
    "BEON_IDENTIFIER_NOUNS",
    "BEON_OCCURRENCE_ACTIONS",
    "BU_DOCUMENT_NOUNS",
    "BU_QUANTITY_ACTIONS",
    "BU_SEQUENCE_NOUNS",
    "CHEOK_LENGTH_NOUNS",
    "CHEOK_SHIP_NOUNS",
    "CHEUNG_LOCATION_NOUNS",
    "CHEUNG_LOCATION_PREFIXES",
    "DAE_AGE_NOUNS",
    "DAE_GENERATION_NOUNS",
    "DAN_GRADE_NOUNS",
    "DAN_STACK_ACTIONS",
    "DEUNG_LIGHT_ACTIONS",
    "DEUNG_LIGHT_NOUNS",
    "DEUNG_RANK_NOUNS",
    "DONG_BUILDING_NOUNS",
    "DONG_IDENTIFIER_NOUNS",
    "DONG_QUANTITY_ACTIONS",
    "HO_HOUSEHOLD_NOUNS",
    "HO_IDENTIFIER_NOUNS",
    "HO_QUANTITY_ACTIONS",
    "GWON_BOOK_NOUNS",
    "GWON_VOLUME_NOUNS",
    "JEOM_ITEM_ACTIONS",
    "JEOM_ITEM_NOUNS",
    "JEOM_SCORE_ANCHORS",
    "JO_FINANCIAL_ANCHORS",
    "JO_GROUP_ACTIONS",
    "JANG_CHAPTER_NOUNS",
    "JANG_SHEET_NOUNS",
    "OWNER",
    "PAN_EDITION_NOUNS",
    "PAN_GAME_ACTIONS",
    "PAN_GAME_NOUNS",
    "PERSON_BUN_NOUNS",
    "PYEON_STRUCTURE_NOUNS",
    "PYEON_WORK_NOUNS",
    "RULE_VERSION",
    "build_contextual_decision_logs",
    "parse_contextual_number_unit_candidate",
    "scan_contextual_large_unit_collision_candidates",
    "scan_contextual_large_unit_malformed_candidates",
    "scan_contextual_malformed_candidates",
    "scan_contextual_non_large_unit_malformed_candidates",
    "scan_contextual_number_unit_candidates",
]
