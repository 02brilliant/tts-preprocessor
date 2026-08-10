from __future__ import annotations

import re

from engine.span_engine.models import SourceSpan, SurfaceCandidate


_STANDALONE_NEWS_RE = re.compile(r"(?<= )뉴스(?= )")


def scan_standalone_news_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Claim only the explicitly ASCII-space-delimited Korean ``뉴스`` surface.

    This is deliberately not a lexical substring rule. In particular,
    ``빌뉴스``, ``뉴스타``, and ``뉴스입니다`` remain original text until a
    separately approved semantic policy exists.
    """

    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    return [
        SurfaceCandidate(
            core_span=SourceSpan(match.start(), match.end()),
            full_span=SourceSpan(match.start(), match.end()),
            owner="standalone_news",
            surface_type="STANDALONE_NEWS_SURFACE",
            reason="space_delimited_news_to_english_reading",
        )
        for match in _STANDALONE_NEWS_RE.finditer(raw_text)
    ]


def parse_standalone_news_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "standalone_news":
        return None
    if raw_text[candidate.core_span.start : candidate.core_span.end] != "뉴스":
        return None
    return "news"


__all__ = [
    "parse_standalone_news_candidate",
    "scan_standalone_news_candidates",
]
