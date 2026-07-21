# Production Refactor P5: transform trace and render provenance audit

## Scope and invariants

P5 audits the normal successful core path from `engine.main.transform` through
the production adapter and `transform_with_trace` into
`_transform_core_with_trace`.  It does not change segment fallback, whole-input
preserve, claim order, parser dispatch, validation decisions, prosody policy,
or bracket policy.  Normalized output, trace ordering and fields, source spans,
RenderPiece provenance, debug serialization, API and binary behavior are
byte-exact invariants.

## Production call graph

| stage | caller -> callee | input -> output | mutable/observable state | failure effect |
| --- | --- | --- | --- | --- |
| facade | `engine.main.transform` -> production adapter | `str` -> `str` | none | adapter contract applies |
| traced entry | `transform_with_trace` -> `_transform_core_with_trace` | `str` -> `TransformOutput` | final trace is observable | exceptions enter the existing outer fallback path |
| source/token | source map, tokenization, token validation | source text -> chars/tokens | immutable source spans | exception escapes core |
| claims | bracket protection, `claim_surfaces` | tokens/ranges -> candidates and registry logs | claim/collision order | exception escapes core |
| parse/render | `parse_candidates`, `render_tokens_with_surfaces` | candidates -> surfaces -> pieces | surface and piece order | exception escapes core |
| post-render | slash alias, safe particle exception | pieces -> pieces/logs | piece order, provenance and consumed spans | exception escapes core |
| validation | `validate_shadow` | pieces/shadow/consumed spans -> result | ordered ValidationLog values | failed result raises before prosody and before trace assembly |
| prosody | base then extra comma adapters | pieces -> pieces/logs | generated punctuation order | exception escapes core |
| bracket filter | join pre-filter text, final bracket filter | pieces -> normalized text/logs | output pieces stay pre-filter pieces; normalized text is filtered | exception escapes core |
| trace | ordered field population | all successful intermediates -> `TransformTrace` | every list and entry is debug-observable | happens only after every prior stage succeeds |

The outer `_transform_hangul_with_segment_fallback`, `_transform_fallback_segment`,
`_fallback_segments` and `_fallback_subsegments` paths are outside P5 and remain
unchanged.

## Trace stage and order manifest

Trace lists are populated only after successful validation, prosody and bracket
filter completion.  List fields retain their schema order in `trace.py`; within
each field the following order is observable.

| trace field | exact entry order | important fields |
| --- | --- | --- |
| `claim_logs` | registry claim order | owner, claim type, surface type, reason, span |
| `claim_collision_logs` | registry collision order | attempted/winner owner and spans |
| `gate_logs` | time, event, emergency, public-number builders | builder-local event/reason/metadata |
| `particle_exception_logs` | particle adapter result order | consumed marker and span |
| `prosody_logs` | base adapter logs, then extra adapter logs | generated punctuation decision and source mapping |
| `bracket_filter_logs` | final bracket filter order | pre/post-filter bracket action |
| `parser_logs` | successful `surfaces` order only | `surface_parsed`, success, `phase7_owner_parse`, surface owner/type/span/raw and reading metadata |
| `source_map_logs` | one summary | source-map counts |
| `tokenization_logs` | one summary, then tokens in source order | token type, immutability and source span |
| `shadow_logs` | one summary, then shadow units in source order | shadow type, raw and source span |
| `render_logs` | one summary, slash-alias logs, then final pieces in piece order | pre-filter text/counts; then provenance projection |
| `validation_logs` | one summary, then `validate_shadow` logs unchanged | pass state, count, ordered mismatch/consume results |

Claim reasons and parser reasons are intentionally separate: registry entries
retain owner policy reasons, while successful parser entries keep the fixed
`phase7_owner_parse` reason.  Rejected candidates produce no parser log.

## RenderPiece and provenance matrix

| provenance | render trace decision | source span contract | examples |
| --- | --- | --- | --- |
| `ORIGINAL_*` | `render_original` | original source span | Korean, space, punctuation and boundaries |
| `GENERATED_READING` | `render_generated` | owner surface or owner-local source span | numbers, units, acronyms |
| `GENERATED_PARTICLE` | `render_generated` | particle adapter source mapping | safe particle replacement |
| `GENERATED_PUNCT` | `render_generated` | `None` for prosody insertion; slash source span for sentence-final slash alias | commas and slash-to-period alias |

