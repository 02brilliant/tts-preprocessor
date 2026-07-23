# Production Refactor P6: shadow validation audit

## Scope and invariants

P6 is limited to `engine/span_engine/validation.py` and validation-specific
characterization.  Transform orchestration, trace assembly, segment fallback,
parser/render/prosody policy, owner order and comparison support are unchanged.
`ValidationResult.passed`, ValidationLog order and every field, exact exception
types/messages, and transform-level failure behavior are observable invariants.

## Call graph and inputs

`_transform_core_with_trace` renders surfaces, applies the sentence-final slash
alias and safe particle exception, computes surface-internal consumed shadow
spans, and calls `validate_shadow(pieces, shadow, consumed_particle_spans,
consumed_shadow_spans)`.  A failed result raises `RuntimeError("shadow validation
failed")` before prosody and trace assembly; the existing outer transform path
owns recovery.  Direct tests and importable diagnostics may also call
`validate_shadow`, so input errors are public behavior.

| input | validation | observable contract |
| --- | --- | --- |
| `pieces` | exact list, then every item is RenderPiece | fixed TypeError messages |
| `shadow` | exact list, then every item is ShadowUnit | fixed TypeError messages |
| consumed particle spans | `None` becomes empty set; otherwise exact set of two-int tuples | distinct argument name in errors |
| consumed surface spans | same shape validation, independent set | distinct argument name in errors |
| piece index | `(start, end, provenance)` -> pieces in input order; unmapped pieces omitted | drives duplicate and exact-match behavior |

## Decision-precedence matrix

Duplicate original-piece detection runs before all shadow-unit decisions.  Its
logs are sorted by duplicate index key and precede unit logs.  For each shadow
unit, exactly the first matching row below wins.

| priority | condition | result/reason | important fields |
| --- | --- | --- | --- |
| 1 | exact span and expected provenance indexed | pass `matched_original_piece`, or fail `original_text_mismatch` | expected raw, actual piece text, unit span |
| 2 | unit span consumed by particle exception | pass `particle_exception_consumed` | actual and metadata marker `PARTICLE_EXCEPTION_CONSUMED` |
| 3 | unit span consumed inside a Surface | pass `surface_internal_consumed` | actual and metadata marker `SURFACE_INTERNAL_CONSUMED` |
| 4 | any piece has the same source span | fail `provenance_mismatch` | first piece text and expected/actual provenance metadata |
| 5 | any piece has expected provenance and raw text elsewhere | fail `source_span_mismatch` | first matching piece actual span list or None |
| 6 | none of the above | fail `missing_original_piece` | actual None |

An exact indexed piece wins over both consumed markers. Particle consumption
wins over surface-internal consumption. Same-span provenance mismatch wins over
same-text source mismatch. List order selects the first piece in the latter two
searches. `ValidationResult.passed` remains `all(log.passed for log in logs)`,
so an empty shadow and no duplicate original pieces passes.

Duplicate detection distinguishes generated and original provenance. Duplicate
keys are logged as failures only when provenance starts with `ORIGINAL_`;
generated duplicates remain available to later mismatch checks but do not
independently fail validation. The existing duplicate log span is
`pieces[0].source_span`, while its metadata records the duplicated key. Though
unusual, this is observable and must remain unchanged.

## Exact input-error contract

Validation order is pieces-list, shadow-list, default consumed sets, particle
set and tuples, surface set and tuples, piece items, then shadow items. The
messages are:

- `pieces must be list[RenderPiece]`
- `shadow must be list[ShadowUnit]`
- `<argument> must be set or None`
- `<argument> must contain (int, int) tuples`
- `pieces must contain RenderPiece`
- `shadow must contain ShadowUnit`

No helper may reorder these checks or normalize other iterables.

## Exact-equivalent extraction candidates

1. `_validate_consumed_spans(name, spans)` can contain the two identical set and
   tuple-shape checks. Defaults remain in `validate_shadow`, and calls remain in
   particle-then-surface order. The argument name formats the same messages.
2. `_index_pieces_by_span_and_provenance(pieces)` can build the existing
   `defaultdict(list)` index in input order while continuing to omit pieces with
   no source span. It has no decisions beyond the current `_span_key` result.

Both are private pure helpers in `validation.py`. Mismatch-log construction is
not extracted: each branch has distinct reason, fields, metadata and precedence,
so a parameterized log factory would obscure policy and increase arguments.

## Policy-distinct and unsafe areas kept separate

- Particle-consumed and Surface-internal-consumed logs intentionally use
  different markers and precedence.
- Same-span and same-text searches have different mismatch semantics and first
  match behavior.
- Matching original text versus original text mismatch share lookup but differ
  in pass state and cannot be combined with later preserve exceptions.
- Duplicate detection and unit matching use the same index but have different
  ordering and output rules.
- The early `continue` chain is the validation policy; it remains explicit.
- Transform-level raising and fallback are outside P6.

## Characterization and performance plan

Before extraction, public tests must pin all precedence collisions, duplicate
ordering and metadata, generated-duplicate behavior, both consumed markers,
same-span versus same-text selection, invalid input type/message order, final
passed calculation, and one transform-level successful validation trace.

Golden 13 plus Batch 1 through 8 provide the fixed 83-input corpus. P6 uses five
isolated samples with 20 corpus rounds before and after production edits. Runs
concurrent with pytest or binary builds are discarded. A reproducible median
regression of at least five percent rejects the extraction.


## Checkpoint results

- P6-A focused validation, provenance, fallback, trace and canonical checkpoint:
  173 passed. Full no-production-change source suite: 6,223 passed and 109
  binary tests deselected.
- Twelve public characterization tests were added before production edits. They
  pin exact argument-specific errors, input-check order, all consumed/mismatch
  precedence collisions, duplicate ordering/span/metadata, generated duplicate
  behavior and transform-level surface-internal markers.
- P6-B extracted only `_validate_consumed_spans` and
  `_index_pieces_by_span_and_provenance`. Defaults and particle-before-surface
  calls remain in `validate_shadow`; the index preserves input order and omits
  only unmapped pieces exactly as before. The early-continue decision chain and
  every ValidationLog constructor remain unchanged.
- P6-C found zero private top-level zero-load functions, zero unused imports and
  zero exact duplicate function bodies in `validation.py`. Validation reasons
  remain consumed by owning tests and debug traces. No production symbol, test
  or file was deleted.
- Full post-change source suite: 6,235 passed and 109 binary tests deselected.
  Explicit PyInstaller rebuild and smoke passed. Rebuilt-binary selected set:
  109 passed and 6,235 source tests deselected.
- Golden 13 plus Batch 1 through 8 (70): all 83 source, rebuilt-binary, API and
  expected outputs were directly compared and byte-exact. Archive production
  module isolation passed. The retained comparison facade/CLI and production
  isolation smoke checkpoint passed 57 tests.
- Fixed 83-case isolated P6 paired-before samples were 1146.00, 1145.16,
  1155.59, 1145.72 and 1147.04 microseconds per input; median/min/max
  1146.00/1145.16/1155.59. Paired-after samples were 1196.11, 1179.93,
  1187.83, 1185.64 and 1241.52; median/min/max 1187.83/1179.93/1241.52.
  The median increased by about 3.7 percent, below the five-percent stop
  threshold. WSL/CPU scheduling remains uncontrolled.
- Normal production output differences, Batch fixture state changes and new
  allowed diffs: zero. The legacy audit remains exact `[]`.
