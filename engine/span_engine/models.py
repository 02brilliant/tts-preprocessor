from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SPAN_TOKEN_KINDS = frozenset(
    {
        "KOREAN_LITERAL",
        "SPACE_LOCK",
        "PUNCT_LOCK",
        "BOUNDARY_LITERAL",
        "PLAIN",
        "SURFACE",
    }
)
LOCKED_TOKEN_KINDS = frozenset({"KOREAN_LITERAL", "SPACE_LOCK", "PUNCT_LOCK"})

SHADOW_UNIT_KINDS = frozenset(
    {
        "KOREAN_LITERAL",
        "KOREAN_SPACE",
        "KOREAN_PUNCT",
        "PARTICLE_LITERAL",
    }
)

RENDER_PROVENANCE_VALUES = frozenset(
    {
        "ORIGINAL_KOREAN",
        "ORIGINAL_SPACE",
        "ORIGINAL_PUNCT",
        "ORIGINAL_BOUNDARY",
        "GENERATED_READING",
        "GENERATED_PARTICLE",
        "GENERATED_PUNCT",
    }
)

CLAIM_TYPES = frozenset({"surface", "preserve", "gate_fail", "lock", "shadow"})


def _ensure_str_field(name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")


def _ensure_optional_str_field(name: str, value: Any) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be str or None")


def _ensure_bool_field(name: str, value: Any) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")


def _ensure_source_span(name: str, value: Any) -> None:
    if not isinstance(value, SourceSpan):
        raise TypeError(f"{name} must be SourceSpan")


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int

    def __post_init__(self) -> None:
        if not isinstance(self.start, int):
            raise TypeError("start must be int")
        if not isinstance(self.end, int):
            raise TypeError("end must be int")
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end < self.start:
            raise ValueError("end must be >= start")

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class SourceChar:
    char: str
    index: int

    def __post_init__(self) -> None:
        _ensure_str_field("char", self.char)
        if len(self.char) != 1:
            raise ValueError("char must be a single Python str code point")
        if not isinstance(self.index, int):
            raise TypeError("index must be int")
        if self.index < 0:
            raise ValueError("index must be >= 0")


@dataclass
class SpanToken:
    kind: str
    raw: str
    span: SourceSpan
    immutable: bool = False
    owner: str | None = None
    surface_type: str | None = None
    reading: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in SPAN_TOKEN_KINDS:
            raise ValueError(f"invalid SpanToken kind: {self.kind!r}")
        _ensure_str_field("raw", self.raw)
        _ensure_source_span("span", self.span)
        _ensure_bool_field("immutable", self.immutable)
        _ensure_optional_str_field("owner", self.owner)
        _ensure_optional_str_field("surface_type", self.surface_type)
        _ensure_optional_str_field("reading", self.reading)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")
        if self.kind in LOCKED_TOKEN_KINDS:
            self.immutable = True


@dataclass(frozen=True)
class ShadowUnit:
    kind: str
    raw: str
    span: SourceSpan

    def __post_init__(self) -> None:
        if self.kind not in SHADOW_UNIT_KINDS:
            raise ValueError(f"invalid ShadowUnit kind: {self.kind!r}")
        _ensure_str_field("raw", self.raw)
        _ensure_source_span("span", self.span)


@dataclass
class RenderPiece:
    text: str
    provenance: str
    source_span: SourceSpan | None = None
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_str_field("text", self.text)
        if self.provenance not in RENDER_PROVENANCE_VALUES:
            raise ValueError(f"invalid RenderPiece provenance: {self.provenance!r}")
        if self.source_span is not None:
            _ensure_source_span("source_span", self.source_span)
        _ensure_optional_str_field("owner", self.owner)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")


@dataclass
class Surface:
    surface_type: str
    owner: str
    raw: str
    span: SourceSpan
    reading: str | None = None
    render_pieces: list[RenderPiece] | None = None
    trailing_particle: str | None = None
    trailing_particle_span: SourceSpan | None = None
    protected: bool = True
    allow_reentry: bool = False
    allow_prosody_inside: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_str_field("surface_type", self.surface_type)
        _ensure_str_field("owner", self.owner)
        _ensure_str_field("raw", self.raw)
        _ensure_source_span("span", self.span)
        _ensure_optional_str_field("reading", self.reading)
        _ensure_optional_str_field("trailing_particle", self.trailing_particle)
        if self.trailing_particle_span is not None:
            _ensure_source_span("trailing_particle_span", self.trailing_particle_span)
            if self.trailing_particle is None:
                raise ValueError(
                    "trailing_particle_span requires trailing_particle"
                )
        if self.render_pieces is not None:
            if not isinstance(self.render_pieces, list):
                raise TypeError("render_pieces must be list[RenderPiece] or None")
            for piece in self.render_pieces:
                if not isinstance(piece, RenderPiece):
                    raise TypeError("render_pieces must contain RenderPiece")
        _ensure_bool_field("protected", self.protected)
        _ensure_bool_field("allow_reentry", self.allow_reentry)
        _ensure_bool_field("allow_prosody_inside", self.allow_prosody_inside)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")


@dataclass
class SurfaceCandidate:
    core_span: SourceSpan
    full_span: SourceSpan
    owner: str
    surface_type: str | None = None
    trailing_particle_span: SourceSpan | None = None
    suffix_spans: list[SourceSpan] = field(default_factory=list)
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_source_span("core_span", self.core_span)
        _ensure_source_span("full_span", self.full_span)
        _ensure_str_field("owner", self.owner)
        _ensure_optional_str_field("surface_type", self.surface_type)
        _ensure_optional_str_field("reason", self.reason)
        if self.trailing_particle_span is not None:
            _ensure_source_span("trailing_particle_span", self.trailing_particle_span)
        if not (
            self.full_span.start
            <= self.core_span.start
            <= self.core_span.end
            <= self.full_span.end
        ):
            raise ValueError("core_span must be contained in full_span")
        if not isinstance(self.suffix_spans, list):
            raise TypeError("suffix_spans must be list[SourceSpan]")
        for suffix_span in self.suffix_spans:
            _ensure_source_span("suffix_span", suffix_span)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")


@dataclass
class ClaimedRange:
    span: SourceSpan
    owner: str
    claim_type: str
    surface_type: str | None = None
    reason: str | None = None
    reentry_allowed: bool = False

    def __post_init__(self) -> None:
        _ensure_source_span("span", self.span)
        _ensure_str_field("owner", self.owner)
        if self.claim_type not in CLAIM_TYPES:
            raise ValueError(f"invalid claim_type: {self.claim_type!r}")
        _ensure_optional_str_field("surface_type", self.surface_type)
        _ensure_optional_str_field("reason", self.reason)
        _ensure_bool_field("reentry_allowed", self.reentry_allowed)


@dataclass
class ClaimCollisionLog:
    attempted_owner: str
    attempted_span: SourceSpan
    existing_owner: str
    existing_span: SourceSpan
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_str_field("attempted_owner", self.attempted_owner)
        _ensure_source_span("attempted_span", self.attempted_span)
        _ensure_str_field("existing_owner", self.existing_owner)
        _ensure_source_span("existing_span", self.existing_span)
        _ensure_str_field("reason", self.reason)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")


@dataclass
class TraceLogEntry:
    stage: str
    event: str
    span: SourceSpan | None = None
    raw: str | None = None
    owner: str | None = None
    surface_type: str | None = None
    decision: str | None = None
    reason: str | None = None
    action: str | None = None
    provenance: str | None = None
    expected: str | None = None
    actual: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_str_field("stage", self.stage)
        _ensure_str_field("event", self.event)
        if self.span is not None:
            _ensure_source_span("span", self.span)
        _ensure_optional_str_field("raw", self.raw)
        _ensure_optional_str_field("owner", self.owner)
        _ensure_optional_str_field("surface_type", self.surface_type)
        _ensure_optional_str_field("decision", self.decision)
        _ensure_optional_str_field("reason", self.reason)
        _ensure_optional_str_field("action", self.action)
        _ensure_optional_str_field("provenance", self.provenance)
        _ensure_optional_str_field("expected", self.expected)
        _ensure_optional_str_field("actual", self.actual)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")


@dataclass
class ValidationLog:
    kind: str
    passed: bool
    expected: str | None = None
    actual: str | None = None
    span: SourceSpan | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure_str_field("kind", self.kind)
        _ensure_bool_field("passed", self.passed)
        _ensure_optional_str_field("expected", self.expected)
        _ensure_optional_str_field("actual", self.actual)
        if self.span is not None:
            _ensure_source_span("span", self.span)
        _ensure_optional_str_field("reason", self.reason)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be dict")


@dataclass
class ValidationResult:
    passed: bool
    logs: list[ValidationLog] = field(default_factory=list)

    def __post_init__(self) -> None:
        _ensure_bool_field("passed", self.passed)
        if not isinstance(self.logs, list):
            raise TypeError("logs must be list[ValidationLog]")
        for log in self.logs:
            if not isinstance(log, ValidationLog):
                raise TypeError("logs must contain ValidationLog")


@dataclass
class TransformTrace:
    source_map_logs: list[Any] = field(default_factory=list)
    tokenization_logs: list[Any] = field(default_factory=list)
    shadow_logs: list[Any] = field(default_factory=list)
    claim_logs: list[Any] = field(default_factory=list)
    claim_collision_logs: list[Any] = field(default_factory=list)
    gate_logs: list[Any] = field(default_factory=list)
    parser_logs: list[Any] = field(default_factory=list)
    fallback_logs: list[Any] = field(default_factory=list)
    preserve_logs: list[Any] = field(default_factory=list)
    particle_exception_logs: list[Any] = field(default_factory=list)
    render_logs: list[Any] = field(default_factory=list)
    validation_logs: list[Any] = field(default_factory=list)
    prosody_logs: list[Any] = field(default_factory=list)
    bracket_filter_logs: list[Any] = field(default_factory=list)


@dataclass
class TransformOutput:
    normalized_text: str
    render_pieces: list[RenderPiece]
    trace: TransformTrace | None = None

    def __post_init__(self) -> None:
        _ensure_str_field("normalized_text", self.normalized_text)
        if not isinstance(self.render_pieces, list):
            raise TypeError("render_pieces must be list[RenderPiece]")
        for piece in self.render_pieces:
            if not isinstance(piece, RenderPiece):
                raise TypeError("render_pieces must contain RenderPiece")
        if self.trace is not None and not isinstance(self.trace, TransformTrace):
            raise TypeError("trace must be TransformTrace or None")


__all__ = [
    "CLAIM_TYPES",
    "ClaimCollisionLog",
    "LOCKED_TOKEN_KINDS",
    "RENDER_PROVENANCE_VALUES",
    "SHADOW_UNIT_KINDS",
    "SPAN_TOKEN_KINDS",
    "ClaimedRange",
    "RenderPiece",
    "ShadowUnit",
    "SourceChar",
    "SourceSpan",
    "SpanToken",
    "Surface",
    "SurfaceCandidate",
    "TraceLogEntry",
    "TransformOutput",
    "TransformTrace",
    "ValidationLog",
    "ValidationResult",
]
