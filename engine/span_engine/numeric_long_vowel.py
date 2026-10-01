"""Render verified numeric vowel targets once, before locking or LLM selection.

All positions are consumed from owner-created components at explicit offsets.
No Korean-output searching, new semantic parser, runtime toggle or TTS profile.
"""
from __future__ import annotations

from dataclasses import replace

from engine.span_engine.models import ContextualDecisionKind, SourceSpan
from engine.span_engine.numeric_plan import (
    NumericBoundary, NumericReadingPlan, NumberComponent,
)


def _prefix_end(text: str, component: NumberComponent) -> int:
    cursor = len(text) - len(text.lstrip(" "))
    from engine.span_engine.sign_aliases import is_signed_numeric_sign
    if is_signed_numeric_sign(component.raw[:1]):
        for prefix in ("플러스 마이너스 ", "화씨 영하 ", "화씨 영상 ",
                       "마이너스 ", "플러스 ", "영하 ", "영상 "):
            if text.startswith(prefix, cursor):
                return cursor + len(prefix)
    return cursor


def _consume_component(text: str, cursor: int, component: NumberComponent):
    """Validate an anchored reading against known lexemes and return positions."""
    start = cursor
    targets = []
    index = 0
    if not component.groups:
        return None
    for group in component.groups:
        for lexeme in group:
            if index:
                while cursor < len(text) and text[cursor] in " -":
                    cursor += 1
            if not text.startswith(lexeme, cursor):
                return None
            target = component.vowels[index]
            targets.append(replace(target, render_span=SourceSpan(cursor, cursor + len(lexeme))))
            cursor += len(lexeme)
            index += 1
    if component.fractional_part is not None:
        if text.startswith("-", cursor):
            cursor += 1
        if not text.startswith("쩜", cursor):
            return None
        cursor += 1
        if text.startswith("-", cursor):
            cursor += 1
        for target in component.vowels[index:]:
            if text.startswith("-", cursor):
                cursor += 1
            if not text.startswith(target.lexeme, cursor):
                return None
            targets.append(replace(target, render_span=SourceSpan(cursor, cursor + 1)))
            cursor += 1
    return replace(component, vowels=tuple(targets), render_span=SourceSpan(start, cursor)), cursor


def _layout(plan: NumericReadingPlan):
    text = plan.text
    first = plan.components[0]
    base = first.render_span.start if first.render_span is not None else 0
    cursor = base + _prefix_end(text[base:], first)
    result = []
    for index, component in enumerate(plan.components):
        if (plan.semantic_kind == "clock" and component.role == "minute"
                and component.groups == (("영",),) and index > 0
                and plan.components[index - 1].role == "hour"
                and text[cursor:].strip() == "시"):
            result.append(replace(component, render_span=SourceSpan(cursor, cursor),
                          vowels=tuple(replace(v, target="unresolved", reason="not_spoken_in_owner_reading")
                                       for v in component.vowels)))
            continue
        if index:
            previous = plan.components[index - 1]
            if component.separator_before is not None:
                separator = component.separator_before
            elif plan.numeric_form == "fraction":
                separator = "분의 "
                if plan.owner == "textual_fraction":
                    start = previous.source_span.end - plan.source_span.start
                    end = component.source_span.start - plan.source_span.start
                    separator = plan.raw[start:end]
            elif plan.numeric_form == "range":
                # Existing owners either repeat the exact Korean suffix or
                # render only the connector. Both are validated at this offset.
                label = plan.unit or ""
                separators = ("-" + label + "에서 ", label + "에서 ", "에서 ")
                separator = next((s for s in separators if text.startswith(s, cursor)), None)
                if separator is None:
                    return None
            elif plan.numeric_form == "ratio":
                separator = " 대 "
            elif plan.owner == "date":
                separator = {"year": "년 ", "month": "월 "}.get(previous.role)
            elif plan.owner == "time" or plan.semantic_kind == "clock":
                separator = {"hour": "시 ", "minute": "분 "}.get(previous.role)
            else:
                return None
            if separator is None or not text.startswith(separator, cursor):
                return None
            cursor += len(separator)
            cursor = _prefix_end(text[cursor:], component) + cursor
        consumed = _consume_component(text, cursor, component)
        if consumed is None:
            return None
        mapped, cursor = consumed
        result.append(mapped)
    return tuple(result)


