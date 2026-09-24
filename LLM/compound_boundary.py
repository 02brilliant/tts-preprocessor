"""Conservative lexical boundaries for the LLM's closed selection plan.

These units are a reviewed eligibility vocabulary, not a morphological analyzer
or an instruction to insert a hyphen. Unknown material fails closed; the model
still decides whether a surviving boundary fits the sentence's meaning/prosody.
Keep lexicalized groups intact by intersecting boundaries of *all* full parses.
"""

from __future__ import annotations

from functools import lru_cache
import re

from LLM.validation_models import AllowedMutation, NormalizationSnapshot


# Common news, public policy, technology and service noun groups. Add vocabulary
# with positive AND negative regression cases. Do not add one-syllable affixes,
# inflected predicates or arbitrary unknown-word fallbacks. Korean names composed
# of these nouns are eligible under the same semantic-boundary rules.
_NOUN_UNITS = frozenset("""
개인 개인정보 정보 보호 정보보호 정보통신 통신 통신망 인공 지능 인공지능
기술 과학 과학기술 연구 개발 연구개발 개발계획 데이터 데이터분석 데이터베이스 시스템 서비스
소프트웨어 하드웨어 컴퓨터 네트워크 플랫폼 인터넷 보안 사이버보안
처리 방침 처리방침 운영 관리 운영관리 통합 자동 자동화 분석 설계 구축
지원 지원사업 지원센터 평가 심사 신청 접수 조회 발급 인증 인증서
전자 전자문서 문서 기록 기록관리 자료 저장 검색 사용자 이용 이용자
산업 산업용 지역 전기 요금 요금제 전기요금 전기요금제 에너지 발전
태양광 재생에너지 신재생에너지 발전소 발전시설 전력 공급 수요 시설 설비
안전 안전관리 안전점검 재난 재난안전 대응 예방 사고 점검 유지 보수 유지보수
환경 환경보호 기후 기후변화 탄소 탄소중립 대기 오염 수질 폐기물 자원
도시 가스 도시가스 교통 대중교통 철도 도로 주택 공동주택 부동산 건설
국가 공공 공공기관 기관 행정 지방 지방자치 자치단체 지방자치단체 정부
정책 사업 계획 제도 기본 기본계획 종합 종합계획 추진 시행 규정 기준
경제 금융 금융기관 투자 자산 자산관리 신용 카드 신용카드 보험 건강보험
국민 국민연금 연금 고용 고용보험 산업재해 산재보험 복지 사회 사회복지
의료 보건 건강 건강관리 병원 환자 진료 진료기록 의료기기 의약품
교육 교육과정 학교 평생교육 직업 직업교육 훈련 직업훈련 인력 양성
문화 관광 문화재 문화유산 유산 콘텐츠 방송 통신기술 방송통신
생산 생산량 소비 소비자 소비자보호 품질 품질관리 유통 물류 배송
제품 상품 식품 식품안전 수출 수입 무역 중소기업 기업 소상공인
경영 경영정보 재무 회계 세무 보고 보고서 실적 성과 성과평가
책임 책임자 담당 담당자 업무 업무처리 절차 결과 현황 내역 사용 사용내역
센터 위원회 협의회 협력 국제 국제협력 전문가 전문가협회
지도 안전지도 안내 안내문 안내서 이용안내 설명 설명서 설명자료
서울 부산 인천 대전 대구 광주 울산 세종 경기 강원 충북 충남 전북 전남 경북 경남 제주 한국
해양 진흥 공사 철도 도시철도 전력 전력공사 산업안전지도 도시철도공사 해양진흥공사
대한적십자사 혈액관리본부 한국전력공사 농림축산식품부 노사정 노사정위원회
재난안전관리시스템
""".split())

