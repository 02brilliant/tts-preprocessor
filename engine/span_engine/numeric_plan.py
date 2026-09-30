"""Internal numeric annotations; never changes reading, ownership or public JSON.

Plans are built only after an existing owner has accepted a candidate. Source
coordinates and render coordinates are separate. Unmapped complex owners retain
an explicit unresolved state instead of reconstructing meaning from Korean text.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
import json
from pathlib import Path
import re

from engine.span_engine.models import ContextualDecision, ContextualDecisionKind, SourceSpan
from engine.span_engine.numeric_reading import integer_lexeme_groups, normalize_integer_text


@dataclass(frozen=True)
class VowelTarget:
    lexeme: str
    lexeme_id: str | None
    domain: str
    syllable_position: int
    lexical_length: str
    target: str
    reason: str
    sources: tuple[str, ...] = ()
    # No acoustic-realization field: synthesis is outside this engine.


@dataclass(frozen=True)
class NumberComponent:
    raw: str
    role: str
    numeral_system: str
    integer_part: str | None = None
    fractional_part: str | None = None
    groups: tuple[tuple[str, ...], ...] = ()
    vowels: tuple[VowelTarget, ...] = ()
    source_span: SourceSpan | None = None


@dataclass(frozen=True)
class NumericBoundary:
    kind: str
    origin: str
    text: str
    source_span: SourceSpan | None = None
    render_span: SourceSpan | None = None


@dataclass(frozen=True)
class NumericReadingPlan:
    raw: str
    source_span: SourceSpan | None
    owner: str
    decision: ContextualDecisionKind
    semantic_kind: str
    numeric_form: str
    rule_id: str
    rule_version: str
    text: str
    components: tuple[NumberComponent, ...] = ()
    unit: str | None = None
    boundaries: tuple[NumericBoundary, ...] = ()
    analysis_status: str = "resolved"
    coordinate_space: str = "source"
    unit_source_span: SourceSpan | None = None


@dataclass(frozen=True)
class NumericAnnotation:
    plan: NumericReadingPlan
    output_span: SourceSpan | None
    alignment: str


@lru_cache(maxsize=1)
def vowel_data() -> dict:
    # __file__ is placed alongside bundled data by PyInstaller, just as the
    # LLM asset loaders resolve package-local files. No runtime network access.
    data = json.loads(Path(__file__).with_name("data").joinpath("numeric_vowels.json").read_text(encoding="utf-8"))
    if data.get("version") != "1" or not isinstance(data.get("entries"), dict):
        raise ValueError("invalid numeric vowel data")
    for key, entry in data["entries"].items():
        if entry.get("length") not in {"long", "short"} or not entry.get("source") or not entry.get("lexeme_id"):
            raise ValueError(f"invalid numeric vowel entry: {key}")
    return data


def _vowels(groups: tuple[tuple[str, ...], ...], system: str, role: str,
            *, domain_resolved: bool = True) -> tuple[VowelTarget, ...]:
    data = vowel_data()
    result = []
    for group_index, group in enumerate(groups):
        position = 0
        for lexeme in group:
            entry = data["entries"].get(f"{system}:{lexeme}")
            lexical = entry["length"] if entry else "unknown"
            if not domain_resolved:
                target, reason = "unresolved", "digit_sequence_domain_unresolved"
            elif lexical == "unknown":
                target, reason = "unresolved", "lexeme_not_verified"
            elif lexical == "long" and position > 0:
                target, reason = "short", "noninitial_in_linguistic_unit"
            else:
                target, reason = lexical, "lexical_length_at_unit_start" if position == 0 else "lexical_short"
            position_source = data["native_position_source"] if system == "native" else data["position_rule_source"]
            sources = (entry["source"], position_source) if entry else ()
            result.append(VowelTarget(lexeme, entry["lexeme_id"] if entry else None,
                                      f"{role}:{group_index}", position, lexical, target, reason, sources))
            position += len(lexeme)
    return tuple(result)


def number_component(raw: str, role: str = "value", system: str = "sino",
                     *, native_reading: str | None = None) -> NumberComponent:
    unsigned = raw.lstrip("+-−－＋")
    integer, dot, fraction = unsigned.partition(".")
    normalized = normalize_integer_text(integer)
    groups: tuple[tuple[str, ...], ...] = ()
    if normalized is not None:
        if system == "native":
            from engine.span_engine.counter import native_lexemes
            lexemes = native_lexemes(int(normalized))
            if native_reading is not None and "".join(lexemes) != native_reading:
                lexemes = (native_reading,)
            groups = (lexemes,) if lexemes else ()
        elif system == "sino":
            try:
                groups = integer_lexeme_groups(int(normalized))
            except ValueError:
                pass  # existing owner's larger/compound forms remain unresolved
    vowels = _vowels(groups, system, role)
    if dot and fraction.isascii() and fraction.isdigit():
        digits = tuple("영일이삼사오육칠팔구"[int(digit)] for digit in fraction)
        vowels += _vowels((digits,), "sino", role + ":fraction_digits", domain_resolved=False)
    return NumberComponent(raw, role, system, integer, fraction if dot else None, groups, vowels)


_SEMANTICS = {
    "number": "cardinal", "decimal": "cardinal", "signed_number": "cardinal",
    "counter_noun": "count", "currency": "money", "simple_unit": "measure",
    "special_unit": "measure", "percent_point": "percent", "signed_temperature": "measure",
    "signed_degree": "measure", "range": "cardinal", "range_with_unit": "measure",
    "fraction": "fraction", "textual_fraction": "fraction", "phone": "phone",
    "hyphen_digit_blocks": "identifier", "date": "date", "time": "clock", "duration": "duration",
    "contextual_number_unit": "contextual", "ordinal": "ordinal", "numeric_suffix": "ordinal",
}


def build_numeric_plan(raw_text: str, candidate, reading: str) -> NumericReadingPlan | None:
    """Consume the accepting owner's parsed fields; never reclassify its output."""
    owner, meta = candidate.owner, candidate.metadata
    raw = raw_text[candidate.core_span.start:candidate.core_span.end]
    if not any(c.isascii() and c.isdigit() for c in raw):
        return None
    if owner not in _SEMANTICS and "numeric_form" not in meta:
        return None
    semantic = _SEMANTICS.get(owner, owner)
    decision = ContextualDecisionKind.CONFIRMED
    contextual = meta.get("contextual_decision")
    if isinstance(contextual, ContextualDecision):
        decision = contextual.decision
        semantic = contextual.semantic_type or semantic
    components = []
    unit = meta.get("counter") or meta.get("unit") or meta.get("suffix") or meta.get("currency")
    if unit == "%":
        semantic = "percent"
    form = "unresolved"
    if owner == "counter_noun" and meta.get("numeric_core_kind") == "arabic_integer":
        from engine.span_engine.counter import counter_reading_details
        number = meta["raw_number"]
        details = counter_reading_details(number, unit)
        if details:
            components.append(number_component(number, system=details[1], native_reading=details[0].removesuffix("-")))
            form = "integer"
    elif owner == "contextual_number_unit" and isinstance(contextual, ContextualDecision):
        unit = contextual.unit
        number_span = meta.get("amount_span") or meta.get("number_span")
        if decision is ContextualDecisionKind.CONFIRMED and number_span is not None:
            number = raw_text[number_span.start:number_span.end]
            mode = meta.get("reading_mode")
            system = "sino"
            if mode and mode != "sino" and normalize_integer_text(number) is not None:
                from engine.span_engine.counter import counter_reading_details, contextual_proxy_reading_details
                proxy = "사람" if mode == "native_1_to_99" else "가지" if unit == "가지" else "개"
                details = (contextual_proxy_reading_details(number) if proxy == "개"
                           else counter_reading_details(number, proxy))
                system = details[1] if details else "unresolved"
            components.append(number_component(number, system=system,
                              native_reading=(meta.get("number_reading") or "").strip()))
            form = "decimal" if "." in number else "integer"
    elif owner in {"number", "decimal", "signed_number"}:
        number = raw.strip()
        components.append(number_component(number))
        form = "decimal" if "." in number else "integer"
    elif owner in {"range", "range_with_unit"} and meta.get("left") is not None and meta.get("right") is not None:
        for side in ("left", "right"):
            value = meta[side]
            number = value.raw if hasattr(value, "raw") else str(value)
            system = "sino"
            if meta.get("count_readings"):
                from engine.span_engine.counter import counter_reading_details
                system = counter_reading_details(number, unit)[1]
                semantic = "count"
            components.append(number_component(number, side, system))
        form = "range"
    elif owner == "fraction":
        for role in ("denominator", "numerator"):
            components.append(number_component(meta[role], role))
        form = "fraction"
    elif owner in {"phone", "hyphen_digit_blocks"}:
        for index, group in enumerate(raw.lstrip("+").split("-")):
            if not group.isascii() or not group.isdigit():
                continue
            digits = tuple("공일이삼사오육칠팔구"[int(c)] for c in group)
            components.append(NumberComponent(group, f"identifier_group:{index}", "digits",
                groups=(digits,), vowels=_vowels((digits,), "sino", f"phone:{index}", domain_resolved=False)))
        form = "digit_sequence"
    elif isinstance(meta.get("amount"), str):
        number = meta["amount"]
        components.append(number_component(number))
        form = "decimal" if "." in number else "integer"
        if unit == "%":
            semantic = "percent"
    if owner in {"number", "decimal", "signed_number", "counter_noun"} and components:
        number_span = meta.get("numeric_span") or candidate.core_span
        components[0] = replace(components[0], source_span=number_span)
    elif form == "range":
        components = [replace(c, source_span=meta.get(c.role + "_span")) for c in components]
    elif owner == "fraction":
        span = meta.get("fraction_span") or candidate.core_span
        numerator_start = span.start + len(meta.get("sign_surface") or "")
        denominator_start = numerator_start + len(meta["numerator"]) + 1
        components = [replace(c, source_span=SourceSpan(
            denominator_start if c.role == "denominator" else numerator_start,
            span.end if c.role == "denominator" else numerator_start + len(meta["numerator"]))) for c in components]
    plan = make_plan(raw, candidate.core_span, owner, decision, semantic, form,
                     candidate.reason or owner, reading, tuple(components), unit,
                     rule_version=contextual.rule_version if isinstance(contextual, ContextualDecision) else "1")
    return replace(plan, unit_source_span=meta.get("counter_span") or meta.get("suffix_span"))


