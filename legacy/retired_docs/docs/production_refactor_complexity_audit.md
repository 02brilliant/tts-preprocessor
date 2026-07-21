# Production refactor complexity audit

Status: Checkpoints A, B, and C complete (2026-07-14)

This audit covers only the production graph rooted at `engine.main.transform`.
The explicitly retained comparison graph documented in
`docs/legacy_comparison_graph_audit.md` is not a production refactor target.

## Method

The review combined:

- AST function LOC and structural-node counts;
- static imports and literal dynamic imports;
- repository-wide symbol and attribute references;
- package exports, `__getattr__`, PyInstaller exclusions, scripts, workflows,
  documentation, and import-boundary tests;
- owner, trace, fallback, Golden, and Batch 1 through 8 regression coverage.

An implementation is an extraction candidate only when its input domain,
source-span semantics, full-consume boundary, precedence, and failure result are
the same. Similar-looking owner-local predicates remain separate when any of
those contracts differ.

## Production call graph

```text
engine.main.transform
  -> engine.span_engine.production_adapter.transform_for_production
     -> engine.span_engine.transform.transform
        -> transform_with_trace
           -> language gate / core transform
              -> tokenize + shadow
              -> claim_scanner.claim_surfaces
              -> parser.parse_candidates
              -> render_tokens_with_surfaces
              -> validation.validate_shadow
              -> base prosody + extra prosody
              -> bracket filter + trace assembly
           -> paragraph split
```

`claim_scanner` dispatches the production owner scanners in policy order.
`parser` dispatches the corresponding owner parsers. Neither module may be
converted into a generic registry in this batch because call order, preserve
claims, and owner-specific failure semantics are observable policy.

## Complexity manifest

The structural count below is an audit heuristic: calls, branches, loops,
`try`, `match`, and boolean-expression nodes inside the function. It is not a
cyclomatic-complexity score.

| File | File LOC | Largest function | Function LOC / structural nodes | Classification and coverage |
| --- | ---: | --- | ---: | --- |
| `claim_scanner.py` | 783 | `_is_supported_number` | 104 / 91 | large policy gate; owner and numeric boundary tests; unsafe to split in P1 |
| `claim_scanner.py` | 783 | `claim_surfaces` | 72 / 154 | explicit policy order; stage/precedence tests; keep ordered |
| `parser.py` | 265 | `_parse_candidate` | 98 / 81 | owner dispatch with distinct parse failures; keep ordered |
| `transform.py` | 815 | `_transform_core_with_trace` | 182 / 66 | orchestration plus trace assembly; broad extraction deferred |
| `transform.py` | 815 | `_transform_hangul_with_segment_fallback` | 83 / 29 | segment-local safety contract; fallback tests; unsafe to generalize |
| `transform.py` | 815 | `_apply_sentence_final_slash_punctuation_alias` | 82 / 30 | owner/source-map-sensitive; keep separate |
| `production_adapter.py` | 96 | `transform_for_production` | 26 / 9 | public facade/fallback shape; no extraction selected |
| `render.py` | 116 | `render_tokens_with_surfaces` | 40 / 33 | ordered source coverage; validation tests; keep cohesive |
| `trace.py` | 178 | `_json_safe` | 24 / 37 | recursive serialization boundary; keep cohesive |
| `validation.py` | 219 | `validate_shadow` | 187 / 80 | invariant checker; large but policy-sensitive |
| `prosody.py` | 482 | `apply_prosody_comma_adapter` | 79 / 47 | base insert-only policy; prosody boundary tests |
| `prosody_extra.py` | 628 | `apply_extra_prosody_comma_adapter` | 51 / 29 | extra insert-only policy; source-mapped trace tests |
| `date_time.py` | 1076 | `scan_date_candidates` | 122 / 64 | date/time owner matrix; out of P1 extraction scope |
| `units.py` | 817 | `_scan_unit_candidates` | 54 / 30 | unit registry/boundary policy; keep owner-local |
| `range.py` | 1717 | `scan_numeric_delimited_hyphen_range_candidates` | 135 / 74 | multiple restricted owners; highest later refactor priority |
| `currency.py` | 986 | `_scan_suffix_currency` | 72 / 44 | sign/spacing/atomic preserve policy; keep owner-local |
| `counter.py` | 457 | `scan_counter_candidates` | 71 / 38 | counter-specific leading-zero and tail policy |
| `large_unit.py` | 789 | `_parse_mixed_large_unit_at` | 85 / 62 | structured number grammar; later isolated refactor candidate |

