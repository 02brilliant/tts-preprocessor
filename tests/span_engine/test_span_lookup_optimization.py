from dataclasses import asdict
import random
from types import SimpleNamespace

import pytest

from engine.span_engine.claim_registry import SurfaceClaimRegistry, spans_overlap
from engine.span_engine.models import ClaimedRange, SourceSpan, SpanToken
from engine.span_engine.render import _render_original_range, render_tokens_with_surfaces
from engine.span_engine.transform import _surface_internal_shadow_spans
from engine.span_engine import compound_unit


def test_claim_index_preserves_nested_overlap_order_and_collision_blocker():
    rng = random.Random(42)
    registry = SurfaceClaimRegistry()
    groups = list(range(60))
    rng.shuffle(groups)
    for group in groups:
        start = group * 20
        registry.claim(ClaimedRange(SourceSpan(start, start + 15), "parent", "surface",
                                    reentry_allowed=True))
        registry.claim(ClaimedRange(SourceSpan(start + 2, start + 4), "child", "lock"))
        registry.claim(ClaimedRange(SourceSpan(start + 8, start + 9), "child", "preserve"))
    for _ in range(500):
        start = rng.randrange(1220)
        span = SourceSpan(start, start + rng.randrange(30))
        expected = [claim for claim in registry.claims if spans_overlap(claim.span, span)]
        assert registry.find_overlaps(span) == expected
        assert registry.is_blocked(span) == any(not c.reentry_allowed for c in expected)
        blocker = next((c for c in expected if c.span == span or not (
            c.reentry_allowed and c.span.start <= span.start <= span.end <= c.span.end)), None)
        assert registry.can_claim(span, "number") == (blocker is None)
        if blocker is not None:
            with pytest.raises(ValueError):
                registry.claim(ClaimedRange(span, "number", "surface"))
            assert registry.collision_logs[-1].existing_span == blocker.span


@pytest.mark.parametrize("unordered", [False, True])
def test_render_lookup_retains_partial_tokens_and_provenance(unordered):
    raw = "가나다라마바사아자차"
    tokens = [SpanToken("KOREAN_LITERAL", raw[:5], SourceSpan(0, 5)),
              SpanToken("KOREAN_LITERAL", raw[5:], SourceSpan(5, 10))]
    if unordered:
        tokens.reverse()
    # Multiple gaps within the same token must not advance past that token.
    from engine.span_engine.models import Surface
    surfaces = [Surface(span=SourceSpan(a, b), raw=raw[a:b], owner="test",
                        surface_type="NUMBER_SURFACE", reading="수")
                for a, b in [(1, 2), (3, 4), (6, 8)]]
    output = render_tokens_with_surfaces(raw, tokens, surfaces)
    original = [asdict(p) for p in output if p.provenance == "ORIGINAL_KOREAN"]
    expected = [asdict(p) for a, b in [(0, 1), (2, 3), (4, 6), (8, 10)]
                for p in _render_original_range(raw, tokens, a, b)]
    assert original == expected


@pytest.mark.parametrize(("owner", "metadata", "overlap"), [
    ("currency", {"reason": "decimal_large_unit_krw_expansion"}, True),
    ("currency", {"reason": "large_unit_currency_suffix"}, True),
    ("currency", {}, False), ("large_unit_atomic", {}, True),
    ("mixed_integer_atomic", {}, True), ("mixed_decimal_atomic", {}, True),
    ("phrase_dictionary", {}, True), ("counter_noun", {}, True),
    ("multiplier", {}, True),
    ("parenthesized_hangul_alias", {"consume_parenthetical_alias": True}, True),
    ("parenthesized_hangul_alias", {"consume_parenthetical_alias": 1}, False),
    ("numeric_suffix", {"reason": "prefixed_ordinal_numeric_core"}, True),
    ("numeric_suffix", {"reason": "prefixed_ordinal_numeric_suffix"}, True),
    ("numeric_suffix", {}, False),
    ("time", {"compact_si_direction": True}, True), ("time", {}, False),
])
def test_shadow_lookup_preserves_closed_exceptions(owner, metadata, overlap):
    surface = SimpleNamespace(span=SourceSpan(10, 20), owner=owner, metadata=metadata)
    units = [SimpleNamespace(span=SourceSpan(a, b), kind=kind)
             for a, b, kind in [(0, 30, "KOREAN_LITERAL"), (0, 10, "KOREAN_LITERAL"),
                                 (9, 11, "KOREAN_LITERAL"), (12, 13, "KOREAN_LITERAL"),
                                 (19, 21, "KOREAN_LITERAL"), (20, 22, "KOREAN_LITERAL"),
                                 (10, 11, "KOREAN_SPACE"), (20, 20, "KOREAN_SPACE")]]
    random.Random(5).shuffle(units)
    expected = {(10, 11), (20, 20)}
    if overlap:
        expected |= {(0, 30), (9, 11), (12, 13), (19, 21)}
    assert _surface_internal_shadow_spans([surface], units) == expected


@pytest.mark.parametrize("matcher", [compound_unit._match_compound_candidate,
                                     compound_unit._match_compound_exact_candidate])
@pytest.mark.parametrize("raw", ["25unknown", "2.50unknown", "1,234unknown",
                                "00unknown", "1,23unknown", "100000000unknown"])
def test_compound_numeric_prefix_is_scanned_once(monkeypatch, matcher, raw):
    calls = []
    consume = compound_unit._consume_integer
    def counted(text, start):
        calls.append(start)
        return consume(text, start)
    monkeypatch.setattr(compound_unit, "_consume_integer", counted)
    assert matcher(raw, 0, []) == []
    assert calls == [0]