def make_plan(raw: str, span: SourceSpan | None, owner: str, decision: ContextualDecisionKind,
              semantic: str, form: str, rule: str, text: str,
              components: tuple[NumberComponent, ...], unit: str | None = None,
              *, rule_version: str = "1", coordinate_space: str = "source") -> NumericReadingPlan:
    boundaries = []
    # Original separators are recorded independently; they do not establish
    # lexical units. Output punctuation is inventoried, never used by _vowels.
    for match in re.finditer(r"[\s.,~:/\-]+", raw):
        kind = "identifier_separator" if form == "digit_sequence" else "source_separator"
        if match.group().isspace():
            kind = "source_space"
        boundaries.append(NumericBoundary(kind, "original", match.group(),
            SourceSpan(span.start + match.start(), span.start + match.end()) if span else None))
    for match in re.finditer(r"[ \-]+", text):
        kind = "identifier_group" if form == "digit_sequence" else "numeric_internal"
        if form == "range" and match.group().isspace():
            kind = "range_endpoint"
        if unit and match.end() == len(text):
            kind = "number_unit"
        elif unit and match.group() == "-":
            # Explicit unit labels from owner data, including translated units.
            from engine.span_engine.units import SIMPLE_UNIT_READINGS, SPECIAL_UNIT_READINGS
            label = SIMPLE_UNIT_READINGS.get(unit, SPECIAL_UNIT_READINGS.get(unit, unit))
            if text.startswith(label, match.end()):
                kind = "number_unit"
        boundaries.append(NumericBoundary(kind, "generated", match.group(),
                                          render_span=SourceSpan(match.start(), match.end())))
    return NumericReadingPlan(raw, span, owner, decision, semantic, form, rule, rule_version,
                              text, components, unit, tuple(boundaries),
                              "resolved" if components and all(c.groups for c in components) else "owner_components_unresolved", coordinate_space)