# Reviewed top-level/second-level noun groupings. An exact grouping takes
# precedence over generic constituent parses so a lexicalized head is not
# split merely because all of its smaller nouns are individually registered.
# Every output is checked against its source at import time: a boundary policy
# may add ASCII hyphens but may never correct, drop, or rewrite source letters.
_REVIEWED_BOUNDARIES: dict[str, tuple[str, ...]] = {
    "서울대학교병원강남검진센터": ("서울대학교병원-강남-검진센터",),
    "대한적십자사서울특별지사혈액원": ("대한적십자사-서울특별지사-혈액원",),
    "국민건강보험공단부산울산경남지역본부": (
        "국민건강보험공단-부산울산경남-지역본부",
    ),
    "국가균형발전특별회계운용계획": ("국가-균형발전특별회계-운용계획",),
    "소상공인경영지원자금사업": ("소상공인-경영지원자금-사업",),
    "초중등교육법시행령개정안": ("초중등교육법-시행령-개정안",),
    "인공지능기반자율주행차량안전기준": (
        "인공지능기반-자율주행차량-안전기준",
    ),
    "차세대지능형교통시스템구축사업": ("차세대-지능형교통시스템-구축사업",),
    "국가초고성능컴퓨팅활용체계": ("국가-초고성능컴퓨팅-활용체계",),
    "생명공학연구원바이오나노연구단": (
        "생명공학연구원-바이오나노연구단",
        "생명공학연구원-바이오나노-연구단",
    ),
    "양자컴퓨팅기술개발사업": ("양자컴퓨팅-기술개발사업",),
    "유전체데이터기반정밀의료시스템": ("유전체-데이터기반-정밀의료시스템",),
    "한국전자통신연구원소프트웨어연구소": (
        "한국-전자통신연구원-소프트웨어연구소",
    ),
    "한국수출입은행무역금융본부": ("한국-수출입은행-무역금융본부",),
    "주택담보대출상환유예제도": ("주택담보대출-상환유예제도",),
    "글로벌자산배분펀드운용전략": (
        "글로벌자산배분-펀드운용전략",
        "글로벌-자산배분-펀드운용전략",
    ),
    "소비자물가지수개편방안": ("소비자물가지수-개편방안",),
    "국립현대미술관덕수궁관": ("국립현대미술관-덕수궁관",),
    "한국예술종합학교연극원": ("한국예술종합학교-연극원",),
    "세계문화유산등재추진위원회": ("세계문화유산-등재추진위원회",),
    "평생학습도시인증평가": ("평생학습도시-인증평가",),
    "한국수자원공사수질개선사업단": ("한국-수자원공사-수질개선사업단",),
    "탄소중립녹색성장기본계획": ("탄소중립-녹색성장-기본계획",),
    "해양생태계보전지역지정안": ("해양생태계-보전지역-지정안",),
    "인공지능자율주행": ("인공지능-자율주행",),
}
for _surface, _outputs in _REVIEWED_BOUNDARIES.items():
    if not _outputs or any(
        option.replace("-", "") != _surface or "--" in option
        or not all(len(part) >= 2 for part in option.split("-"))
        for option in _outputs
    ):
        raise ValueError(f"invalid compound boundary registry entry: {_surface}")
_NOUN_UNITS |= frozenset(
    part
    for outputs in _REVIEWED_BOUNDARIES.values()
    for option in outputs
    for part in option.split("-")
)
_NOUN_UNITS |= frozenset({"한국수출입은행"})
# The rule engine has already rendered these Latin abbreviations as locked
# Hangul readings. Split only the original Korean fragments around an exactly
# matching, provenance-confirmed reading; never rewrite the reading itself.
_REVIEWED_ACRONYM_BOUNDARIES = {
    "한국토지주택공사엘에이치토지주택연구원": (
        "한국토지주택공사", "엘에이치", "토지주택연구원",
        "한국토지주택공사-", "-토지주택연구원",
    ),
    "수도권광역급행철도지티엑스노선": (
        "수도권광역급행철도", "지티엑스", "노선",
        "수도권-광역급행철도-", "-노선",
    ),
}
for _surface, (_left, _reading, _right, _left_out, _right_out) in _REVIEWED_ACRONYM_BOUNDARIES.items():
    if _surface != _left + _reading + _right or (
        _left_out + _reading + (_right_out or _right)
    ).replace("-", "") != _surface:
        raise ValueError(f"invalid locked acronym boundary entry: {_surface}")
