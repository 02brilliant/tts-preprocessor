# Production Refactor P8 final graph audit

Status: Checkpoints A, B and C complete (2026-07-15)

## Scope and invariants

P8 is the closing audit for Policy Alignment Batches 1 through 8 and Production
Refactor P1 through P7. It permits no policy, normal-output, owner-order,
parser, validation, recovery, trace, provenance, source-span, public API, or
binary CLI change. The comparison decision remains **retain and isolate**.

The audit combines AST imports and definitions, literal dynamic imports,
package exports, `__all__`, lazy imports, direct monkeypatch targets,
PyInstaller exclusions, scripts, workflows, documentation, and executable
tests. A repository-local reference count of zero is never sufficient to
delete an importable module.

## Final graph roots

```text
production source/API/binary
  engine.main
    -> engine.span_engine.production_adapter
       -> engine.span_engine.transform
          -> language gate, tokenizer/source map/shadow
          -> claim_scanner -> owner scanners
          -> parser -> render -> particle exception
          -> validation -> prosody -> bracket filter
          -> segment-local recovery -> paragraph split
  engine.api_interface / api.server / api.binary_runtime
    -> engine.main or packaged binary entrypoint

comparison developer graph
  engine.legacy_compare
    -> lazy legacy baseline
       -> engine.pipeline -> engine.rules -> engine.gates/engine.parsers
       -> engine.prosody.comma -> engine.pipeline.surfaces
       -> engine.prosody.paragraph
    -> engine.span_engine.compare -> production adapter/debug trace
  engine.span_engine.compare_cli -> engine.span_engine.compare
  engine.span_engine.rollout_gate -> engine.span_engine.compare
```

Importing the production span package eagerly exposes its documented model and
owner utilities, so those exports are compatibility surfaces even when a
particular function is not called by `transform` directly. Comparison imports
production reporting/transform modules, but production never imports the
comparison-only graph.

## Module disposition manifest

| Module/file family | Inbound/outbound and dynamic/package/build evidence | Classification | P8 disposition and deletion risk |
| --- | --- | --- | --- |
| `engine.main`, `engine.api_interface`, `api.server`, `api.binary_runtime`, `bin/build_binary_entrypoint.py` | official source/API/binary facades; runtime dynamic import of `engine.main`; deployment docs and tests | production/public | retain; external and binary contract |
| `engine.span_engine.production_adapter`, `transform`, `trace`, `render`, `validation`, `models` | normal transform, debug, API and fallback graph; package exports and direct tests | production/public or package-public | retain; observable output, exception, trace and model contracts |
| `claim_scanner`, `parser`, `claim_registry`, source-map/tokenizer/shadow/bracket/language helpers | direct transform graph and package exports | production | retain; order and preserve/fallback semantics are policy |
| numeric/date/time/range/unit/counter/currency/phone and other owner modules under `engine.span_engine` | scanner/parser imports, direct package exports and owning policy/trace tests | production | retain; owner-local boundary semantics |
| `engine.span_engine.prosody`, `prosody_extra`, `prosody_support` | production post-render graph and source-mapped tests | production | retain; generated punctuation provenance is observable |
| `engine.prosody.paragraph` | production post-recovery and comparison facade | production + comparison shared | retain independently of legacy comma |
| `engine.legacy_compare` | documented `__all__`, API rejection guidance, direct support tests, lazy baseline imports | supported developer facade | retain; retirement requires product decision |
| `engine.span_engine.compare` | facade/report/CLI/gate tests; literal optional import of absent `engine.pipeline.core`; explicit `__all__` | comparison implementation API | retain; dynamic fallback behavior is tested |
| `engine.span_engine.compare_cli` | direct programmatic tests; no console script, `__main__`, workflow or deployment invocation | importable compatibility utility | retain conservatively; not a shell CLI |
| `engine.span_engine.rollout_gate` | direct report/artifact tests; no production/deployment caller | importable compatibility utility | retain root; remove only proven unused imports |
| `engine.pipeline`, `engine.rules`, `engine.gates`, `engine.parsers`, `engine.prosody.comma`, `engine.dictionary`, legacy tokenizer | transitively loaded by `engine.legacy_compare.transform_for_comparison` | comparison-only implementation | retain while facade is supported; no module deletion |
| `engine.prosody.__init__` | package initialization only; no lazy comparison export remains | package compatibility surface | retain empty package module |
| `tts_preprocessor.spec` comparison exclusions | archive defense in depth; isolation tests | build boundary | retain even for dynamically unreachable legacy names |
| Batch 1-8 fixtures and owning tests | 70 exact canonical decisions; applied transitions only in Batch 1 and 4 | canonical regression contract | retain without consolidation |
| Golden fixture | 13 exact public outputs | canonical regression contract | retain |
| legacy audit fixture | exact `[]`; empty-state test and direct equality helper | completed structural audit | retain empty completion marker; no masking |

