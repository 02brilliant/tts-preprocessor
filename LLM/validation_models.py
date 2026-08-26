from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedSpan:
    normalized_start: int
    normalized_end: int
    text: str
    source_start: int | None
    source_end: int | None
    owner: str | None
    provenance: str
    locked: bool
    protected: bool

    def __post_init__(self) -> None:
        if self.normalized_start < 0 or self.normalized_end < self.normalized_start:
            raise ValueError("invalid normalized span")
        if self.normalized_end - self.normalized_start != len(self.text):
            raise ValueError("normalized span length does not match text")


@dataclass(frozen=True)
class NormalizationSnapshot:
    normalized_text: str
    spans: tuple[NormalizedSpan, ...]


@dataclass(frozen=True)
class AllowedMutation:
    start: int
    end: int
    kind: str
    source_text: str
    allowed_outputs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("invalid mutation span")
        if self.end - self.start != len(self.source_text):
            raise ValueError("mutation span length does not match source text")
        if not self.allowed_outputs:
            raise ValueError("allowed_outputs must not be empty")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: tuple[ValidationIssue, ...] = ()


__all__ = [
    "AllowedMutation",
    "NormalizationSnapshot",
    "NormalizedSpan",
    "ValidationIssue",
    "ValidationResult",
]