def render_numeric_plan(plan: NumericReadingPlan | None) -> NumericReadingPlan | None:
    if plan is None or plan.marker_status != "not_rendered":
        return plan
    if plan.decision is not ContextualDecisionKind.CONFIRMED:
        return replace(plan, marker_status="decision_unresolved")
    if not plan.components or plan.numeric_form == "digit_sequence":
        return replace(plan, marker_status="domain_unresolved")
    mapped = _layout(plan)
    if mapped is None:
        return replace(plan, marker_status="component_coordinates_unresolved")
    edits = []
    for component in mapped:
        for target in component.vowels:
            if target.target != "long" or target.render_span is None:
                continue
            position = target.render_span.start + 1  # length belongs to the first syllable
            replace_boundary = plan.text.startswith("-", position) and any(
                b.origin == "generated" and b.render_span is not None
                and b.render_span.start <= position < b.render_span.end for b in plan.boundaries)
            edits.append((position, position + int(replace_boundary), "~",
                          "NUM_LONG_REPLACE_BOUNDARY" if replace_boundary else "NUM_LONG_INSERT"))
    # J1 only: the accepting time/range owner already established clock semantics.
    if (plan.owner == "time" and plan.unit == "시") or (plan.numeric_form == "range" and plan.unit == "시"):
        for component in mapped:
            end = component.render_span.end
            if plan.text.startswith("-", end) and not any(e[0] == end for e in edits):
                edits.append((end, end + 1, "", "NUM_CLOCK_JOIN"))
    edits.sort()
    text = plan.text
    for start, end, replacement, _ in reversed(edits):
        text = text[:start] + replacement + text[end:]
    def project(position: int) -> int:
        return position + sum(len(value) - (end - start)
                              for start, end, value, _ in edits if end <= position)
    def numeric_end(position: int) -> int:
        return project(position) + int(any(start == position and end > start and value == "~"
                                          for start, end, value, _ in edits))
    components = tuple(replace(c, render_span=SourceSpan(project(c.render_span.start), numeric_end(c.render_span.end)),
                       vowels=tuple(replace(v, render_span=SourceSpan(project(v.render_span.start), numeric_end(v.render_span.end))
                                             if v.render_span is not None else None)
                                    for v in c.vowels)) for c in mapped)
    boundaries = []
    for boundary in plan.boundaries:
        span = boundary.render_span
        if span is None:
            boundaries.append(boundary)
            continue
        # Split combined boundary records rather than retaining deleted hyphens.
        for position in range(span.start, span.end):
            if any(start <= position < end for start, end, _, _ in edits):
                continue
            shifted = project(position)
            boundaries.append(replace(boundary, text=plan.text[position],
                                      render_span=SourceSpan(shifted, shifted + 1)))
    for start, end, value, rule in edits:
        if value:
            # An insertion at this position includes its own delta; subtract it.
            position = project(start) - (len(value) if start == end else 0)
            boundaries.append(NumericBoundary("vowel_length", "generated", value,
                                              render_span=SourceSpan(position, position + len(value))))
    return replace(plan, text=text, components=components, boundaries=tuple(boundaries),
                   marker_status="rendered", render_edits=tuple(edits))


def apply_numeric_surface(surface, plan: NumericReadingPlan | None):
    """Keep source-exact pieces and explicit unit-copy provenance intact."""
    if plan is not None and surface.render_pieces is not None:
        pieces = surface.render_pieces
        if "".join(p.text for p in pieces) == plan.text:
            # Cumulative piece offsets establish origin without searching for
            # repeated text. Original spaces remain original in the render map.
            intervals = []
            offset = 0
            for piece in pieces:
                intervals.append((offset, offset + len(piece.text), piece))
                offset += len(piece.text)
            boundaries = []
            for boundary in plan.boundaries:
                if boundary.render_span is None:
                    boundaries.append(boundary)
                    continue
                for pos in range(boundary.render_span.start, boundary.render_span.end):
                    piece_start, _, piece = next(i for i in intervals if i[0] <= pos < i[1])
                    original = piece.provenance.startswith("ORIGINAL")
                    source = None
                    if original and piece.source_span is not None and len(piece.text) == piece.source_span.end - piece.source_span.start:
                        source = SourceSpan(piece.source_span.start + pos - piece_start,
                                            piece.source_span.start + pos - piece_start + 1)
                    boundaries.append(replace(boundary, text=plan.text[pos],
                        origin="original" if original else "generated", source_span=source,
                        render_span=SourceSpan(pos, pos + 1)))
            plan = replace(plan, boundaries=tuple(boundaries))
    rendered = render_numeric_plan(plan)
    if rendered is None:
        return
    if surface.render_pieces is not None and rendered.render_edits:
        pieces = surface.render_pieces
        if "".join(p.text for p in pieces) != plan.text:
            surface.numeric_plan = replace(plan, marker_status="piece_coordinates_unresolved")
            return
        assignments = [[] for _ in pieces]
        offsets = []
        cursor = 0
        for piece in pieces:
            offsets.append(cursor)
            cursor += len(piece.text)
        for edit in rendered.render_edits:
            start, end, value, rule = edit
            eligible = [i for i, piece in enumerate(pieces)
                        if piece.provenance.startswith("GENERATED")
                        and offsets[i] <= start and end <= offsets[i] + len(piece.text)]
            if not eligible:
                surface.numeric_plan = replace(plan, marker_status="piece_coordinates_unresolved")
                return
            # Insert at the preceding generated numeral's end; replacements
            # must lie inside the generated boundary piece, never original text.
            i = eligible[0]
            assignments[i].append((start - offsets[i], end - offsets[i], value, rule))
        for piece, edits in zip(pieces, assignments):
            for start, end, value, rule in reversed(edits):
                piece.text = piece.text[:start] + value + piece.text[end:]
            if edits:
                piece.metadata = {**piece.metadata, "numeric_render_rules": tuple(e[3] for e in edits)}
    surface.reading = rendered.text
    surface.numeric_plan = rendered
