from __future__ import annotations

from dataclasses import dataclass
import re


_STANDALONE_NEWS_RE = re.compile(r"(?<= )news(?= )")
_LOCK_TOKEN_RE = re.compile(r"<LOCK_(\d+)>")


@dataclass(frozen=True)
class LockedNewsText:
    text: str
    replacements: tuple[tuple[str, str], ...]


def lock_standalone_news(text: str) -> LockedNewsText:
    """Replace only the stage-1 ASCII-space-delimited ``news`` surface with locks."""

    if not isinstance(text, str):
        raise TypeError("text must be str")

    used_indices = {int(match.group(1)) for match in _LOCK_TOKEN_RE.finditer(text)}
    next_index = 1
    replacements: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        nonlocal next_index
        while next_index in used_indices:
            next_index += 1
        token = f"<LOCK_{next_index:04d}>"
        used_indices.add(next_index)
        next_index += 1
        replacements.append((token, match.group(0)))
        return token

    return LockedNewsText(
        text=_STANDALONE_NEWS_RE.sub(replace, text),
        replacements=tuple(replacements),
    )


def restore_locked_news(text: str, locked: LockedNewsText) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not isinstance(locked, LockedNewsText):
        raise TypeError("locked must be LockedNewsText")

    restored = text
    for token, reading in locked.replacements:
        if restored.count(token) != 1:
            raise ValueError("locked news token must occur exactly once")
        restored = restored.replace(token, reading)
    return restored


__all__ = ["LockedNewsText", "lock_standalone_news", "restore_locked_news"]