_MIN_STEM_LENGTH = 6
_MAX_STEM_LENGTH = 32
_MIN_CHUNK_LENGTH = 3
_MAX_OPTIONS = 6
_WORD_RE = re.compile(r"[가-힣]+")
# A two-syllable initial chunk is allowed only for a reviewed, independent
# geographic/national modifier. The rest of the noun must still parse fully.
_SHORT_ROOT_MODIFIERS = frozenset("""
국가 한국 서울 부산 인천 대전 대구 광주 울산 세종 경기 강원 충북 충남 전북 전남 경북 경남 제주
""".split())

# Match only the complete remainder AFTER lexical analysis. In particular, do
# not repeatedly strip syllables such as 이/가/도 from a noun (전기/평가/지도).
_NOUN_TAIL_RE = re.compile(
    r"(?:은|는|이|가|을|를|의|와|과|도|만)"
    r"|(?:에|로|으로|에서|에게|께|한테|"
    r"까지|부터|처럼|보다|조차|마저|마다|밖에|으로서|로서|으로써|로써|"
    r"으로부터|에서부터)(?:는|은|도|만)?"
    r"|(?:이다|입니다|이었다|이었습니다|이었어요|이었는데|이었지만|이었다가|"
    r"이에요|이어서|이시다|이세요|이셨다|이라고|이라는|이라면|이라서|이며|이고)"
)


@lru_cache(maxsize=4096)
def _common_boundaries(stem: str) -> frozenset[int] | None:
    """DP intersection of every complete lexical parse, without enumerating them.

    None means unrecognized; an empty set means recognized but indivisible (or
    no agreed internal boundary). A long lexical unit also has a one-unit parse,
    preventing its shorter component nouns from authorizing internal breaks.
    """
    paths: list[frozenset[int] | None] = [None] * (len(stem) + 1)
    paths[len(stem)] = frozenset()
    for start in range(len(stem) - 1, -1, -1):
        alternatives = []
        for end in range(start + 2, len(stem) + 1):
            if stem[start:end] not in _NOUN_UNITS or paths[end] is None:
                continue
            boundaries = paths[end]
            if end < len(stem):
                boundaries = boundaries | {end}
            alternatives.append(boundaries)
        if alternatives:
            paths[start] = frozenset.intersection(*alternatives)
    return paths[0]


def compound_options(word: str) -> tuple[str, ...]:
    """Offer bounded single/multiple-boundary readings, keeping noun tails intact."""
    if not _MIN_STEM_LENGTH <= len(word) <= _MAX_STEM_LENGTH + 8:
        return ()
    for end in range(min(len(word), _MAX_STEM_LENGTH), _MIN_STEM_LENGTH - 1, -1):
        tail = word[end:]
        if tail and _NOUN_TAIL_RE.fullmatch(tail) is None:
            continue
        stem = word[:end]
        reviewed = _REVIEWED_BOUNDARIES.get(stem)
        if reviewed is not None:
            return tuple(output + tail for output in reviewed)
        boundaries = _common_boundaries(stem)
        if boundaries is None:
            continue
        # The longest recognized nominal stem wins even if it has no safe break.
        # Never retry with a shorter stem by treating its last syllable as a tail.
        return tuple(
            "-".join(word[left:right] for left, right in zip((0,) + layout, layout)) + tail
            for layout in _boundary_layouts(word[:end], boundaries)
        )
    return ()


def _layout_score(layout: tuple[int, ...]) -> tuple[int, int, int, tuple[int, ...]]:
    sizes = [right - left for left, right in zip((0,) + layout, layout)]
    # Presentation heuristic only: avoid very long chunks, then unnecessary
    # pauses, then uneven lengths. These are not semantic confidence scores.
    return (
        sum(max(0, size - 8) ** 2 for size in sizes),
        len(layout),
        sum(size ** 2 for size in sizes),
        layout,
    )


