from __future__ import annotations

from engine.span_engine.models import ShadowUnit, SpanToken

SHADOW_KIND_BY_TOKEN_KIND = {
    "KOREAN_LITERAL": "KOREAN_LITERAL",
    "SPACE_LOCK": "KOREAN_SPACE",
    "PUNCT_LOCK": "KOREAN_PUNCT",
}


def build_shadow_buffer(tokens: list[SpanToken]) -> list[ShadowUnit]:
    if not isinstance(tokens, list):
        raise TypeError("tokens must be list[SpanToken]")

    shadow: list[ShadowUnit] = []
    for token in tokens:
        if not isinstance(token, SpanToken):
            raise TypeError("tokens must contain SpanToken")
        shadow_kind = SHADOW_KIND_BY_TOKEN_KIND.get(token.kind)
        if shadow_kind is None:
            continue
        shadow.append(ShadowUnit(shadow_kind, token.raw, token.span))
    return shadow
