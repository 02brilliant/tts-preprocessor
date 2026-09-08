from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re

from LLM.standard_pronunciation import entries_for_mode
from LLM.validation_models import AllowedMutation, NormalizationSnapshot


@dataclass(frozen=True)
class PronunciationEntry:
    surface: str
    pronunciation: str
    category: str
    stage: int
    source: str
    boundary_type: str = "noun"
    allowed_tails: tuple[str, ...] = ()
    paradigm_id: str | None = None


_GRAMMATICAL_TAIL_RE = re.compile(
    r"(?:"
    r"은|는|이|가|을|를|의|에|에서|에게|까지|부터|와|과|도|만|로|으로|"
    r"이다|입니다|이었다|이었지만|이었는데|이었어요|이었다가|이에요|이어서|"
    r"이시다|이세요|이셨다"
    r")$"
)
_STAGE5_NOUN_TAIL_RE = re.compile(
    r"(?:"
    r"으로는|에서는|에게는|까지는|부터는|으로서|로서|으로써|로써|"
    r"이라고|이라면|이라서|이며|이고|처럼|보다|으로|에서|에게|까지|부터|"
    r"은|는|이|가|을|를|의|에|와|과|도|만|로|"
    r"이다|입니다|이었다|이었지만|이었는데|이었어요|이었다가|이에요|이어서|"
    r"이시다|이세요|이셨다"
    r")+$"
)
_CONTEXTUAL_APPLY_PHRASES = {
    "대가": (
        "노동의 대가",
        "성공의 대가",
        "실패의 대가",
        "선택의 대가",
        "희생의 대가",
        "대가를 치르",
        "대가를 치렀",
        "대가를 지불",
        "대가를 지급",
        "대가로 받",
        "대가로 지급",
    ),
}
_CONTEXTUAL_PRESERVE_PHRASES = {
    "대가": (
        "예술계의 대가",
        "바둑계의 대가",
        "문단의 대가",
        "화단의 대가",
        "학계의 대가",
        "당대의 대가",
        "대가로 불리",
    ),
}
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
    if stage not in {3, 4, 5}:
        raise ValueError("stage must be 3, 4, or 5")
    if stage < 5:
        return ()
    return _stage5_entries("deterministic")


def build_allowed_mutations(
    normalized_text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
) -> tuple[AllowedMutation, ...]:
    if stage not in {3, 4, 5}:
        raise ValueError("stage must be 3, 4, or 5")

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

    if stage >= 5:
        contextual = _entry_mutations(
            normalized_text,
            _stage5_entries("contextual"),
            grammatical_tail_re=_STAGE5_NOUN_TAIL_RE,
        )
        candidates.extend(
            item
            for item in contextual
            if _contextual_status(normalized_text, item) == "unresolved"
        )
        candidates = _merge_contextual_contraction_candidates(candidates)

    return _filter_and_resolve(candidates, snapshot)


def build_stage5_deterministic_pronunciation_mutations(
    normalized_text: str,
    *,
    snapshot: NormalizationSnapshot | None = None,
) -> tuple[AllowedMutation, ...]:
    """Return stage-5-only exact pronunciations applied before its LLM pass."""

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    deterministic = _entry_mutations(
        normalized_text,
        _stage5_entries("deterministic"),
        grammatical_tail_re=_STAGE5_NOUN_TAIL_RE,
    )
    contextual = _entry_mutations(
        normalized_text,
        _stage5_entries("contextual"),
        grammatical_tail_re=_STAGE5_NOUN_TAIL_RE,
    )
    deterministic.extend(
        item
        for item in contextual
        if _contextual_status(normalized_text, item) == "apply"
    )
    return _filter_and_resolve(deterministic, snapshot)


@lru_cache(maxsize=2)
def _stage5_entries(mode: str) -> tuple[PronunciationEntry, ...]:
    return tuple(
        PronunciationEntry(
            surface=entry.surface,
            pronunciation=entry.pronunciation,
            category=entry.category,
            stage=5,
            source=entry.source,
            boundary_type=entry.boundary_type,
            allowed_tails=entry.allowed_tails,
            paradigm_id=entry.paradigm_id,
        )
        for entry in entries_for_mode(mode)
    )


def _entry_mutations(
    normalized_text: str,
    entries: tuple[PronunciationEntry, ...],
    *,
    grammatical_tail_re: re.Pattern[str] = _GRAMMATICAL_TAIL_RE,
) -> list[AllowedMutation]:
    candidates: list[AllowedMutation] = []

    multiword_entries, entry_index = _entry_index(entries)

    for entry in multiword_entries:
        search_from = 0
        while (start := normalized_text.find(entry.surface, search_from)) >= 0:
            end = start + len(entry.surface)
            search_from = start + 1
            if start > 0 and "가" <= normalized_text[start - 1] <= "힣":
                continue
            tail_end = end
            while (
                tail_end < len(normalized_text)
                and "가" <= normalized_text[tail_end] <= "힣"
            ):
                tail_end += 1
            tail = normalized_text[end:tail_end]
            if not _tail_is_allowed(entry, tail, grammatical_tail_re):
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
        for entry in entry_index.get(word[0], ()):
            if not word.startswith(entry.surface):
                continue
            remainder = word[len(entry.surface) :]
            if not _tail_is_allowed(entry, remainder, grammatical_tail_re):
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


