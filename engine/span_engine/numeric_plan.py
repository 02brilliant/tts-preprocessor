"""Internal numeric annotations; ownership and public JSON stay unchanged.

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
    render_span: SourceSpan | None = None
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
    render_span: SourceSpan | None = None
    separator_before: str | None = None


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
    marker_status: str = "not_rendered"
    render_edits: tuple[tuple[int, int, str, str], ...] = ()


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
    for month, entry in data.get("months", {}).items():
        if month not in {"2", "4", "5"} or entry.get("length") != "long" or not entry.get("source") or not entry.get("lexeme_id"):
            raise ValueError(f"invalid numeric month entry: {month}")
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
    from engine.span_engine.sign_aliases import strip_signed_numeric_sign
    _, unsigned = strip_signed_numeric_sign(raw)
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
    "decimal_registered_suffix": "count", "compound_slash_unit": "measure", "compound_exact_unit": "measure",
    "multiplier": "count", "colon_semantic_pair": "ratio", "korean_da_score_pair": "ratio",
    "large_unit_atomic": "large_unit", "multi_colon_numeric": "ratio",
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
    unit = meta.get("counter") or meta.get("unit") or meta.get("suffix") or meta.get("currency") or meta.get("numeric_unit")
    if unit == "%":
        semantic = "percent"
    form = "unresolved"
    metadata_only = False
    if owner in {"date", "time", "duration"} and not meta.get("preserve") and not meta.get("fallback_owner"):
        if meta.get("numeric_parts"):
            for role, number, span in meta["numeric_parts"]:
                components.append(_temporal_component(number, role, span, owner))
        elif meta.get("numeric_span") and not (owner == "duration" and unit == "년"):
            span = meta["numeric_span"]
            number = raw_text[span.start:span.end]
            role = {"년": "year", "월": "month", "일": "day", "시": "hour",
                    "시간": "duration_hour", "분": "minute", "초": "second"}.get(unit, "value")
            if normalize_integer_text(number.lstrip("0") or "0") is not None and not any(c in number for c in "+-−－＋/."):
                components.append(_temporal_component(number, role, span, owner))
        form = "integer" if components else "unresolved"
    elif owner in {"compound_slash_unit", "compound_exact_unit"}:
        from engine.span_engine.compound_unit import COMPOUND_SLASH_UNIT_READINGS, COMPOUND_EXACT_UNIT_READINGS
        template = (COMPOUND_SLASH_UNIT_READINGS if owner == "compound_slash_unit" else COMPOUND_EXACT_UNIT_READINGS)[unit]
        number = meta["numeric"]
        prefix = template.split("{number}")[0]
        span = SourceSpan(candidate.core_span.start, candidate.core_span.start + len(number))
        components.append(replace(number_component(number), source_span=span,
                                  render_span=SourceSpan(len(prefix), len(prefix))))
        form = "decimal" if "." in number else "integer"
    elif owner == "decimal_registered_suffix":
        components.append(replace(number_component(meta["number"]), source_span=candidate.core_span))
        form = "decimal"
    elif owner == "multiplier":
        from engine.span_engine.multiplier import multiplier_number_reading
        from engine.span_engine.counter import HYBRID_COUNTER_THRESHOLD
        number = meta["number"]
        system = "native" if number.isdigit() and 1 <= int(number) <= HYBRID_COUNTER_THRESHOLD else "sino"
        components.append(replace(number_component(number, system=system,
                          native_reading=multiplier_number_reading(number)), source_span=candidate.core_span))
        unit, form = "배", "decimal" if "." in number else "integer"
    elif owner in {"colon_semantic_pair", "korean_da_score_pair"}:
        for role in ("left", "right"):
            value = meta[role]
            components.append(replace(number_component(value.raw if hasattr(value, "raw") else value, role),
                                      source_span=meta.get(role + "_span")))
        if owner == "korean_da_score_pair":
            components[1] = replace(components[1], separator_before=(
                "대" if meta["compact_integer_rendering"] else " 대 "))
        form = "ratio"
    elif owner == "counter_noun" and meta.get("numeric_core_kind") == "arabic_integer":
        from engine.span_engine.counter import counter_reading_details
        number = meta["raw_number"]
        details = counter_reading_details(number, unit)
        if unit == "자" and candidate.reason in {
            "general_character_ja_sino", "character_count_context",
            "name_character_count_context", "traditional_character_length_context",
        }:
            from engine.span_engine.numeric_reading import read_number_text
            selected = meta["reading"].strip().removesuffix("-")
            details = (selected, "sino" if selected == read_number_text(number) else "native")
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
            components.append(replace(number_component(number, system=system,
                              native_reading=(meta.get("number_reading") or "").strip()),
                              source_span=number_span))
            form = "decimal" if "." in number else "integer"
    elif owner in {"number", "decimal", "signed_number"}:
        number = raw.strip()
        system = meta.get("numeral_system", "sino")
        components.append(number_component(number, system=system, native_reading=meta.get("number_reading")))
        if owner == "signed_number" and system == "native":
            # Correct the selected reading without extending this owner's
            # previously unresolved signed-counter marker scope.
            semantic, unit, metadata_only = "count", meta.get("reading_counter"), True
        form = "decimal" if "." in number else "integer"
    elif owner == "large_unit_atomic" and isinstance(meta.get("numeric_span"), SourceSpan):
        span = meta["numeric_span"]
        components.append(replace(number_component(raw_text[span.start:span.end]), source_span=span))
        form = meta.get("number_form", "unresolved")
        suffix_span = meta.get("suffix_span")
        unit = raw_text[suffix_span.start:suffix_span.end] if isinstance(suffix_span, SourceSpan) else None
        metadata_only = True
    elif owner == "multi_colon_numeric" and meta.get("blocks"):
        cursor = candidate.core_span.start
        for index, number in enumerate(meta["blocks"]):
            components.append(replace(number_component(number, f"block:{index}"),
                                      source_span=SourceSpan(cursor, cursor + len(number))))
            cursor += len(number) + 1  # The accepting scanner consumed one colon alias.
        form, metadata_only = "ratio", True
    elif owner in {"range", "range_with_unit"} and meta.get("left") is not None and meta.get("right") is not None:
        for side in ("left", "right"):
            value = meta[side]
            number = value.raw if hasattr(value, "raw") else str(value)
            system = "sino"
            if meta.get("count_readings"):
                from engine.span_engine.counter import counter_reading_details
                system = counter_reading_details(number, unit)[1]
                semantic = "count"
            elif unit in {"시", "시간"} and normalize_integer_text(number) is not None:
                from engine.span_engine.date_time import clock_hour_reading
                from engine.span_engine.range import _duration_hour_prefix_reading
                selected = (clock_hour_reading(int(number)) if unit == "시"
                            else _duration_hour_prefix_reading(number))
                from engine.span_engine.numeric_reading import read_number_text
                system = "sino" if selected == read_number_text(number) else "native"
            components.append(number_component(number, side, system))
            if unit == "월":
                components[-1] = _month_evidence(components[-1])
        form = "range"
    elif owner == "fraction":
        for role in ("denominator", "numerator"):
            components.append(number_component(meta[role], role))
        form = "fraction"
    elif owner == "textual_fraction":
        for role in ("denominator", "numerator"):
            span = meta[role + "_span"]
            components.append(replace(number_component(raw_text[span.start:span.end], role), source_span=span))
        form = "fraction"
    elif owner in {"phone", "hyphen_digit_blocks"}:
        for index, group in enumerate(raw.lstrip("+").split("-")):
            if not group.isascii() or not group.isdigit():
                continue
            digits = tuple("공일이삼사오육칠팔구"[int(c)] for c in group)
            components.append(NumberComponent(group, f"identifier_group:{index}", "digits",
                groups=(digits,), vowels=_vowels((digits,), "sino", f"phone:{index}", domain_resolved=False)))
        form = "digit_sequence"
    elif (owner == "numeric_suffix" and unit == "초"
          and candidate.reason == "numeric_korean_suffix_fallback"
          and normalize_integer_text(meta["number"]) is not None):
        components.append(_temporal_component(meta["number"], "second", candidate.core_span, "time"))
        semantic, form = "clock", "integer"
    elif isinstance(meta.get("amount"), str):
        number = meta["amount"]
        if "/" in number and not number.startswith(tuple("+-−－–—‒‑")):
            numerator, denominator = number.split("/")
            components.extend((number_component(denominator, "denominator"), number_component(numerator, "numerator")))
            form = "fraction"
        else:
            components.append(number_component(number))
            form = "decimal" if "." in number else "integer"
    elif owner == "percent_point" and isinstance(meta.get("number"), str):
        number = (meta.get("sign_surface") or "") + meta["number"]
        if "/" in number and not number.startswith(tuple("+-−－–—‒‑")):
            numerator, denominator = number.split("/")
            components.extend((number_component(denominator, "denominator"), number_component(numerator, "numerator")))
            form = "fraction"
        else:
            components.append(number_component(number))
            form = "decimal" if "." in number else "integer"
        if unit == "%":
            semantic = "percent"
    if components and meta.get("unit_reading") == "화씨" and not meta.get("sign_surface"):
        components[0] = replace(components[0], render_span=SourceSpan(3, 3))
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
    if metadata_only:
        plan = replace(plan, components=tuple(replace(component, vowels=tuple(
            replace(vowel, target="unresolved", reason="owner_linguistic_unit_unresolved")
            for vowel in component.vowels)) for component in plan.components),
            analysis_status="owner_linguistic_unit_unresolved")
    excluded = (meta.get("preserve") or meta.get("fallback_owner") or meta.get("je_span")
                or (form == "fraction" and meta.get("sign_surface"))
                or candidate.reason == "time_hour_clock_direction"
                or raw.startswith("제") or raw_text[candidate.full_span.start:candidate.core_span.start].strip() == "제"
                or (owner == "contextual_number_unit" and isinstance(contextual, ContextualDecision)
                    and (contextual.semantic_type in {"fixed_identifier_suffix", "fixed_numeric_compound"}
                         or (contextual.matched_anchor or "").startswith("fixed_suffix:"))))
    unit_span = meta.get("counter_span") or meta.get("suffix_span")
    tail_span = meta.get("unit_tail_span")
    if unit_span is None and unit and isinstance(tail_span, SourceSpan):
        if raw_text[tail_span.start:tail_span.start + len(unit)] == unit:
            unit_span = SourceSpan(tail_span.start, tail_span.start + len(unit))
    return replace(plan, unit_source_span=unit_span,
                   marker_status="scope_excluded" if excluded else "owner_scope_unresolved" if metadata_only else "not_rendered")


def _month_evidence(component: NumberComponent) -> NumberComponent:
    month = str(int(component.raw)) if component.raw.isdigit() else component.raw
    entry = vowel_data().get("months", {}).get(month)
    if entry and component.vowels:
        first = replace(component.vowels[0], lexeme_id=entry["lexeme_id"],
                        lexical_length="long", target="long", reason="calendar_month_dictionary",
                        sources=(entry["source"],))
        return replace(component, vowels=(first, *component.vowels[1:]))
    if month in {"6", "10"}:
        groups = (("유" if month == "6" else "시",),)
        return replace(component, groups=groups, vowels=_vowels(groups, "month", component.role))
    return component


def _temporal_component(raw: str, role: str, span: SourceSpan, owner: str) -> NumberComponent:
    # The accepting temporal owner alone permits normalization of leading zeroes.
    normalized = str(int(raw.replace(",", "")))
    system = "sino"
    if role == "hour" and owner == "time":
        system = "native" if 1 <= int(normalized) <= 12 else "sino"
    elif role == "duration_hour" and owner == "duration" and "," not in raw:
        system = "native" if 1 <= int(normalized) <= 23 and not raw.startswith("0") else "sino"
    component = number_component(normalized, role, system)
    component = replace(component, raw=raw, integer_part=raw, source_span=span)
    return _month_evidence(component) if role == "month" else component


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


def project_plan_source(plan: NumericReadingPlan, indices: tuple[int | None, ...],
                        original: str) -> NumericReadingPlan:
    """Return owner coordinates to original input after known newline edits."""
    if plan.coordinate_space != "source":
        return plan
    def project(span):
        if span is None:
            return None
        positions = indices[span.start:span.end]
        # Numeric/owner endpoints survive; intervening elisions are known edits.
        # An inserted endpoint has no original coordinate and stays unresolved.
        if not positions or positions[0] is None or positions[-1] is None:
            return None
        return SourceSpan(positions[0], positions[-1] + 1)
    source_span = project(plan.source_span)
    components = []
    for component in plan.components:
        span = project(component.source_span)
        components.append(replace(component, source_span=span,
                                  raw=original[span.start:span.end] if span is not None else component.raw))
    boundaries = []
    for boundary in plan.boundaries:
        span = project(boundary.source_span)
        if boundary.source_span is not None and span is None:
            boundary = replace(boundary, origin="generated", kind="input_normalization")
        boundaries.append(replace(boundary, source_span=span,
                                  text=original[span.start:span.end] if span is not None else boundary.text))
    return replace(plan, source_span=source_span,
                   raw=original[source_span.start:source_span.end] if source_span is not None else plan.raw,
                   unit_source_span=project(plan.unit_source_span),
                   components=tuple(components), boundaries=tuple(boundaries))


def annotations_from_output(output) -> tuple[NumericAnnotation, ...]:
    """Cumulative piece offsets projected through recorded presentation edits.

    No find/SequenceMatcher alignment is allowed for numeric metadata, even for
    repeated identical values. Unmapped or internally changed plans stay unresolved.
    """
    from engine.text_alignment import rendered_index_map
    mapping = rendered_index_map(output)
    result = []
    cursor = 0
    for piece in output.render_pieces:
        for plan in piece.numeric_plans:
            positions = ([mapping.get(index) for index in range(cursor, cursor + len(plan.text))]
                         if mapping is not None else [])
            aligned = (bool(positions) and all(index is not None for index in positions)
                       and positions == list(range(positions[0], positions[0] + len(plan.text)))
                       and output.normalized_text[positions[0]:positions[-1] + 1] == plan.text)
            result.append(NumericAnnotation(plan, SourceSpan(positions[0], positions[-1] + 1) if aligned else None,
                                            "exact" if aligned else "final_coordinates_unresolved"))
        cursor += len(piece.text)
    return tuple(result)


def project_annotations(annotations: tuple[NumericAnnotation, ...],
                        edits: tuple[tuple[int, int, str, NumericReadingPlan | None], ...]) -> tuple[NumericAnnotation, ...]:
    """Project only explicit, non-overlapping edits in the current input space."""
    def project(index, *, after_insertions=True):
        return index + sum(len(text) - (end - start) for start, end, text, _ in edits
                           if end < index or (end == index and (start < end or after_insertions)))
    result = []
    for annotation in annotations:
        span = annotation.output_span
        if span is None:
            result.append(annotation)
        elif not any(start < span.end and span.start < end for start, end, _, _ in edits):
            result.append(replace(annotation, output_span=SourceSpan(
                project(span.start), project(span.end, after_insertions=False))))
    for start, _end, text, plan in edits:
        if plan is not None:
            # A residual candidate's source coordinates refer to pre-edit
            # normalized text, not fabricated original-input coordinates.
            plan = replace(plan, coordinate_space="normalized_input")
            projected_start = project(start, after_insertions=False)
            result.append(NumericAnnotation(plan, SourceSpan(projected_start, projected_start + len(text)), "exact"))
    return tuple(result)