def _valid_chunk(stem: str, start: int, end: int) -> bool:
    length = end - start
    return length >= _MIN_CHUNK_LENGTH or (
        start == 0 and length == 2 and stem[:end] in _SHORT_ROOT_MODIFIERS
    )


def _boundary_layouts(stem: str, boundaries: frozenset[int]) -> tuple[tuple[int, ...], ...]:
    """Bounded DP; only reviewed outer modifiers may form a two-syllable chunk.

    Paths include their final endpoint. Keeping the best K paths at each endpoint
    avoids exponential subset enumeration. Both one-break and multi-break options
    survive when available, so the LLM can choose the number of pauses in context.
    """
    length = len(stem)
    eligible = sorted(
        index for index in boundaries
        if _valid_chunk(stem, 0, index) and length - index >= _MIN_CHUNK_LENGTH
    )
    if not eligible:
        return ()
    paths: dict[int, list[tuple[int, ...]]] = {0: [()]}
    for end in eligible + [length]:
        alternatives = [
            path + (end,)
            for start, previous in paths.items()
            if _valid_chunk(stem, start, end)
            for path in previous
        ]
        paths[end] = sorted(alternatives, key=_layout_score)[:_MAX_OPTIONS + 1]
    singles = [(index, length) for index in eligible]
    multiple = [path for path in paths[length] if len(path) > 2]
    ranked = sorted(set(singles + multiple), key=_layout_score)
    reserved = [min(singles, key=_layout_score)]
    if multiple:
        reserved.append(min(multiple, key=_layout_score))
    selected = list(dict.fromkeys(reserved + ranked))[:_MAX_OPTIONS]
    return tuple(sorted(selected, key=_layout_score))


def build_compound_mutations(text: str) -> list[AllowedMutation]:
    candidates = []
    for match in _WORD_RE.finditer(text):
        # A Hangul substring of a mixed identifier or already hyphenated token
        # must not gain another break, including on a subsequent pipeline pass.
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        if any(
            char and (char.isalnum() or char in "_-‐‑‒–—―−﹘﹣－/\\@")
            for char in (before, after)
        ):
            continue
        options = compound_options(match.group())
        if options:
            candidates.append(AllowedMutation(
                start=match.start(),
                end=match.end(),
                kind="compound_boundary",
                source_text=match.group(),
                allowed_outputs=options,
            ))
    return candidates


def build_locked_acronym_compound_mutations(
    text: str, snapshot: NormalizationSnapshot | None,
) -> list[AllowedMutation]:
    """Offer reviewed pauses adjacent to a confirmed, locked acronym reading."""
    if snapshot is None or snapshot.normalized_text != text:
        return []
    candidates: list[AllowedMutation] = []
    for match in _WORD_RE.finditer(text):
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        if any(
            char and (char.isalnum() or char in "_-‐‑‒–—―−﹘﹣－/\\@")
            for char in (before, after)
        ):
            continue
        word = match.group()
        for surface, (left, reading, right, left_out, right_out) in _REVIEWED_ACRONYM_BOUNDARIES.items():
            if not word.startswith(surface):
                continue
            if word != surface and _NOUN_TAIL_RE.fullmatch(word[len(surface):]) is None:
                continue
            reading_start = match.start() + len(left)
            reading_end = reading_start + len(reading)
            if not any(
                span.normalized_start == reading_start
                and span.normalized_end == reading_end
                and span.text == reading
                and span.provenance == "GENERATED_READING"
                and span.locked
                and not span.protected
                for span in snapshot.spans
            ):
                continue
            candidates.append(AllowedMutation(
                start=match.start(), end=reading_start,
                kind="compound_boundary", source_text=left,
                allowed_outputs=(left_out,),
            ))
            if right_out is not None:
                candidates.append(AllowedMutation(
                    start=reading_end, end=reading_end + len(right),
                    kind="compound_boundary", source_text=right,
                    allowed_outputs=(right_out,),
                ))
            break
    return candidates