## Reachability and private-code result

The AST graph resolves 61 production-reachable engine modules and 78 modules
reachable from the four comparison roots, with 59 shared production modules.
The comparison-only set contains the facade/report roots and the real legacy
pipeline/rule/gate/parser/comma graph. No comparison implementation module is a
zero-reach file.

A BOM-aware AST and repository-text audit found:

- private top-level zero-reference functions: **0**;
- proven zero-reach module files: **0**;
- stale production or parser dispatch branches: **0**;
- package-export candidates safe to remove: **0**.

Many owner modules contain structurally identical primitive consumers or
boundary predicates. They are not P8 deletion candidates: they are live and
often encode owner-local accepted domains, failure semantics, or atomic
preserve boundaries. Cross-owner consolidation would be a new production
refactor, not final dead-code cleanup.

## Checkpoint B candidates

### Proven unused imports

| File | Import | Evidence | Action after Checkpoint A |
| --- | --- | --- | --- |
| `engine/span_engine/phone.py` | `is_hyphen_digit_candidate` | never loaded, not exported by `phone`, scanner calls `scan_hyphen_digit_candidates` | remove import only |
| `engine/span_engine/brackets.py` | `Any` | no annotation or runtime load anywhere in the module | remove import only |
| `engine/span_engine/rollout_gate.py` | `export_compare_jsonl`, `export_compare_markdown` | never loaded; artifact writer uses `write_compare_jsonl`/`write_compare_markdown`; exports remain live in `compare` | remove two imports only |

Imports in `engine.span_engine.__init__`, `engine.gates.__init__`, and
`code_separator` that appear unused to a local-name linter are deliberate
package re-exports and must stay.

### Exact duplicate tests

Only duplicates with the same callable, inputs, expected values, assertions,
decorators and no distinct fixture/import/fallback contract qualify:

- the second `abc` preservation assertion in `tests/unit/test_dictionary.py`;
- repeated combined non-string `transform`/`transform_with_trace` guards in
  phase regression files; the dedicated public API tests in
  `test_phase1_public_api.py` retain the same four-value contract for both
  entrypoints;
- the identical phase 19a/19b/18c production regression smoke bodies; retain
  the earliest production-prosody owning copy and remove the two comparison
  phase copies;
- the identical phase 19a/19b compare-module lazy-import assertion; retain one
  import-boundary copy while preserving each file's distinct remaining tests.

Parameterized Batch fixture tests are not duplicates despite identical
function bodies because each module binds a different canonical fixture. Tests
with the same input but different trace, precedence, serialization, fallback,
binary, or source-mapping assertions also remain.

## Documentation consistency result

- P1's complexity table is a historical pre-P1 baseline; its current-result
  sections correctly link P2-P7 and will become the final index in P8-B.
- P2-P7 measurements and module counts are internally consistent with the
  current worktree where they describe their own checkpoints.
- `comparison_tool_support_decision.md` and
  `legacy_comparison_graph_audit.md` agree on retain-and-isolate and the absence
  of a supported shell entrypoint.
- `legacy_test_migration_audit.md` correctly records Batch 1-8 completion and
  exact empty audit state. Its update date and final P8 completion note require
  refresh only after Checkpoint C.
- No current document authorizes whole-input preservation for an internal
  Hangul failure. P7 and the legacy migration audit consistently require
  segment-local preservation.

## Checkpoint A verification

- Canonical Batch/Golden/empty-audit/production-isolation/comparison/CLI set:
  121 passed.
