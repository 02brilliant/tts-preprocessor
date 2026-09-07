from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
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

    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise StandardPronunciationDataError(
            "5단계 표준발음 사전 schema_version은 1이어야 합니다."
        )
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise StandardPronunciationDataError(
            "5단계 표준발음 사전에 entries가 필요합니다."
        )

    entries: list[StandardPronunciationEntry] = []
    identities: set[tuple[str, str]] = set()
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
        if any(not isinstance(raw.get(field), str) or not raw[field] for field in required):
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] 필드가 유효하지 않습니다."
            )
        if raw["mode"] not in {"deterministic", "contextual"}:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}] mode가 유효하지 않습니다."
            )
        if raw["surface"] == raw["pronunciation"]:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전 entries[{index}]가 원형과 같습니다."
            )
        identity = (raw["mode"], raw["surface"])
        if identity in identities:
            raise StandardPronunciationDataError(
                f"5단계 표준발음 사전에 중복 표면이 있습니다: {raw['surface']}"
            )
        identities.add(identity)
        entries.append(StandardPronunciationEntry(**{field: raw[field] for field in required}))
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