def offset_plan(plan: NumericReadingPlan, offset: int) -> NumericReadingPlan:
    def shift(span):
        return None if span is None else SourceSpan(span.start + offset, span.end + offset)
    return replace(plan, source_span=shift(plan.source_span),
                   unit_source_span=shift(plan.unit_source_span),
                   components=tuple(replace(c, source_span=shift(c.source_span)) for c in plan.components),
                   boundaries=tuple(replace(b, source_span=shift(b.source_span)) for b in plan.boundaries))


def annotations_from_output(output) -> tuple[NumericAnnotation, ...]:
    """Exact cumulative piece offsets, or explicitly unresolved after filtering.

    No find/SequenceMatcher alignment is allowed for numeric metadata, even for
    repeated identical values. A changed paragraph/filter output is conservative.
    """
    exact = "".join(p.text for p in output.render_pieces) == output.normalized_text
    result = []
    cursor = 0
    for piece in output.render_pieces:
        for plan in piece.numeric_plans:
            aligned = exact and output.normalized_text[cursor:cursor + len(plan.text)] == plan.text
            result.append(NumericAnnotation(plan, SourceSpan(cursor, cursor + len(plan.text)) if aligned else None,
                                            "exact" if aligned else "final_coordinates_unresolved"))
        cursor += len(piece.text)
    return tuple(result)


def project_annotations(annotations: tuple[NumericAnnotation, ...],
                        edits: tuple[tuple[int, int, str, NumericReadingPlan | None], ...]) -> tuple[NumericAnnotation, ...]:
    """Project only explicit, non-overlapping edits in the current input space."""
    def project(index):
        return index + sum(len(text) - (end - start) for start, end, text, _ in edits if end <= index)
    result = []
    for annotation in annotations:
        span = annotation.output_span
        if span is None:
            result.append(annotation)
        elif not any(start < span.end and span.start < end for start, end, _, _ in edits):
            result.append(replace(annotation, output_span=SourceSpan(project(span.start), project(span.end))))
    for start, _end, text, plan in edits:
        if plan is not None:
            # A residual candidate's source coordinates refer to pre-edit
            # normalized text, not fabricated original-input coordinates.
            plan = replace(plan, coordinate_space="normalized_input")
            result.append(NumericAnnotation(plan, SourceSpan(project(start), project(start) + len(text)), "exact"))
    return tuple(result)
