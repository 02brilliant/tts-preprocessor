from __future__ import annotations

import re
from dataclasses import dataclass

from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.signed_numeric import parse_signed_numeric_core


# Minimal canonical inventory for nouns that directly license the `대` quantity
# counter. Keep this metadata centralized; scanners must not carry local keyword
# lists or infer counter semantics from arbitrary Hangul nouns.
REGISTERED_DAE_COUNTER_NOUNS = frozenset(
    {"자동차", "차량", "장비", "버스", "서버", "카메라"}
)
REGISTERED_DAE_TOPIC_PARTICLES = frozenset({"은", "는", "이", "가"})
REGISTERED_DAE_QUANTITY_MARKERS = frozenset({"모두", "총"})

_INTEGER_CORE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_NUMERIC_DAE_RE = re.compile(rf"(?P<number>{_INTEGER_CORE}(?:\.\d+)?)대")
_CONTINUATION_RE = re.compile(
    rf"(?P<noun>[가-힣]+) (?P<first>{_INTEGER_CORE})대 $"
)
_TOPIC_QUANTITY_RE = re.compile(
    r"(?P<noun>[가-힣]+)(?P<particle>은|는|이|가) "
    r"(?P<marker>모두|총) $"
)
_RELATION_RIGHT_RE = re.compile(r" ?(?:[+-]?\d|\d+/\d)")


@dataclass(frozen=True)
class NumericDaeDecision:
    action: str
    owner: str
    reason: str
    span: SourceSpan


def is_registered_dae_counter_noun(noun: str) -> bool:
    if not isinstance(noun, str):
        raise TypeError("noun must be str")
    return noun in REGISTERED_DAE_COUNTER_NOUNS