@lru_cache(maxsize=8)
def _entry_index(
    entries: tuple[PronunciationEntry, ...],
) -> tuple[tuple[PronunciationEntry, ...], dict[str, tuple[PronunciationEntry, ...]]]:
    multiword = tuple(
        sorted(
            (entry for entry in entries if " " in entry.surface),
            key=lambda entry: len(entry.surface),
            reverse=True,
        )
    )
    grouped: dict[str, list[PronunciationEntry]] = {}
    for entry in entries:
        if " " in entry.surface:
            continue
        grouped.setdefault(entry.surface[0], []).append(entry)
    return multiword, {
        initial: tuple(sorted(group, key=lambda entry: len(entry.surface), reverse=True))
        for initial, group in grouped.items()
    }


def _tail_is_allowed(
    entry: PronunciationEntry,
    tail: str,
    default_tail_re: re.Pattern[str],
) -> bool:
    if not tail:
        return True
    if entry.allowed_tails:
        return tail in entry.allowed_tails
    if entry.boundary_type in {"noun", "contextual"}:
        return default_tail_re.fullmatch(tail) is not None
    return False


def _contextual_status(
    normalized_text: str,
    mutation: AllowedMutation,
) -> str:
    surface = mutation.source_text
    if _span_is_in_any_phrase(
        normalized_text,
        mutation.start,
        mutation.end,
        _CONTEXTUAL_PRESERVE_PHRASES.get(surface, ()),
    ):
        return "preserve"
    if _span_is_in_any_phrase(
        normalized_text,
        mutation.start,
        mutation.end,
        _CONTEXTUAL_APPLY_PHRASES.get(surface, ()),
    ):
        return "apply"
    return "unresolved"


def _span_is_in_any_phrase(
    text: str,
    start: int,
    end: int,
    phrases: tuple[str, ...],
) -> bool:
    for phrase in phrases:
        search_from = 0
        while (phrase_start := text.find(phrase, search_from)) >= 0:
            phrase_end = phrase_start + len(phrase)
            if phrase_start <= start and end <= phrase_end:
                return True
            search_from = phrase_start + 1
    return False


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


def _merge_contextual_contraction_candidates(
    candidates: list[AllowedMutation],
) -> list[AllowedMutation]:
    """Preserve contextual pronunciation when it overlaps an ``이다`` contraction."""

    contextual = [
        item
        for item in candidates
        if item.kind == "contextual_standard_pronunciation"
    ]
    consumed: set[int] = set()
    merged: list[AllowedMutation] = []
    for candidate in candidates:
        if candidate.kind != "natural_speech_contraction":
            merged.append(candidate)
            continue
        nested = [
            item
            for item in contextual
            if candidate.start <= item.start
            and item.end <= candidate.end
        ]
        if not nested:
            merged.append(candidate)
            continue

        outputs = list(candidate.allowed_outputs)
        rewritten_sources = [candidate.source_text]
        for item in nested:
            relative_start = item.start - candidate.start
            relative_end = item.end - candidate.start
            next_sources: list[str] = []
            for source in rewritten_sources:
                for replacement in item.allowed_outputs:
                    contextual_source = (
                        source[:relative_start]
                        + replacement
                        + source[relative_end:]
                    )
                    next_sources.append(contextual_source)
                    outputs.append(contextual_source)
                    contraction = _contraction_mutation(
                        contextual_source,
                        candidate.start,
                    )
                    if contraction is not None:
                        outputs.extend(contraction.allowed_outputs)
            rewritten_sources.extend(next_sources)
            consumed.add(id(item))
        merged.append(
            AllowedMutation(
                start=candidate.start,
                end=candidate.end,
                kind="contextual_standard_pronunciation",
                source_text=candidate.source_text,
                allowed_outputs=tuple(dict.fromkeys(outputs)),
            )
        )
    return [item for item in merged if id(item) not in consumed]


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
        "aspiration": 1,
        "consonant_cluster": 1,
        "final_consonant": 1,
        "liaison": 1,
        "liquid_assimilation": 1,
        "nasal_assimilation": 1,
        "palatalization": 1,
        "tensification": 1,
        "contextual_standard_pronunciation": 1,
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
    "PronunciationEntry",
    "build_allowed_mutations",
    "build_stage5_deterministic_pronunciation_mutations",
    "entries_for_stage",
]
