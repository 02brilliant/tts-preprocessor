# Production Refactor P7: segment fallback and recovery orchestration audit

## Scope and invariants

P7 audits only the production recovery path in
`engine/span_engine/transform.py`. It does not change the successful core path,
claim or parser order, validation, prosody, paragraph policy, the production
adapter, or the retained comparison graph. Normalized output, RenderPiece order
and provenance, absolute source spans, fallback trace fields and serialization,
public API behavior, and binary behavior are byte-exact invariants.

The governing safety rule is asymmetric: no-Hangul global bypass may preserve
the whole input, while any input containing a Hangul syllable must recover at
the narrowest safe segment and must not return the whole raw input merely
because one internal operation failed. A whole-input absolute-preserve reason
is the only Hangul-capable preserve exception.

## Production recovery call graph

```text
engine.main.transform
  -> production_adapter.transform_for_production
     -> span_engine.transform.transform
        -> transform_with_trace
           -> _transform_with_language_gate_trace
              -> normal core path
           !! exception
           -> recover_transform_output
              -> no Hangul
                 -> _whole_input_preserve_output(global_no_hangul_bypass)
              -> Hangul present
                 -> _transform_hangul_with_segment_fallback
                    -> _fallback_segments
                    -> _transform_fallback_segment for each segment
                    !! segment exception
                    -> _fallback_subsegments
                    -> _transform_fallback_segment for each subsegment
                    !! subsegment exception
                    -> one ORIGINAL_BOUNDARY preserve piece
           -> _apply_paragraph_split_to_output
```

`transform` and `production_adapter` retain outer recovery guards because their
public result types differ. `production_adapter` adds payload-level fallback
metadata and is outside P7.

`_try_core_trace_for_whole_input` is not exception recovery. It is a fidelity
probe used after language-gate processing: it returns a real core output only
when the core succeeds and produces exactly the already selected normalized
text. Core failure or text mismatch returns `None`, leaving the caller's
language-gate result unchanged. Its deliberate local exception suppression must
not be merged with `recover_transform_output`.

## Function manifest

Structural counts are the same audit heuristic used in the parent complexity
audit: calls, branches, loops, try nodes, boolean expressions and
comprehensions.

| function | LOC / structural | caller and result | observable contract |
| --- | ---: | --- | --- |
| `recover_transform_output` | 9 / 5 | transform and production adapter -> TransformOutput | Hangul test chooses segment recovery versus no-Hangul whole preserve |
| `_apply_paragraph_split_to_output` | 9 / 4 | `transform_with_trace` final step | may change normalized newlines; leaves RenderPieces and trace unchanged |
| `may_whole_input_preserve` | 10 / 3 | whole preserve guard, direct policy test | absolute reason wins; other allowlisted reasons require no Hangul |
| `_try_core_trace_for_whole_input` | 10 / 3 | language gate only -> output or None | exact normalized-text match; core exception becomes None |
| `_whole_input_preserve_output` | 32 / 12 | no-Hangul recovery; private absolute contract | disallowed reason re-raises the same exception object; allowed path emits one piece and one log |
| `_transform_hangul_with_segment_fallback` | 83 / 29 | Hangul recovery -> TransformOutput | segment-first retry, subsegment narrowing, ordered accumulation and one fallback trace |
| `_transform_fallback_segment` | 13 / 7 | recovery orchestrator -> text and pieces | empty, whitespace and core-transform cases remain distinct |
| `_offset_render_piece` | 14 / 4 | successful fallback segment projection | absolute span offset, `None` unchanged, owner/provenance/text copied, metadata shallow-copied |
| `_fallback_segments` | 10 / 10 | recovery orchestrator -> ordered spans | split after sentence punctuation plus whitespace and on newline runs; delimiter whitespace belongs to preceding segment |
| `_fallback_subsegments` | 7 / 4 | failed segment -> ordered spans | exhaustive alternating `\s+` / `\S+` spans with absolute offsets |
| `_preserve_render_piece` | 8 / 2 | whole and local preserve | ORIGINAL_BOUNDARY, exact source text and absolute span, no owner |

## Whole-input preserve eligibility matrix

