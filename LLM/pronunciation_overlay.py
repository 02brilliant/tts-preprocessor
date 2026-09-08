from __future__ import annotations

from dataclasses import dataclass

from LLM.pronunciation_lexicon import (
    build_stage5_deterministic_pronunciation_mutations,
)
from LLM.provenance import minimal_snapshot
from LLM.validation_models import (
    AllowedMutation,
    NormalizationSnapshot,
    NormalizedSpan,
)


@dataclass(frozen=True)
class PronunciationOverlayResult:
    text: str
    snapshot: NormalizationSnapshot
    applied_mutations: tuple[AllowedMutation, ...] = ()


def apply_pronunciation_overlay(
    normalized_text: str,
    *,
    stage: int,
    snapshot: NormalizationSnapshot | None = None,
) -> PronunciationOverlayResult:
    """Apply fixed pronunciation entries for stage 5 without changing stage 2.

    Stage 3/4 leave the text unchanged. Stage 5 applies the unified exact
    registry once and locks every generated pronunciation so its LLM pass can
    add only closed, stage-specific changes around it.
    """

    if not isinstance(normalized_text, str):
        raise TypeError("normalized_text must be str")
    if stage not in {3, 4, 5}:
        raise ValueError("stage must be 3, 4, or 5")
    active_snapshot = snapshot or minimal_snapshot(normalized_text)
    if active_snapshot.normalized_text != normalized_text:
        raise ValueError("snapshot does not match normalized_text")

    mutations = (
        build_stage5_deterministic_pronunciation_mutations(
            normalized_text,
            snapshot=active_snapshot,
        )
        if stage == 5
        else ()
    )
    return apply_locked_pronunciation_mutations(
        normalized_text,
        mutations=mutations,
        snapshot=active_snapshot,
        owner="stage5_standard_pronunciation",
        provenance="GENERATED_STAGE5_PRONUNCIATION",
    )


def apply_locked_pronunciation_mutations(
    normalized_text: str,
    *,
    mutations: tuple[AllowedMutation, ...],
    snapshot: NormalizationSnapshot,
    owner: str,
    provenance: str,
) -> PronunciationOverlayResult:
    """Apply non-overlapping exact mutations and lock the generated spans."""

    if snapshot.normalized_text != normalized_text:
        raise ValueError("snapshot does not match normalized_text")
    if not mutations:
        return PronunciationOverlayResult(normalized_text, snapshot)

    replacements = tuple(
        (mutation, mutation.allowed_outputs[0]) for mutation in mutations
    )
    output = normalized_text
    for mutation, replacement in reversed(replacements):
        output = output[: mutation.start] + replacement + output[mutation.end :]

    projected_spans: list[NormalizedSpan] = []
    for span in snapshot.spans:
        if any(
            mutation.start < span.normalized_end
            and span.normalized_start < mutation.end
            for mutation, _replacement in replacements
        ):
            continue
        start = _project_index(span.normalized_start, replacements)
        end = _project_index(span.normalized_end, replacements)
        projected_spans.append(
            NormalizedSpan(
                normalized_start=start,
                normalized_end=end,
                text=output[start:end],
                source_start=span.source_start,
                source_end=span.source_end,
                owner=span.owner,
                provenance=span.provenance,
                locked=span.locked,
                protected=span.protected,
            )
        )

    for mutation, replacement in replacements:
        start = _project_index(mutation.start, replacements)
        source_span = next(
            (
                span
                for span in snapshot.spans
                if span.normalized_start == mutation.start
                and span.normalized_end == mutation.end
            ),
            None,
        )
        projected_spans.append(
            NormalizedSpan(
                normalized_start=start,
                normalized_end=start + len(replacement),
                text=replacement,
                source_start=None if source_span is None else source_span.source_start,
                source_end=None if source_span is None else source_span.source_end,
                owner=owner,
                provenance=provenance,
                locked=True,
                protected=False,
            )
        )

    updated_snapshot = NormalizationSnapshot(
        normalized_text=output,
        spans=tuple(
            sorted(
                projected_spans,
                key=lambda span: (span.normalized_start, span.normalized_end),
            )
        ),
    )
    return PronunciationOverlayResult(output, updated_snapshot, mutations)


def _project_index(
    index: int,
    replacements: tuple[tuple[AllowedMutation, str], ...],
) -> int:
    return index + sum(
        len(replacement) - len(mutation.source_text)
        for mutation, replacement in replacements
        if mutation.end <= index
    )


__all__ = [
    "PronunciationOverlayResult",
    "apply_locked_pronunciation_mutations",
    "apply_pronunciation_overlay",
]
