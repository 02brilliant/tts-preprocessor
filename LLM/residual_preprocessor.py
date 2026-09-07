"""Finite residual readings shared by stages 3–5; never invokes a model."""
from __future__ import annotations

import re

from engine.span_engine.currency import scan_currency_candidates, parse_currency_candidate
from engine.span_engine.date_time import (
    scan_date_candidates, parse_date_candidate, scan_time_candidates,
    parse_time_candidate, is_valid_time, time_number_reading,
)
from engine.span_engine.units import (
    scan_simple_unit_candidates, scan_special_unit_candidates, parse_unit_candidate,
)
from engine.span_engine.percent_point import scan_percent_point_candidates, parse_percent_point_candidate
from engine.span_engine.range import scan_range_candidates, parse_range_candidate
from engine.span_engine.lexicon import dictionary_reading, spell_uppercase_acronym
from engine.span_engine.language_gate import is_non_korean_prose_line
from engine.span_engine.counter import native_number_under_100
from engine.span_engine.contextual_number_unit import (
    scan_contextual_number_unit_candidates,
)
from engine.span_engine.models import ContextualDecision, ContextualDecisionKind
from engine.span_engine.numeric_reading import read_number_text, read_fraction_text
from LLM.validation_models import AllowedMutation, NormalizationSnapshot
from LLM.pronunciation_overlay import (
    apply_locked_pronunciation_mutations, PronunciationOverlayResult,
)


_SCANNERS = (
    (scan_date_candidates, parse_date_candidate),
    (scan_time_candidates, parse_time_candidate),
    (scan_currency_candidates, parse_currency_candidate),
    (scan_percent_point_candidates, parse_percent_point_candidate),
    (scan_simple_unit_candidates, parse_unit_candidate),
    (scan_special_unit_candidates, parse_unit_candidate),
    (scan_range_candidates, parse_range_candidate),
)
_WORD = re.compile(r"(?<![A-Za-z0-9_./-])[A-Za-z]+(?![A-Za-z0-9_./-])")
_COUNTER = re.compile(
    r"(?<![\w./+-])(?P<number>[1-9]\d?) ?(?P<unit>가지|분|번|점|조|대|부|동|호|판|단|등|척|장|권|편|층|차|위)"
    r"(?=(?:은|는|이|가|을|를|에|도|만|의|로|으로|와|과|에서|부터|까지|씩|입니다|이다)?(?:\s|[.,!?]|$))"
)
_NUMBER = re.compile(
    r"(?<![\w./,:+~-])(?:0|[1-9]\d{0,15})(?:\.\d{1,16})?(?![\w/,:~+-]|\.\d)"
)
_KBS = re.compile(r"(?<![A-Za-z])KBS news(?![A-Za-z])")
_PAIR = re.compile(
    r"(?<![\w./:+~-])(?P<left>0|[1-9]\d{0,3})"
    r"(?P<sep>[:/])(?P<right>0|[1-9]\d{0,3})(?![\w/:+-]|\.\d)"
)


def blocked_ranges(text: str, snapshot: NormalizationSnapshot) -> list[tuple[int, int]]:
    ranges = [
        (s.normalized_start, s.normalized_end)
        for s in snapshot.spans if s.locked or s.protected
    ]
    ranges.extend(m.span() for m in _KBS.finditer(text))
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.strip() and is_non_korean_prose_line(line.strip()):
            ranges.append((offset, offset + len(line)))
        offset += len(line)
    return ranges


def _overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < right and left < end for left, right in ranges)