## Exact-equivalent extraction candidates

### P1-A: excluded-range overlap in `claim_scanner`

`claim_scanner._span_overlaps_excluded_range` has an AST-identical body and the
same `SourceSpan`/`BracketRange` contract as the existing production helper
`span_guards.span_overlaps_excluded_ranges`. The scanner can import the shared
helper and remove its private duplicate without changing call sites, range
semantics, or owner order.

Characterization coverage must include square-bracket and incomplete-bracket
claims, protected literals, dictionary/acronym claims, number fallback, and
large-unit candidates. The Batch fixtures and production isolation tests are
the final output boundary.

### P1-B: shared prosody position utilities

`prosody.py` and `prosody_extra.py` contain AST-identical pure helpers for:

- merging half-open integer ranges;
- finding the previous visible character;
- finding the start of the preceding whitespace run;
- finding the next non-space character;
- finding the render piece containing an insertion position.

These helpers have the same argument and return contracts and do not encode a
base- versus extra-prosody rule. They may move to one internal support module.
Candidate selection, sentence budgets, blocked-range construction, owner names,
generated-comma provenance, and trace reasons must remain in their respective
policy modules.

Characterization coverage must directly fix the five pure helper boundaries and
retain all existing base/extra prosody positive, negative, protected-surface,
source-span, and trace tests.

## Similar but policy-distinct: keep separate

- Counter, unit, currency, range, duration, and date/time boundary functions
  often inspect the same neighboring characters, but accept different Hangul
  tails, spacing, signs, and atomic-preserve behavior.
- Numeric consumers with similar loops differ in comma, decimal, sign, or
  leading-zero acceptance. They are not interchangeable.
- `claim_scanner._is_supported_number` and owner-local `_valid_boundary`
  predicates sit at different precedence layers and must not be merged.
- Base and extra prosody safety-context builders consume different policy
  ranges and return different context models. Only their pure position helpers
  are equivalent.
- `transform` recovery and `production_adapter` payload recovery share error
  metadata concepts but return different public types. Combining them would
  obscure exception and debug-payload contracts.

## Large or complex but unsafe in P1

The first later candidates are `range.py`, `_is_supported_number`, parser owner
dispatch, core trace assembly, shadow validation, and segment recovery. Each
requires a dedicated characterization batch because it combines several policy
owners or observable provenance. P1 must not reduce their branch count by
changing dispatch tables, fallback order, or trace construction.

## Private dead-code manifest

Repository-wide AST name/attribute references plus textual searches found three
private definitions with zero inbound reference:

| Symbol | File | Dynamic/export/package evidence | Checkpoint C decision |
| --- | --- | --- | --- |
| `_digit_reading` | `currency.py` | no call, export, string reference, docs, script, workflow, or test | removed leaf-first |
| `_has_time_prefix` | `date_time.py` | `_time_prefix` is live; boolean wrapper has no caller or export | removed leaf-first |
| `_consume_integer_block` | `range.py` | no call, export, string reference, docs, script, workflow, or test | removed leaf-first |

No production or comparison module file is a proven deletion candidate. Public
or importable modules remain even when repository-local callers are absent.

## Checkpoint plan and performance risk

1. Replace only the scanner overlap duplicate; risk is low and the helper body
   is already production-used by decimal and middle-dot owners.
2. Extract only the five pure prosody position utilities; risk is low-to-medium
   because imports change, while policy selection remains untouched.
3. Remove the three zero-reference private leaves after both extraction
   checkpoints pass.

All steps require exact Golden and Batch parity, trace/fallback coverage,
production import isolation, a rebuilt binary, and the fixed 83-case performance
corpus. Any repeatable median regression of at least five percent blocks the
corresponding refactor.