| reason | no Hangul | Hangul present | result |
| --- | --- | --- | --- |
| `global_no_hangul_bypass` | allowed | blocked | one exact ORIGINAL_BOUNDARY piece and one `whole_input_preserve_allowed` log, or same exception re-raised |
| `non_korean_prose_global_bypass` | allowed | blocked | same eligibility contract; no current recovery caller |
| `code_like_global_bypass` | allowed | blocked | same eligibility contract; no current recovery caller |
| `whole_input_absolute_preserve` | allowed | allowed | explicit whole-input absolute-preserve contract |
| unknown reason | blocked | blocked | re-raise the identical exception object |

The allowed log is stage `fallback`, event
`whole_input_preserve_allowed`, decision `preserve`, action
`preserve_original`, and the supplied reason. Its metadata order and values are
`status=whole_input_preserve`, outer exception type, and outer exception text.
The empty string still produces a zero-length preserve piece and zero-length
trace span.

## Segment and subsegment decision matrix

1. `_fallback_segments` always returns at least one half-open source span. A
   sentence delimiter match includes the trailing whitespace/newline in the
   preceding segment.
2. Each whole segment is attempted once with `_transform_fallback_segment`.
3. Empty segments return no text/pieces; whitespace-only segments are preserved
   without calling core; other segments call the successful core path.
4. A whole-segment exception triggers `_fallback_subsegments` over only that
   segment. No already successful segment is retried.
5. Each whitespace subsegment is preserved and recorded as
   `preserved_boundary`; each successful nonspace subsegment is recorded as
   `recovered`.
6. A failed nonspace subsegment is the terminal narrow boundary: its exact raw
   bytes become one ORIGINAL_BOUNDARY piece and its exception type/message are
   appended to `segment_failures`. It is not added to `segment_recoveries`.
7. Text, pieces, failures and recoveries remain in source traversal order.

The final trace contains exactly one entry:

- stage/event: `fallback` /
  `blocked_whole_input_fallback_for_hangul_input`;
- decision/reason/action: `blocked` /
  `hangul_input_whole_fallback_prohibited` / `segment_fallback`;
- top-level span/raw: the complete original input;
- metadata: segment status, outer exception type and message, whole-input
  prohibition fields, then ordered failure and recovery records.

Successful segment-local parser/render/validation traces are intentionally not
merged into the final recovery trace. Only their RenderPieces are retained.

## Span, provenance and paragraph matrix

| recovery result | text/provenance | source-span behavior | metadata |
| --- | --- | --- | --- |
| successful generated reading | existing text/provenance/owner | local non-None span offset by segment start | shallow dict copy |
| successful original piece | existing original provenance | local span offset by segment start | shallow dict copy |
| generated punctuation | GENERATED_PUNCT | `None` remains `None`; mapped slash punctuation retains offset span | shallow dict copy |
| whitespace fallback | ORIGINAL_BOUNDARY | exact absolute subsegment span | empty |
| failed nonspace fallback | ORIGINAL_BOUNDARY | exact absolute failed span | empty |
| whole-input preserve | ORIGINAL_BOUNDARY | `(0, len(text))` | empty |

After recovery, paragraph splitting operates only on `normalized_text`. It does
not rewrite RenderPieces or fallback trace spans. Thus inserted paragraph
newlines may make the final string differ from the simple concatenation of
piece text while source mapping remains tied to the original input. This is an
existing public contract and is not normalized in P7.

## Exception contract

- The exception that first caused public recovery supplies
  `fallback_reason` and `fallback_error_message`.
- Each terminal failed subsegment records its own exception type and message.
- An ineligible `_whole_input_preserve_output` raises the identical exception
  object, not a wrapper.
- `_transform_hangul_with_segment_fallback` catches only at the whole-segment
  and subsegment retry boundaries. No new broad catch or silent default is
  permitted.
- Exceptions from trace/result construction remain visible to the existing
  outer public guard; P7 does not add a third recovery layer.

## Exact-equivalent extraction candidates

1. `_preserved_failed_segment(text, start, end, exc)` can project the terminal
   failed subsegment into its exact raw text, one ORIGINAL_BOUNDARY piece, and
   the existing failure record. It is a pure result builder called only from
   the current inner exception branch.
2. `_segment_fallback_trace_log(text, exc, failures, recoveries)` can project
   completed recovery state into the existing single TraceLogEntry. It is
   called at the same post-loop point and preserves field and metadata order.

