from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum


class SurfaceType(StrEnum):
    LEXICAL_TOKEN = "LEXICAL_TOKEN"
    ACRONYM_SURFACE = "ACRONYM_SURFACE"
    ALLOWED_ACRONYM_WITH_PARTICLE = "ALLOWED_ACRONYM_WITH_PARTICLE"
    ACRONYM_WITH_LEXICAL_SUFFIX_SURFACE = "ACRONYM_WITH_LEXICAL_SUFFIX_SURFACE"
    LEXICAL_MIDDLEDOT_SURFACE = "LEXICAL_MIDDLEDOT_SURFACE"
    SINGLE_LETTER_HYPHEN_SURFACE = "SINGLE_LETTER_HYPHEN_SURFACE"
    NUMERIC_PREFIXED_NOUN_SURFACE = "NUMERIC_PREFIXED_NOUN_SURFACE"
    NUMERIC_UNIT_SURFACE = "NUMERIC_UNIT_SURFACE"
    NUMERIC_CURRENCY_SURFACE = "NUMERIC_CURRENCY_SURFACE"
    COUNTER_SURFACE = "COUNTER_SURFACE"
    RANGE_SURFACE = "RANGE_SURFACE"
    RANGE_WITH_UNIT_SURFACE = "RANGE_WITH_UNIT_SURFACE"
    LARGE_UNIT_ATOMIC_SURFACE = "LARGE_UNIT_ATOMIC_SURFACE"
    SIGNED_DEGREE_SURFACE = "SIGNED_DEGREE_SURFACE"
    EVENT_SURFACE = "EVENT_SURFACE"
    PROTECTED_LITERAL_SURFACE = "PROTECTED_LITERAL_SURFACE"


class HelperKind(StrEnum):
    GENERIC_STRING = "generic_string_helper"
    STRUCTURED_PARSER = "structured_parser_helper"
    TYPED_SURFACE = "typed_surface_helper"
    PROSODY = "prosody_helper"


@dataclass(frozen=True, slots=True)
class PlainSegmentPolicy:
    helper_name: str
    helper_kind: HelperKind
    owner_stage: str
    skip_hangul: bool = False


@dataclass(frozen=True, slots=True)
class Surface:
    """
    Internal typed surface contract.

    Allowed operations by type:
    - ACRONYM_SURFACE: opaque reading only; attach_particle() preserves the input particle.
    - ALLOWED_ACRONYM_WITH_PARTICLE: opaque, particle already attached; no further rewrite.
    - LEXICAL_MIDDLEDOT_SURFACE / SINGLE_LETTER_HYPHEN_SURFACE: opaque, no particle rewrite.
    - NUMERIC_UNIT_SURFACE / NUMERIC_CURRENCY_SURFACE / COUNTER_SURFACE:
      limited particle attachment or phonetic binding is allowed.
    - LARGE_UNIT_ATOMIC_SURFACE / SIGNED_DEGREE_SURFACE / EVENT_SURFACE:
      opaque final readings; no internal rewrite.
    - LEXICAL_TOKEN: plain lexical material; never enters particle rewrite helpers.

    Forbidden operations:
    - Any opaque surface must not be internally segmented or rewritten.
    - LEXICAL_TOKEN must not be passed to particle-changing helpers.
    """

    surface_text: str
    surface_type: SurfaceType
    opaque: bool
    allow_particle_attachment: bool
    allow_phonetic_binding: bool
    allow_prosody_inside: bool
    source_stage: str
    restorable: bool = True
    trailing_particle: str | None = None

    @property
    def rendered_text(self) -> str:
        return f"{self.surface_text}{self.trailing_particle or ''}"

    def attach_particle(self, particle: str, surface_type: SurfaceType | None = None) -> "Surface":
        if not self.allow_particle_attachment:
            raise ValueError(f"particle attachment is not allowed for {self.surface_type}")
        if self.trailing_particle is not None:
            raise ValueError(f"particle attachment already fixed for {self.surface_type}")
        return replace(
            self,
            surface_type=surface_type or self.surface_type,
            trailing_particle=particle,
        )


@dataclass(frozen=True, slots=True)
class RenderedSurfaceSpan:
    start: int
    end: int
    surface: Surface


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    text: str
    rendered_surfaces: tuple[RenderedSurfaceSpan, ...]
    ownership_collisions: tuple[str, ...] = ()
    gate_logs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Segment:
    text: str
    surface: Surface | None = None

    @property
    def is_surface(self) -> bool:
        return self.surface is not None