## Completed P1 result

- `claim_scanner.py` now imports the existing shared excluded-range predicate;
  its duplicate was removed without changing scanner calls or order. The file
  changed from 783 LOC / 25 functions to 775 LOC / 24 functions.
- Five duplicated prosody helpers moved to `prosody_support.py`. Private aliases
  in both policy modules preserve their internal attribute names. The two
  modules changed from 1,110 LOC / 60 functions combined to 1,027 LOC / 50
  functions, plus one 61-LOC / 5-function shared module: 22 net LOC and five
  duplicate definitions removed.
- The three zero-reference private leaves were removed in currency, date/time,
  then range order. Those files changed from 986/1076/1717 LOC to
  980/1072/1710 LOC. A repeated repository-wide AST reference audit reports no
  remaining private top-level function with zero name or attribute reference.
- No owner dispatch, claim order, candidate selection, parse/render behavior,
  trace reason, source span, fallback path, public API, or comparison module was
  changed.

## Validation

- Checkpoint A documentation baseline: Batch/audit/isolation 98 passed; full
  source 6,161 passed and 109 binary tests deselected.
- P1-A shared overlap checkpoint: 209 targeted tests passed.
- P1-B characterization and prosody checkpoint: 149 then 211 targeted tests
  passed.
- Leaf deletion checkpoints: currency 127, date/time 152, and range 162 tests
  passed.
- Final source suite: 6,173 passed and 109 deselected.
- Explicit PyInstaller rebuild and smoke: passed.
- Final rebuilt-binary selected set: 109 passed and 6,173 deselected, including
  Golden 13, Batch 1 through 8, API parity, and archive isolation.
- Fixed 83-case performance samples were 1210.91, 1197.05, 1203.91, 1191.79,
  and 1185.18 microseconds per input. Median/min/max were
  1197.05/1185.18/1210.91. The median is about 0.17 percent above the prior
  1195.08 reference and well below the five-percent stop threshold; WSL and CPU
  scheduling remain uncontrolled.
- Production output differences: zero. No allowed-diff fixture was added or
  changed.

## Production P2 follow-up

Production Refactor P2 audited the complete `range.py` owner graph and kept its scanner state machines and owner-local boundary predicates separate. Two exact-equivalent mechanisms were extracted inside the same module: numeric sign-prefix application and Hangul tail-spacing with caller-supplied owner tuples. The owner tuples, scanner order, candidate metadata, reason strings, spans, parser dispatch, and fallback behavior did not change.

`range.py` changed from 1,710 to 1,694 LOC. Twenty-one characterization cases were added; two unused imports were removed after AST reachability checks. Final private zero-load and exact duplicate function-body counts are zero. Full validation was 6,198 source tests and 109 rebuilt-binary tests, with all 83 canonical source/binary/API outputs byte-exact. Same-session performance median moved from 1291.99 to 1217.34 microseconds per input. Detailed evidence is in `docs/production_refactor_p2_range_audit.md`.

## Production P3 follow-up

Production Refactor P3 audited the final generic number gate and extracted only two contiguous exact-equivalent decisions: spaced deferral to earlier range/unit owners and blocking an attached registered-unit prefix followed by slash. `CLAIM_ORDER_DOC`, scanner order, registry overlap, candidate metadata, spans, parser dispatch, preserve, and fallback behavior did not change. Fourteen public output/trace characterization cases were added. `_is_supported_number` changed from 104 LOC / 53 structural nodes to 97 LOC / 47 structural nodes; final scanner private zero-load, real unused-import, and exact duplicate-body counts are zero. Full validation was 6,212 source tests and 109 rebuilt-binary tests, with production output diff zero. Same-session performance median moved from 1317.81 to 1339.89 microseconds per input, about 1.7 percent and below the five-percent stop threshold. Detailed evidence is in `docs/production_refactor_p3_number_gate_audit.md`.


## Production P4 follow-up