def _structured(
    text: str, snapshot: NormalizationSnapshot,
) -> tuple[list[AllowedMutation], list[tuple[int, int]]]:
    blocked = blocked_ranges(text, snapshot)
    found = []
    # Reuse the production contextual classifier before exposing broad LLM
    # choices.  High-confidence number/counter meanings (for example, an
    # occurrence in `3번 처리했다`) are rendered and locked by code;
    # only genuinely deferred meanings reach the model as finite choices.
    for candidate in scan_contextual_number_unit_candidates(text):
        decision = candidate.metadata.get("contextual_decision")
        if (
            isinstance(decision, ContextualDecision)
            and decision.decision is ContextualDecisionKind.CONFIRMED
            and decision.confirmed_reading
        ):
            span = candidate.core_span
            found.append((span.start, span.end, decision.confirmed_reading))
    for scan, parse in _SCANNERS:
        for candidate in scan(text):
            span = candidate.core_span
            if candidate.owner == "preserve":
                blocked.append((candidate.full_span.start, candidate.full_span.end))
            else:
                reading = parse(text, candidate)
                if reading and reading != text[span.start:span.end]:
                    found.append((span.start, span.end, reading))
    # Longer recognized forms own their entire surface; numbers cannot be
    # consumed independently inside dates, amounts, or malformed expressions.
    mutations = []
    for start, end, reading in sorted(found, key=lambda item: (-(item[1] - item[0]), item[0])):
        if _overlaps(start, end, blocked):
            continue
        mutations.append(AllowedMutation(
            start, end, "residual_structured", text[start:end], (reading,),
        ))
        blocked.append((start, end))
    return sorted(mutations, key=lambda item: item.start), blocked


def preprocess_residual(
    text: str, *, snapshot: NormalizationSnapshot,
) -> PronunciationOverlayResult:
    """Apply only existing engine-certified forms and registered dictionary words."""
    if snapshot.normalized_text != text:
        raise ValueError("snapshot does not match residual text")
    mutations, blocked = _structured(text, snapshot)
    for match in _WORD.finditer(text):
        if _overlaps(*match.span(), blocked):
            continue
        reading = dictionary_reading(match.group())
        if reading:
            mutations.append(AllowedMutation(
                match.start(), match.end(), "residual_dictionary", match.group(), (reading,),
            ))
    return apply_locked_pronunciation_mutations(
        text,
        mutations=tuple(sorted(mutations, key=lambda item: item.start)),
        snapshot=snapshot,
        owner="residual_reading", provenance="GENERATED_RESIDUAL_READING",
    )


def residual_choices(
    text: str, snapshot: NormalizationSnapshot,
) -> tuple[list[AllowedMutation], list[tuple[int, int]]]:
    structured, blocked = _structured(text, snapshot)
    result = list(structured)
    for match in _PAIR.finditer(text):
        if _overlaps(*match.span(), blocked):
            continue
        left, sep, right = match.group("left", "sep", "right")
        if sep == ":":
            options = [read_number_text(left) + " 대 " + read_number_text(right)]
            if len(right) == 2 and is_valid_time(int(left), int(right)):
                options.append(time_number_reading(int(left), int(right)))
            kind = "residual_ratio_or_time"
        else:
            reading = read_fraction_text(left, right)
            options = [reading] if reading else []
            kind = "residual_fraction"
        if options:
            result.append(AllowedMutation(
                match.start(), match.end(), kind, match.group(), tuple(options),
            ))
            blocked.append(match.span())
    for match in _COUNTER.finditer(text):
        if _overlaps(*match.span(), blocked):
            continue
        number, unit = match.group("number", "unit")
        sino = read_number_text(number)
        native = (
            native_number_under_100(int(number))
            if unit not in {"호", "단", "등", "층", "차", "위"} else None
        )
        if unit == "가지":
            sino = None
        outputs = tuple(dict.fromkeys(item for item in (
            sino + unit if sino else None,
            native + "-" + unit if native else None,
        ) if item))
        result.append(AllowedMutation(
            match.start(), match.end(),
            "deferred_n_beon" if unit == "번" else "residual_counter", match.group(), outputs,
        ))
        blocked.append(match.span())
    for match in _WORD.finditer(text):
        if _overlaps(*match.span(), blocked):
            continue
        raw = match.group()
        reading = dictionary_reading(raw)
        if reading is None and raw.isupper() and 2 <= len(raw) <= 10:
            reading = spell_uppercase_acronym(raw)
        if reading:
            result.append(AllowedMutation(
                match.start(), match.end(), "residual_acronym", raw, (reading,),
            ))
            blocked.append(match.span())
    for match in _NUMBER.finditer(text):
        if _overlaps(*match.span(), blocked):
            continue
        reading = read_number_text(match.group())
        if reading:
            result.append(AllowedMutation(
                match.start(), match.end(), "residual_number", match.group(), (reading,),
            ))
            blocked.append(match.span())
    return result, blocked