`render_piece_created` entries iterate the exact `pieces` list returned in
`TransformOutput`.  They therefore have the same ordering as final pieces, but
the normalized string may differ after the bracket filter.  The render summary
uses `pre_filter_text`, and bracket-filter actions live in their own trace list.
This distinction must not be hidden by a shared orchestration helper.

## Exact-equivalent extraction candidates

1. `_parser_trace_log(surface)` is a pure one-to-one projection of one already
   successful Surface.  The input domain, fixed event/decision/reason/action,
   owner/type/span/raw fields, reading metadata, exception behavior and call
   time can remain exactly identical.
2. `_render_piece_trace_log(piece)` is a pure one-to-one projection of one
   final RenderPiece.  Its only decision is the existing provenance-prefix
   check.  It preserves list order, source span, raw text, owner and provenance.

Both candidates remain private to `transform.py`; no support module or generic
trace registry is justified.  They will be called at the existing trace
assembly point, after all successful core stages, so they do not alter which
logs are visible on exceptions or fallback.

## Policy-distinct or unsafe areas kept separate

- Claim, collision and gate logs are produced by their owning subsystems and
  have different precedence and failure semantics.
- Particle, base prosody, extra prosody and bracket logs are ordered results of
  separate policies; a common append abstraction would obscure that order.
- Source-map, token, shadow, render and validation summaries have different
  metadata schemas and are not exact duplicates.
- Slash alias logs precede per-piece render logs but are not projections of the
  final pieces.
- Validation must occur before prosody and trace assembly.  Failed validation
  raises instead of returning a partial success trace.
- Pre-filter pieces and post-filter normalized text intentionally describe
  different views.  Render pieces must not be rebuilt from normalized text.
- Segment fallback and whole-input preserve are policy-bearing error recovery
  paths and are excluded from P5.

## Characterization and performance plan

Before extracting either helper, public tests must pin normalized output, exact
parser and render entry dictionaries and order, validation summary/log order,
debug serialization, generated punctuation span behavior, bracket filtering,
preserve/no-surface behavior, particle handling and the unchanged fallback
boundaries.  Existing phase tests retain their separate serialization,
precedence and regression purposes.

The fixed Golden 13 plus Batch 1 through 8 corpus contains 83 inputs.  P5 uses
five isolated samples with 20 full-corpus rounds per sample before and after
production edits.  Measurements running concurrently with pytest or binary
builds are discarded.  A reproducible median regression of at least five
percent rejects the extraction.


## Checkpoint results

- P5-A focused trace, render, provenance, particle, bracket, fallback and
  canonical tests: 198 passed. Full pre-change source suite: 6,217 passed and
  109 binary tests deselected.
- Six public characterization tests were added before production edits. They
  pin exact successful parser projection, final piece projection and ordering,
  generated punctuation spans, slash-log ordering, bracket pre/post-filter
  separation, preserve-without-Surface behavior, validation ordering and debug
  serialization.
- P5-B extracted only `_parser_trace_log` and `_render_piece_trace_log`. Both are
  pure one-item projections invoked at the original trace assembly point. No
  stage, list append, exception, validation, prosody, bracket or fallback order
  changed.
- P5-C found zero private top-level zero-load functions, zero unused imports and
  zero exact duplicate function bodies in `transform.py`, `trace.py` and
  `render.py`. No production symbol, test or file was deleted.
- Full post-change source suite: 6,223 passed and 109 binary tests deselected.
  Batch 1 through 8, Golden 13 and the empty legacy audit remain exact.
- Fixed 83-case isolated paired-before samples were 1192.27, 1182.56, 1183.13,
  1202.03 and 1197.09 microseconds per input; median/min/max
  1192.27/1182.56/1202.03. Paired-after samples were 1142.77, 1140.79,
  1126.69, 1138.58 and 1131.65; median/min/max 1138.58/1126.69/1142.77.
  The median improved by about 4.5 percent. WSL/CPU scheduling remains
  uncontrolled.
- Normal production output differences and allowed-diff changes: zero.