Production Refactor P4 audited the complete scanner-owner to parser-dispatch graph and retained the explicit dispatch chain. One exact-equivalent post-parse mechanism was extracted: core-span Surface assembly for K-Hangul, acronym-Hangul and large-unit custom RenderPiece owners. Owner parsers, `None` and exception behavior, multiplier full-span semantics, parser ordering, provenance and fallback did not change. Seven characterization tests were added and two exact duplicate owner/parser-trace tests were removed while their precedence owning tests remain. Final parser private zero-load, unused-import and exact duplicate-body counts are zero; no stale dispatch was proven. Full validation was 6,217 source tests and 109 rebuilt-binary tests, with all 83 canonical source/binary/API outputs byte-exact. Isolated same-session performance median moved from 1322.84 to 1221.06 microseconds per input. Detailed evidence is in `docs/production_refactor_p4_parser_dispatch_audit.md`.

### P5 result: transform trace/render provenance

Production Refactor P5 audited the complete successful core trace assembly and
kept its observable stage and list ordering explicit. Two exact-equivalent
one-item projections were extracted for successful Surface parser logs and
final RenderPiece render logs. Six characterization tests pin log fields and
order, provenance and spans, generated punctuation, slash alias ordering,
bracket pre/post-filter separation, preserve behavior, validation order and
debug serialization. Segment fallback, validation, prosody and orchestration
were unchanged. Final P5 source validation was 6,223 passed with 109 binary
tests deselected; production output diff was zero. Same-session isolated
performance median moved from 1192.27 to 1138.58 microseconds per input.
Detailed evidence is in `docs/production_refactor_p5_transform_trace_audit.md`.

### P6 result: shadow validation

Production Refactor P6 audited the complete shadow-validation decision chain
and kept duplicate ordering and every early-continue mismatch priority explicit.
Two exact-equivalent helpers were extracted: argument-specific consumed-span set
validation and the ordered RenderPiece span/provenance index. Twelve public
characterization tests pin exact errors, precedence collisions, duplicate
metadata, generated duplicates and transform-level consumed markers. Final P6
source validation was 6,235 passed with 109 binary tests deselected; the rebuilt
binary set was 109 passed and all 83 source/binary/API/expected outputs were
byte-exact. Production output diff was zero. Same-session isolated performance
median moved from 1146.00 to 1187.83 microseconds per input, about 3.7 percent
and below the five-percent stop threshold. Detailed evidence is in
`docs/production_refactor_p6_validation_audit.md`.

### P7 result: segment fallback and recovery orchestration

Production Refactor P7 audited the complete public recovery chain and retained
its asymmetric whole-input eligibility, segment-first retry, whitespace/nonspace
subsegment narrowing, source-span offset and post-recovery paragraph timing. Two
exact-equivalent projections were extracted: terminal failed-subsegment result
construction and final segment-fallback TraceLogEntry construction. Eleven
characterization tests pin failure placement and order, exact pieces and trace
serialization, protected inputs, generated punctuation, whole preserve,
exception identity, boundaries and metadata copying. The main orchestrator
changed from 83 LOC / 29 structural nodes to 56 / 22. Final P7 source validation
was 6,246 passed with 109 binary tests deselected; the rebuilt binary set was 109
passed and all 83 source/binary/API/expected outputs were byte-exact. Production
output diff was zero. Same-session isolated performance median moved from
1308.61 to 1196.71 microseconds per input. Detailed evidence is in
`docs/production_refactor_p7_segment_fallback_audit.md`.


### P8 result: final graph and repository hygiene

Production Refactor P8 reconciles the final production and retained comparison
graphs rather than changing transform behavior. The final AST/text/export audit
found no zero-reach production or comparison module and no private top-level
zero-reference function. Four unused imported names were removed from the
phone owner and comparison rollout utility. Exact duplicate test bodies were
consolidated leaf-first while keeping the dedicated public API, owning policy,
trace, comparison-boundary, Golden and Batch contracts. No production owner,
parser, validation, fallback or comparison root was changed. Detailed final
evidence and completion criteria are in
`docs/production_refactor_p8_final_audit.md` and
`docs/production_refactor_final_report.md`.