These candidates remove construction detail from the 83-line orchestrator
without changing retry control flow. Both stay private in `transform.py`; a
generic retry framework or support module is not justified.

## Policy-distinct and unsafe areas kept separate

- no-Hangul whole preserve and Hangul segment recovery have opposite eligibility
  and must not share a generic fallback result factory;
- whole-segment retry and subsegment retry have different failure consequences;
- whitespace preservation and failed-token preservation have different trace
  status and exception semantics;
- `_try_core_trace_for_whole_input` is a language-gate fidelity check, not a
  recovery retry;
- paragraph splitting happens after recovery and must not be folded into piece
  accumulation;
- successful inner trace logs are deliberately discarded; merging them would
  change debug behavior;
- protected/code-like/bracket behavior remains owned by the language gate and
  core owner graph, not by segment recovery;
- `_offset_render_piece`, `_fallback_segments` and `_fallback_subsegments` are
  already cohesive pure helpers and need no further abstraction.

## Characterization and performance plan

Before either extraction, public tests must pin leading, middle, trailing and
consecutive failed subsegments; sentence and newline segment retry; successful
owners around failures; exact RenderPiece order, metadata and absolute spans;
`None` generated-punctuation spans; whitespace recovery records; outer and
inner exception messages; fallback debug serialization; no-Hangul and absolute
whole preserve; ineligible same-exception rethrow; and paragraph-split timing.

P7 uses the fixed Golden 13 plus Batch 1 through 8 corpus (83 inputs), with five
isolated samples of 20 full-corpus rounds before and after production edits.
Measurements concurrent with pytest, binary builds or parity subprocesses are
discarded. A reproducible median regression of at least five percent rejects
the extraction.


## Checkpoint results

- P7-A focused fallback, language-gate, protected-boundary, adapter, provenance
  and canonical checkpoint: 363 passed. Full no-production-change source suite:
  6,235 passed and 109 binary tests deselected.
- Eleven public characterization tests were added before production edits. They
  pin leading, middle, trailing and consecutive terminal failures; exact piece
  and serialized fallback-log projection; sentence retry and generated comma
  `None` span; paragraph-split timing; protected JSON/bracket/backtick behavior;
  no-Hangul and absolute whole preserve; same-exception rethrow; segment spans;
  and shallow metadata copying during piece offset.
- P7-B extracted only `_preserved_failed_segment` and
  `_segment_fallback_trace_log`. Both are pure projections invoked inside the
  existing terminal exception branch or at the existing post-loop trace point.
  Retry count, call order, catch boundaries and accumulation order did not
  change. First-candidate validation passed 265 tests; the complete second
  checkpoint passed 374 tests.
- `_transform_hangul_with_segment_fallback` changed from 83 LOC / 29 structural
  nodes to 56 LOC / 22 structural nodes. The extracted failure projection is
  14 LOC / 3 nodes and the trace projection is 28 LOC / 6 nodes.
- P7-C found zero private top-level zero-load functions, zero unused imports and
  zero exact duplicate function bodies in `transform.py`. Apparent identical
  parameterized test bodies retain different case matrices and fallback/gate
  contracts, so no production symbol, test or file was deleted.
- Full post-change source suite: 6,246 passed and 109 binary tests deselected.
  Explicit PyInstaller rebuild and smoke passed. Rebuilt-binary selected set:
  109 passed and 6,246 source tests deselected.
- Golden 13 plus Batch 1 through 8 (70): all 83 source, rebuilt-binary, API and
  expected outputs were directly compared and byte-exact. Archive production
  isolation passed. The retained comparison facade/CLI and production-isolation
  smoke checkpoint passed 57 tests.
- Fixed 83-case isolated paired-before samples were 1248.58, 1314.35, 1297.63,
  1354.33 and 1308.61 microseconds per input; median/min/max
  1308.61/1248.58/1354.33. Paired-after samples were 1201.73, 1190.72,
  1193.55, 1216.36 and 1196.71; median/min/max 1196.71/1190.72/1216.36.
  The median improved by about 8.6 percent. WSL/CPU scheduling remains
  uncontrolled.
- Normal production output differences, Batch fixture state changes and new
  allowed diffs: zero. The legacy audit remains exact `[]`.
