from __future__ import annotations

from dataclasses import dataclass
import re

from LLM.validation_models import AllowedMutation, NormalizationSnapshot


@dataclass(frozen=True)
class PronunciationEntry:
    surface: str
    pronunciation: str
    category: str
    stage: int
    source: str


_STAGE4_ENTRIES = (
    PronunciationEntry("색연필", "색년필", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("솜이불", "솜니불", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("막일", "막닐", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("꽃잎", "꽃닢", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("식용유", "식용뉴", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("국민연금", "국민년금", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("국민 연금", "국민 년금", "n_insertion", 4, "existing-level-4-policy"),
    PronunciationEntry("문고리", "문꼬리", "lexical_tensification", 4, "existing-level-4-policy"),
    PronunciationEntry("손등", "손뜽", "lexical_tensification", 4, "existing-level-4-policy"),
    PronunciationEntry("발바닥", "발빠닥", "lexical_tensification", 4, "existing-level-4-policy"),
    PronunciationEntry("길가", "길까", "lexical_tensification", 4, "existing-level-4-policy"),
    PronunciationEntry("초승달", "초승딸", "lexical_tensification", 4, "existing-level-4-policy"),
    PronunciationEntry("의견란", "의견난", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("임진란", "임진난", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("생산량", "생산냥", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("결단력", "결딴녁", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("공권력", "공꿘녁", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("동원령", "동원녕", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("상견례", "상견녜", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("횡단로", "횡단노", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("이원론", "이원논", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("입원료", "이붠뇨", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("구근류", "구근뉴", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 20"),
    PronunciationEntry("백분율", "백뿐뉼", "lexical_n_l", 4, "NIKL Standard Pronunciation Rule 29"),
)

PRONUNCIATION_ENTRIES = _STAGE4_ENTRIES

_GRAMMATICAL_TAIL_RE = re.compile(
    r"(?:"
    r"은|는|이|가|을|를|의|에|에서|에게|까지|부터|와|과|도|만|로|으로|"
    r"이다|입니다|이었다|이었지만|이었는데|이었어요|이었다가|이에요|이어서|"
    r"이시다|이세요|이셨다"
    r")$"
)
_COMPOUND_GRAMMATICAL_TAIL_RE = re.compile(
    r"(?:"
    r"했습니다|하였습니다|합니다|됩니다|되었습니다|입니다|"
    r"이었다|이었어요|이었는데|이었지만|이에요|이어서|이세요|이셨다|"
    r"습니다|습니까|어요|아요|였다|였어요|였는데|였지만|"
    r"이라고|이라면|이라서|이며|이고|"
    r"으로는|에서는|에게는|까지는|부터는|"
    r"으로|에서|에게|까지|부터|처럼|보다|"
    r"은|는|이|가|을|를|의|에|와|과|도|만|로"
    r")+$"
)
_HANGUL_WORD_RE = re.compile(r"[가-힣]+")
_CONTRACTION_TAILS = {
    "이었다": "였다",
    "이었지만": "였지만",
    "이었는데": "였는데",
    "이었어요": "였어요",
    "이었다가": "였다가",
    "이에요": "예요",
    "이어서": "여서",
    "이시다": "시다",
    "이세요": "세요",
    "이셨다": "셨다",
}
def entries_for_stage(stage: int) -> tuple[PronunciationEntry, ...]:
    if stage not in {3, 4}:
        raise ValueError("stage must be 3 or 4")
    return tuple(entry for entry in PRONUNCIATION_ENTRIES if entry.stage <= stage)


def build_allowed_mutations(
    normalized_text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
) -> tuple[AllowedMutation, ...]:
    if stage not in {3, 4}:
        raise ValueError("stage must be 3 or 4")

    candidates: list[AllowedMutation] = []
    for word_match in _HANGUL_WORD_RE.finditer(normalized_text):
        word = word_match.group(0)

        if stage >= 4:
            contraction = _contraction_mutation(
                word,
                word_match.start(),
            )
            if contraction is not None:
                candidates.append(contraction)

        compound_tail = _COMPOUND_GRAMMATICAL_TAIL_RE.search(word)
        stem_end = len(word) if compound_tail is None else compound_tail.start()
        compound_stem = word[:stem_end]
        compound_tail_text = word[stem_end:]
        if len(compound_stem) >= 6:
            candidates.append(
                AllowedMutation(
                    start=word_match.start(),
                    end=word_match.end(),
                    kind="compound_boundary",
                    source_text=word,
                    allowed_outputs=tuple(
                        compound_stem[:index]
                        + "-"
                        + compound_stem[index:]
                        + compound_tail_text
                        for index in range(2, len(compound_stem) - 1)
                    ),
                )
            )

    return _filter_and_resolve(candidates, snapshot)


def build_deterministic_pronunciation_mutations(
    normalized_text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
) -> tuple[AllowedMutation, ...]:
    """Return fixed whole-word pronunciation rewrites for the stage overlay."""

    if stage not in {3, 4}:
        raise ValueError("stage must be 3 or 4")
    if stage == 3:
        return ()
    return _filter_and_resolve(
        _entry_mutations(normalized_text, entries_for_stage(stage)), snapshot
    )


def _entry_mutations(
    normalized_text: str,
    entries: tuple[PronunciationEntry, ...],
) -> list[AllowedMutation]:
    candidates: list[AllowedMutation] = []

    for entry in (item for item in entries if " " in item.surface):
        search_from = 0
        while (start := normalized_text.find(entry.surface, search_from)) >= 0:
            end = start + len(entry.surface)
            search_from = start + 1
            if start > 0 and "가" <= normalized_text[start - 1] <= "힣":
                continue
            tail_end = end
            while tail_end < len(normalized_text) and "가" <= normalized_text[tail_end] <= "힣":
                tail_end += 1
            tail = normalized_text[end:tail_end]
            if tail and _GRAMMATICAL_TAIL_RE.fullmatch(tail) is None:
                continue
            candidates.append(
                AllowedMutation(
                    start=start,
                    end=end,
                    kind=entry.category,
                    source_text=entry.surface,
                    allowed_outputs=(entry.pronunciation,),
                )
            )

    for word_match in _HANGUL_WORD_RE.finditer(normalized_text):
        word = word_match.group(0)
        for entry in sorted(
            (item for item in entries if " " not in item.surface),
            key=lambda item: len(item.surface),
            reverse=True,
        ):
            if not word.startswith(entry.surface):
                continue
            remainder = word[len(entry.surface) :]
            if remainder and _GRAMMATICAL_TAIL_RE.fullmatch(remainder) is None:
                continue
            start = word_match.start()
            end = start + len(entry.surface)
            candidates.append(
                AllowedMutation(
                    start=start,
                    end=end,
                    kind=entry.category,
                    source_text=entry.surface,
                    allowed_outputs=(entry.pronunciation,),
                )
            )
            break
    return candidates


def _filter_and_resolve(
    candidates: list[AllowedMutation],
    snapshot: NormalizationSnapshot | None,
) -> tuple[AllowedMutation, ...]:
    blocked = () if snapshot is None else tuple(
        span for span in snapshot.spans if span.locked or span.protected
    )
    filtered = [
        candidate
        for candidate in candidates
        if not any(
            candidate.start < span.normalized_end
            and span.normalized_start < candidate.end
            for span in blocked
        )
    ]
    return _resolve_overlaps(filtered)


def _contraction_mutation(
    word: str,
    offset: int,
) -> AllowedMutation | None:
    stem = ""
    outputs: set[str] = set()
    if word.endswith("입니다"):
        stem = word[: -len("입니다")]
        contracted = _contract_imnida(stem)
        if contracted is None:
            return None
        outputs.add(contracted)
    else:
        for source_tail, output_tail in _CONTRACTION_TAILS.items():
            if word.endswith(source_tail):
                stem = word[: -len(source_tail)]
                if not stem or _has_final_consonant(stem[-1]):
                    return None
                outputs.add(stem + output_tail)
                break
    if not outputs:
        return None

    return AllowedMutation(
        start=offset,
        end=offset + len(word),
        kind="natural_speech_contraction",
        source_text=word,
        allowed_outputs=tuple(sorted(outputs)),
    )


def _contract_imnida(stem: str) -> str | None:
    if not stem or _has_final_consonant(stem[-1]):
        return None
    code = ord(stem[-1]) - 0xAC00
    if code < 0 or code >= 11172:
        return None
    return stem[:-1] + chr(ord(stem[-1]) + 17) + "니다"


def _has_final_consonant(character: str) -> bool:
    code = ord(character) - 0xAC00
    return 0 <= code < 11172 and code % 28 != 0


def _resolve_overlaps(candidates: list[AllowedMutation]) -> tuple[AllowedMutation, ...]:
    priority = {
        "natural_speech_contraction": 0,
        "lexical_n_l": 1,
        "n_insertion": 1,
        "lexical_tensification": 1,
        "compound_boundary": 2,
    }
    # Different stage policies can legitimately target the same complete span
    # (for example, a long compound ending in ``입니다`` may allow either one
    # compound-boundary hyphen or the closed ``이다`` contraction).  Preserve
    # those as mutually exclusive whole-span alternatives.  This does not
    # authorize chaining the two rewrites.
    coalesced: dict[tuple[int, int, str], AllowedMutation] = {}
    for candidate in candidates:
        key = (candidate.start, candidate.end, candidate.source_text)
        existing = coalesced.get(key)
        if existing is None:
            coalesced[key] = candidate
            continue
        preferred = min(
            (existing, candidate),
            key=lambda item: priority.get(item.kind, 9),
        )
        coalesced[key] = AllowedMutation(
            start=preferred.start,
            end=preferred.end,
            kind=preferred.kind,
            source_text=preferred.source_text,
            allowed_outputs=tuple(
                dict.fromkeys(existing.allowed_outputs + candidate.allowed_outputs)
            ),
        )

    selected: list[AllowedMutation] = []
    for candidate in sorted(
        coalesced.values(),
        key=lambda item: (item.start, priority.get(item.kind, 9), -(item.end - item.start)),
    ):
        if any(candidate.start < item.end and item.start < candidate.end for item in selected):
            continue
        selected.append(candidate)
    return tuple(sorted(selected, key=lambda item: item.start))


__all__ = [
    "PRONUNCIATION_ENTRIES",
    "PronunciationEntry",
    "build_allowed_mutations",
    "build_deterministic_pronunciation_mutations",
    "entries_for_stage",
]
