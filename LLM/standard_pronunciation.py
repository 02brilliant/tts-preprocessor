from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import re
from pathlib import Path

from LLM.config import STAGE5_PRONUNCIATION_PATH


class StandardPronunciationDataError(ValueError):
    """The packaged stage-5 pronunciation registry is missing or invalid."""


@dataclass(frozen=True)
class StandardPronunciationEntry:
    surface: str
    pronunciation: str
    mode: str
    category: str
    sense_hint: str
    source: str
    boundary_type: str
    allowed_tails: tuple[str, ...]
    paradigm_id: str | None


_ALLOWED_MODES = {"deterministic", "contextual"}
_ALLOWED_CATEGORIES = {
    "aspiration",
    "consonant_cluster",
    "contextual_standard_pronunciation",
    "final_consonant",
    "lexical_n_l",
    "lexical_tensification",
    "liaison",
    "liquid_assimilation",
    "n_insertion",
    "nasal_assimilation",
    "palatalization",
    "tensification",
}
_ALLOWED_BOUNDARY_TYPES = {
    "contextual",
    "fixed_phrase",
    "noun",
    "predicate_complete",
    "predicate_form",
}
_HANGUL_SURFACE_RE = re.compile(r"[가-힣]+(?: [가-힣]+)*")
_HANGUL_TAIL_RE = re.compile(r"[가-힣]+")


def load_stage5_pronunciations(
    path: Path = STAGE5_PRONUNCIATION_PATH,
) -> tuple[StandardPronunciationEntry, ...]:
    return _load_stage5_pronunciations(path)


@lru_cache(maxsize=4)
def _load_stage5_pronunciations(
    path: Path,
) -> tuple[StandardPronunciationEntry, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StandardPronunciationDataError(
            "5단계 표준발음 사전 파일을 찾을 수 없습니다."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StandardPronunciationDataError(
            "5단계 표준발음 사전은 유효한 UTF-8 JSON이어야 합니다."
        ) from exc

    if not isinstance(payload, dict) or payload.get("schema_version") not in {1, 2}:
        raise StandardPronunciationDataError(
            "5단계 표준발음 사전 schema_version은 1 또는 2여야 합니다."
        )
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise StandardPronunciationDataError(
            "5단계 표준발음 사전에 entries가 필요합니다."
        )

    entries: list[StandardPronunciationEntry] = []
    surfaces: set[str] = set()
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}]가 객체가 아닙니다."
            )
        required = (
            "surface",
            "pronunciation",
            "mode",
            "category",
            "sense_hint",
            "source",
        )
        if any(
            not isinstance(raw.get(field), str) or not raw[field]
            for field in required
        ):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] 필드가 유효하지 않습니다."
            )
        if raw["mode"] not in _ALLOWED_MODES:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] mode가 유효하지 않습니다."
            )
        if raw["surface"] == raw["pronunciation"]:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}]가 원형과 같습니다."
            )
        if raw["category"] not in _ALLOWED_CATEGORIES:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] category가 유효하지 않습니다."
            )
        if (
            _HANGUL_SURFACE_RE.fullmatch(raw["surface"]) is None
            or _HANGUL_SURFACE_RE.fullmatch(raw["pronunciation"]) is None
        ):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] 표면은 한글과 단일 공백만 허용합니다."
            )
        if not raw["source"].startswith("https://"):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] source는 HTTPS URL이어야 합니다."
            )

        default_boundary = "contextual" if raw["mode"] == "contextual" else "noun"
        boundary_type = raw.get("boundary_type", default_boundary)
        if boundary_type not in _ALLOWED_BOUNDARY_TYPES:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] boundary_type이 유효하지 않습니다."
            )
        if raw["mode"] == "contextual" and boundary_type != "contextual":
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] contextual 경계가 필요합니다."
            )
        raw_tails = raw.get("allowed_tails", [])
        if (
            not isinstance(raw_tails, list)
            or any(
                not isinstance(tail, str)
                or _HANGUL_TAIL_RE.fullmatch(tail) is None
                for tail in raw_tails
            )
            or len(set(raw_tails)) != len(raw_tails)
        ):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] allowed_tails가 유효하지 않습니다."
            )
        if boundary_type == "fixed_phrase" and raw_tails:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] fixed_phrase에는 allowed_tails를 둘 수 없습니다."
            )
        paradigm_id = raw.get("paradigm_id")
        if paradigm_id is not None and (
            not isinstance(paradigm_id, str) or not paradigm_id.strip()
        ):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] paradigm_id가 유효하지 않습니다."
            )

        if raw["surface"] in surfaces:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전에 중복 표면이 있습니다: {raw['surface']}"
            )
        surfaces.add(raw["surface"])
        entries.append(
            StandardPronunciationEntry(
                **{field: raw[field] for field in required},
                boundary_type=boundary_type,
                allowed_tails=tuple(raw_tails),
                paradigm_id=paradigm_id,
            )
        )

    pronunciation_surfaces = {entry.surface for entry in entries}
    for entry in entries:
        if entry.pronunciation in pronunciation_surfaces:
            raise StandardPronunciationDataError(
                "5단계 표준발음 사전에 연쇄 변환 충돌이 있습니다: "
                f"{entry.surface}→{entry.pronunciation}"
            )
    return tuple(entries)


def entries_for_mode(mode: str) -> tuple[StandardPronunciationEntry, ...]:
    if mode not in {"deterministic", "contextual"}:
        raise ValueError("mode must be deterministic or contextual")
    return tuple(entry for entry in load_stage5_pronunciations() if entry.mode == mode)


__all__ = [
    "StandardPronunciationDataError",
    "StandardPronunciationEntry",
    "entries_for_mode",
    "load_stage5_pronunciations",
]