def evaluate_numeric_dae_counter_context(
    raw_text: str, candidate_span: SourceSpan
) -> NumericDaeDecision:
    """Decide whether an attached `N대` may defer to the existing counter owner."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(candidate_span, SourceSpan):
        raise TypeError("candidate_span must be SourceSpan")

    if is_sino_threshold_numeric_dae(raw_text, candidate_span):
        return NumericDaeDecision(
            action="DEFER_TO_COUNTER",
            owner="contextual_numeric_dae",
            reason="dae_counter_sino_threshold_40_plus",
            span=candidate_span,
        )

    explicit_reason = explicit_numeric_dae_counter_context_reason(
        raw_text, candidate_span
    )
    if explicit_reason is not None:
        return NumericDaeDecision(
            action="DEFER_TO_COUNTER",
            owner="contextual_numeric_dae",
            reason=explicit_reason,
            span=candidate_span,
        )

    return NumericDaeDecision(
        action="FALLBACK",
        owner="contextual_numeric_dae",
        reason="explicit_dae_counter_context_missing",
        span=candidate_span,
    )


def explicit_numeric_dae_counter_context_reason(
    raw_text: str, candidate_span: SourceSpan
) -> str | None:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(candidate_span, SourceSpan):
        raise TypeError("candidate_span must be SourceSpan")

    previous_noun = _direct_previous_noun(raw_text, candidate_span.start)
    if previous_noun is not None and is_registered_dae_counter_noun(previous_noun):
        return "dae_counter_registered_noun_direct_context"

    continuation_noun = _registered_counter_series_noun(raw_text, candidate_span.start)
    if continuation_noun is not None:
        return "dae_counter_registered_noun_adjacent_continuation"

    topic_quantity_noun = _registered_topic_quantity_noun(
        raw_text, candidate_span.start
    )
    if topic_quantity_noun is not None:
        return "dae_counter_registered_noun_topic_quantity_context"
    return None


def scan_ambiguous_numeric_dae_preserve_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    candidates: list[SurfaceCandidate] = []
    for match in _NUMERIC_DAE_RE.finditer(raw_text):
        core_span = SourceSpan(match.start(), match.end())
        surface_end = _consume_attached_hangul_tail(raw_text, core_span.end)
        span = SourceSpan(core_span.start, surface_end)
        if not _safe_left_boundary(raw_text, span.start):
            continue
        if not _safe_right_boundary(raw_text, span.end):
            continue
        if _looks_like_relation_right_operand(raw_text, core_span.end):
            continue
        number_end = match.start("number") + len(match.group("number"))
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="ambiguous_numeric_dae_preserve",
                surface_type="AMBIGUOUS_NUMERIC_DAE_PRESERVE_SURFACE",
                reason="no_existing_owner_and_no_explicit_counter_context",
                metadata={
                    "claim_type": "preserve",
                    "number_span": SourceSpan(span.start, number_end),
                    "dae_span": SourceSpan(number_end, surface_end),
                },
            )
        )
    return candidates


def parse_ambiguous_numeric_dae_preserve_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "ambiguous_numeric_dae_preserve":
        return None
    number_span = candidate.metadata.get("number_span")
    dae_span = candidate.metadata.get("dae_span")
    if not isinstance(number_span, SourceSpan) or not isinstance(dae_span, SourceSpan):
        return None
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    pieces = [
        RenderPiece(
            text=raw_text[number_span.start : number_span.end],
            provenance="ORIGINAL_BOUNDARY",
            source_span=number_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=raw_text[dae_span.start : dae_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=dae_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]
    return Surface(
        surface_type=candidate.surface_type
        or "AMBIGUOUS_NUMERIC_DAE_PRESERVE_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=raw,
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def _direct_previous_noun(raw_text: str, numeric_start: int) -> str | None:
    if numeric_start < 2 or raw_text[numeric_start - 1] != " ":
        return None
    noun_end = numeric_start - 1
    noun_start = noun_end
    while noun_start > 0 and _is_completed_hangul(raw_text[noun_start - 1]):
        noun_start -= 1
    if noun_start == noun_end:
        return None
    if noun_start > 0 and _is_identifier_neighbor(raw_text[noun_start - 1]):
        return None
    return raw_text[noun_start:noun_end]


def _registered_counter_series_noun(raw_text: str, numeric_start: int) -> str | None:
    match = _CONTINUATION_RE.search(raw_text[:numeric_start])
    if match is None:
        return None
    noun = match.group("noun")
    if not is_registered_dae_counter_noun(noun):
        return None
    if match.start("noun") > 0 and _is_identifier_neighbor(
        raw_text[match.start("noun") - 1]
    ):
        return None
    return noun


def _registered_topic_quantity_noun(
    raw_text: str, numeric_start: int
) -> str | None:
    match = _TOPIC_QUANTITY_RE.search(raw_text[:numeric_start])
    if match is None:
        return None
    noun = match.group("noun")
    particle = match.group("particle")
    marker = match.group("marker")
    if (
        not is_registered_dae_counter_noun(noun)
        or particle not in REGISTERED_DAE_TOPIC_PARTICLES
        or marker not in REGISTERED_DAE_QUANTITY_MARKERS
    ):
        return None
    if match.start("noun") > 0 and _is_identifier_neighbor(
        raw_text[match.start("noun") - 1]
    ):
        return None
    return noun


def is_sino_threshold_numeric_dae(
    raw_text: str, candidate_span: SourceSpan
) -> bool:
    raw = raw_text[candidate_span.start : candidate_span.end]
    if not raw.endswith("대"):
        return False
    numeric_core = parse_signed_numeric_core(
        raw[:-1],
        allow_plus=False,
        allow_minus=False,
    )
    if numeric_core is None or numeric_core.sign_kind is not None:
        return False
    return int(numeric_core.integer_digits) >= 40


def _safe_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    previous = raw_text[start - 1]
    return not _is_identifier_neighbor(previous) and previous not in ".,/_+-"


def _safe_right_boundary(raw_text: str, end: int) -> bool:
    if end == len(raw_text):
        return True
    following = raw_text[end]
    if following.isascii() and (following.isalnum() or following in "_/"):
        return False
    return True


def _looks_like_relation_right_operand(raw_text: str, end: int) -> bool:
    return _RELATION_RIGHT_RE.match(raw_text, end) is not None


def _consume_attached_hangul_tail(raw_text: str, start: int) -> int:
    end = start
    while end < len(raw_text) and _is_completed_hangul(raw_text[end]):
        end += 1
    return end


def _is_completed_hangul(char: str) -> bool:
    return "가" <= char <= "힣"


def _is_identifier_neighbor(char: str) -> bool:
    return _is_completed_hangul(char) or (char.isascii() and char.isalnum()) or char == "_"


__all__ = [
    "NumericDaeDecision",
    "REGISTERED_DAE_COUNTER_NOUNS",
    "REGISTERED_DAE_QUANTITY_MARKERS",
    "REGISTERED_DAE_TOPIC_PARTICLES",
    "evaluate_numeric_dae_counter_context",
    "explicit_numeric_dae_counter_context_reason",
    "is_sino_threshold_numeric_dae",
    "is_registered_dae_counter_noun",
    "parse_ambiguous_numeric_dae_preserve_candidate",
    "scan_ambiguous_numeric_dae_preserve_candidates",
]