class SurfaceRegistry:
    _PLACEHOLDER_PATTERN = re.compile(r"__surface__(?P<index>[a-z]+)__")

    def __init__(self) -> None:
        self._surfaces: list[Surface] = []

    def register(self, surface: Surface) -> str:
        index = len(self._surfaces)
        self._surfaces.append(surface)
        return f"__surface__{self._encode_index(index)}__"

    def get(self, placeholder: str) -> Surface | None:
        match = self._PLACEHOLDER_PATTERN.fullmatch(placeholder)
        if match is None:
            return None
        index = self._decode_index(match.group("index"))
        if not 0 <= index < len(self._surfaces):
            return None
        return self._surfaces[index]

    def render(self, text: str) -> NormalizationResult:
        rendered: list[str] = []
        spans: list[RenderedSurfaceSpan] = []
        cursor = 0

        for match in self._PLACEHOLDER_PATTERN.finditer(text):
            rendered.append(text[cursor:match.start()])
            literal = "".join(rendered)
            surface = self.get(match.group(0))
            if surface is None:
                rendered.append(match.group(0))
            else:
                start = len(literal)
                rendered.append(surface.rendered_text)
                end = start + len(surface.rendered_text)
                spans.append(RenderedSurfaceSpan(start, end, surface))
            cursor = match.end()

        rendered.append(text[cursor:])
        return NormalizationResult("".join(rendered), tuple(spans))

    def split_segments(self, text: str) -> list[Segment]:
        segments: list[Segment] = []
        cursor = 0

        for match in self._PLACEHOLDER_PATTERN.finditer(text):
            if match.start() > cursor:
                segments.append(Segment(text[cursor:match.start()]))
            surface = self.get(match.group(0))
            if surface is None:
                segments.append(Segment(match.group(0)))
            else:
                segments.append(Segment(match.group(0), surface))
            cursor = match.end()

        if cursor < len(text):
            segments.append(Segment(text[cursor:]))
        return segments

    def rewrite_plain_segments(
        self,
        text: str,
        rewriter: callable[[str], str],
        *,
        skip_hangul: bool = False,
        policy: PlainSegmentPolicy | None = None,
        collision_log: list[str] | None = None,
    ) -> str:
        active_policy = policy or PlainSegmentPolicy(
            helper_name="<anonymous>",
            helper_kind=HelperKind.GENERIC_STRING if skip_hangul else HelperKind.STRUCTURED_PARSER,
            owner_stage="unspecified",
            skip_hangul=skip_hangul,
        )
        if active_policy.skip_hangul != skip_hangul:
            raise AssertionError("plain segment policy skip_hangul must match rewrite invocation")
        if active_policy.skip_hangul and active_policy.helper_kind != HelperKind.GENERIC_STRING:
            raise AssertionError("skip_hangul is only allowed for generic string helpers")

        parts: list[str] = []
        for segment in self.split_segments(text):
            if segment.is_surface:
                parts.append(segment.text)
            elif active_policy.skip_hangul and re.search(r"[가-힣]", segment.text):
                if collision_log is not None:
                    collision_log.append(
                        f"{active_policy.helper_name}: skipped Hangul plain segment under {active_policy.owner_stage}: {segment.text!r}"
                    )
                parts.append(segment.text)
            else:
                parts.append(rewriter(segment.text))
        return "".join(parts)

    @staticmethod
    def _encode_index(index: int) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        value = index + 1
        chars: list[str] = []
        while value > 0:
            value, remainder = divmod(value - 1, 26)
            chars.append(alphabet[remainder])
        return "".join(reversed(chars))

    @staticmethod
    def _decode_index(text: str) -> int:
        value = 0
        for char in text:
            value = value * 26 + (ord(char) - ord("a") + 1)
        return value - 1


def surface_from_type(
    surface_text: str,
    surface_type: SurfaceType,
    *,
    source_stage: str,
) -> Surface:
    opaque_types = {
        SurfaceType.ACRONYM_SURFACE,
        SurfaceType.ALLOWED_ACRONYM_WITH_PARTICLE,
        SurfaceType.ACRONYM_WITH_LEXICAL_SUFFIX_SURFACE,
        SurfaceType.LEXICAL_MIDDLEDOT_SURFACE,
        SurfaceType.SINGLE_LETTER_HYPHEN_SURFACE,
        SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE,
        SurfaceType.RANGE_SURFACE,
        SurfaceType.RANGE_WITH_UNIT_SURFACE,
        SurfaceType.LARGE_UNIT_ATOMIC_SURFACE,
        SurfaceType.SIGNED_DEGREE_SURFACE,
        SurfaceType.EVENT_SURFACE,
        SurfaceType.PROTECTED_LITERAL_SURFACE,
    }
    particle_types = {
        SurfaceType.ACRONYM_SURFACE,
        SurfaceType.ALLOWED_ACRONYM_WITH_PARTICLE,
        SurfaceType.ACRONYM_WITH_LEXICAL_SUFFIX_SURFACE,
        SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE,
        SurfaceType.NUMERIC_UNIT_SURFACE,
        SurfaceType.NUMERIC_CURRENCY_SURFACE,
        SurfaceType.COUNTER_SURFACE,
        SurfaceType.RANGE_SURFACE,
        SurfaceType.RANGE_WITH_UNIT_SURFACE,
        SurfaceType.LARGE_UNIT_ATOMIC_SURFACE,
        SurfaceType.SIGNED_DEGREE_SURFACE,
        SurfaceType.EVENT_SURFACE,
    }
    phonetic_types = {
        SurfaceType.NUMERIC_UNIT_SURFACE,
        SurfaceType.NUMERIC_CURRENCY_SURFACE,
        SurfaceType.COUNTER_SURFACE,
    }
    return Surface(
        surface_text=surface_text,
        surface_type=surface_type,
        opaque=surface_type in opaque_types,
        allow_particle_attachment=surface_type in particle_types,
        allow_phonetic_binding=surface_type in phonetic_types,
        allow_prosody_inside=False if surface_type in opaque_types else True,
        source_stage=source_stage,
    )