- Full source suite: 6,246 passed and 109 binary tests deselected.
- Golden 13 plus Batch 1-8: 83 cases reconstructed and exact before timing.
- Isolated pre-cleanup performance samples: 1335.21, 1292.66, 1252.39,
  1254.87 and 1296.69 microseconds/input; median/min/max
  1292.66/1252.39/1335.21.
- Production code/test deletions and output diffs at P8-A: zero.
- `tests/_policy_case.py` contains direct equality only; the legacy fixture is
  exact `[]` and no canonical test uses skip/xfail or an expectation mask.

## Leaf-first execution plan

1. Remove the four proven unused imported names and run phone/comparison tests.
2. Remove only the exact duplicate test functions listed above, retaining the
   canonical owning/import-boundary copies, then run every affected file.
3. Convert the parent complexity audit to a final P1-P8 index and refresh the
   legacy/comparison completion notes without rewriting historical evidence.
4. Re-run the AST graph, full source/binary/API parity, archive isolation and
   isolated paired performance before declaring completion.


## Checkpoint B result

- Removed the unused `is_hyphen_digit_candidate` import from the phone owner;
  its live scan path still calls `scan_hyphen_digit_candidates`.
- Removed the unused `Any` import from `brackets.py`; no annotation or runtime
  path consumed it.
- Removed unused `export_compare_jsonl` and `export_compare_markdown` imports
  from `rollout_gate`; those public functions remain implemented, exported and
  tested in `engine.span_engine.compare`.
- Consolidated 44 exact duplicate test functions. Nine test-only files became
  empty or contained only a duplicate function and were removed leaf-first.
  Dedicated public API type guards, the earliest owning production regression,
  policy/precedence/trace tests and comparison import-boundary tests remain.
- The post-cleanup AST duplicate audit reports only the shared Batch test bodies.
  They remain because each module binds a different canonical fixture and thus
  exercises different inputs and expected values.
- No production or comparison function, class, constant, owner branch, package
  export or module file was deleted. No fixture or expected value changed.
- Phone and comparison report/gate target: 18 passed.
- All affected source test files after the first cleanup: 118 passed.
- Complete span-engine plus dictionary checkpoint after all cleanup:
  5,329 passed.

The cleanup changes collection size, not coverage: every removed assertion has
an identical retained execution contract. Checkpoint C must still prove the
complete source/binary/API and archive boundaries and record the final count.


## Checkpoint C and final result

- Final source suite: 6,144 passed and 109 binary tests deselected. The prior
  6,246 count fell by exactly 102 parameterized instances represented by the 44
  removed duplicate functions; no skip or xfail was added.
- Explicit PyInstaller rebuild and local smoke: passed.
- Rebuilt-binary selected set: 109 passed and 6,144 source tests deselected.
- Golden 13 plus Batch 1-8 (70): all 83 source, rebuilt-binary, API and expected
  strings were directly compared and byte-exact.
- Comparison facade/import/CLI/report/gate and production isolation smoke:
  83 passed. Binary archive production-module isolation passed in the selected
  binary suite.
- Final Batch state: Batch 1 stable 2 / allowed 8 applied; Batch 2 stable 14;
  Batch 3 stable 16; Batch 4 stable 7 / allowed 1 applied; Batch 5 stable 5;
  Batch 6 stable 6; Batch 7 stable 5; Batch 8 stable 6.
- Legacy audit remains byte-exact `[]`; `_policy_case.py` has no masking.
- Final private top-level zero-reference functions, proven zero-reach modules
  and real unused imports: zero. Exact duplicate test bodies remain only where
  separate Batch modules bind different fixtures.
- Isolated paired-after performance samples: 1276.38, 1264.34, 1295.75,
  1258.66 and 1257.98 microseconds/input; median/min/max
  1264.34/1257.98/1295.75 versus paired-before
  1292.66/1252.39/1335.21. The median improved about 2.2 percent; WSL/CPU
  scheduling remains uncontrolled.
- Production output differences, expected-value changes, fixture state changes
  and new allowed diffs: zero.

P8 closes the repository-local refactor objective. No mandatory technical
cleanup remains under the current support policy. Retiring `engine.legacy_compare`
and its transitive graph is a separate product and external-compatibility
decision.
