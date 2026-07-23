# Production refactor final report

Status: repository-local refactor complete (2026-07-15)

## Final decision

The policy alignment and behavior-preserving production refactor are complete
under the current support policy. Policy documents, production behavior, Batch
fixtures, owning tests, source/API/binary entrypoints, trace/provenance and
fallback behavior are aligned. No proven private dead code or zero-reach module
remains. The comparison facility is intentionally retained and isolated; its
possible retirement is a separate product compatibility decision.

## Final runtime graphs

```text
production
  engine.main.transform / transform_debug
    -> span_engine.production_adapter
       -> transform_with_trace
          -> language/source/token/shadow
          -> claim scanner -> owner parser -> render
          -> particle exception -> validation
          -> base/extra prosody -> bracket filter
          -> segment-local recovery -> paragraph split
  API and packaged binary -> official production facade

comparison-only developer surface
  engine.legacy_compare
    -> legacy pipeline/rules/gates/parsers/comma
    -> span_engine.compare and production debug/reporting
  compare_cli and rollout_gate -> importable compatibility utilities
```

Production does not import the comparison graph. PyInstaller exclusions and
archive tests enforce that boundary. `engine.prosody.paragraph` remains shared
production/comparison runtime and is not coupled to legacy comma prosody.

## Policy Alignment Batches 1-8

| Batch | Final fixture state | Runtime transition | Result |
| --- | --- | --- | --- |
| 1 | stable 2 / allowed 8 applied | spaced-hyphen and caret-power exact transitions | complete |
| 2 | stable 14 / allowed 0 | none | complete |
| 3 | stable 16 / allowed 0 | none | complete |
| 4 | stable 7 / allowed 1 applied | exact spaced-middle-dot transition | complete |
| 5 | stable 5 / allowed 0 | none | complete |
| 6 | stable 6 / allowed 0 | none | complete |
| 7 | stable 5 / allowed 0 | none | complete |
| 8 | stable 6 / allowed 0 | none | complete |

The deferred legacy policy fixture is the exact JSON array `[]`. Resolved cases
remain in Batch fixtures and owning policy/trace tests; no expectation mask,
skip or audit fallback is used.

## Production Refactor P1-P8

| Batch | Scope | Safe result |
| --- | --- | --- |
| P1 | production graph duplication and private leaves | shared excluded-range/prosody helpers; three proven private leaves removed |
| P2 | range owner | two exact pure mechanisms extracted; owner state machines retained |
| P3 | final number fallback gate | two contiguous owner-deferral predicates extracted |
| P4 | parser dispatch | common core-span Surface assembly extracted; explicit dispatch retained |
| P5 | successful transform trace | parser/render trace projections extracted without ordering changes |
| P6 | shadow validation | consumed-span validation and piece index extracted; decision precedence retained |
| P7 | segment recovery | failed-segment and fallback-trace projections extracted; retry policy retained |
| P8 | final graph/test/docs hygiene | four dead imports and exact duplicate tests removed; graphs reconciled |

All cross-owner primitives that merely look similar remain separate where input
domain, precedence, full-consume, preserve, exception or source-span semantics
differ. No generic registry or retry framework was introduced.

## P8 cleanup details

Removed unused imported names:

- `engine/span_engine/phone.py`: `is_hyphen_digit_candidate`;
- `engine/span_engine/brackets.py`: `Any`;
- `engine/span_engine/rollout_gate.py`: `export_compare_jsonl` and
  `export_compare_markdown` imports only. The public exports remain live in
  `engine.span_engine.compare`.

Consolidated 44 byte-identical test functions. This removed 102 collected
parameterized instances while retaining one canonical owning contract per
group. Nine test-only files became empty or contained only a duplicate and were
removed leaf-first:

- `tests/span_engine/test_phase3_pass_through_regression.py`;
- `tests/span_engine/test_phase5_pass_through_regression.py`;
- `tests/span_engine/test_phase6_pass_through_regression.py`;
- `tests/span_engine/test_phase19a_regression.py`;
- `tests/span_engine/test_phase19b_regression.py`;
- `tests/span_engine/test_phase19d_regression.py`;
- `tests/span_engine/test_phase20d_regression.py`;
- `tests/span_engine/test_phase20h_rollout_gate_helper_regression.py`;
- `tests/span_engine/test_phase25a_regression.py`.

No production/comparison function, class, constant, owner branch, package
export or runtime module was deleted in P8. Remaining duplicate test bodies are
only the deliberately separate Batch fixture runners, whose module globals bind
different canonical fixtures.

## Preserved observable contracts

- claim and parser dispatch order;
- owner, claim type, surface type and reason;
- SourceSpan and RenderPiece order, owner, metadata and provenance;
- parser/render/validation/fallback trace order and serialization;
- no-Hangul global bypass;
- whole-input absolute preserve;
- Hangul segment-local recovery and identical exception metadata;
- public source/API/binary behavior;
- retained comparison facade and importable compatibility utilities.

Normal production output differences, fixture changes and new allowed diffs in
P1-P8: **zero outside the already applied Policy Alignment Batch 1 and Batch 4
contracts**. P8 itself has zero output difference.

## Final verification

- Source suite: **6,144 passed, 109 deselected**.
- Explicit PyInstaller rebuild and local smoke: passed.
- Rebuilt binary selected set: **109 passed, 6,144 deselected**.
- Golden 13 + Batch 1-8 70: **83 source/binary/API/expected byte-exact**.
- Comparison facade/import/CLI/report/gate plus production isolation smoke:
  **83 passed**.
- Binary archive production-module isolation: passed.
- Legacy audit: byte-exact `[]`.
- `tests/_policy_case.py` masking: absent.
- Private top-level zero-reference functions: 0.
- Proven zero-reach runtime modules: 0.
- Real unused imports after cleanup: 0.
- `git diff --check`: passed.
- `.orig`, `.rej`, accidental patch and merge-conflict markers: absent.

Paired isolated 83-case performance:

- before: median/min/max 1292.66/1252.39/1335.21 microseconds/input;
- after: median/min/max 1264.34/1257.98/1295.75 microseconds/input.

The median improved by about 2.2 percent. WSL/CPU scheduling is uncontrolled,
so the exact improvement is not attributed solely to P8; importantly, no
repeatable five-percent regression occurred.

## Remaining work

### Mandatory technical work

None under the current requirements. Future feature or policy changes should be
handled as new scoped work, not as unfinished P8 cleanup.

### Separate product decision

Decide whether the documented Python developer facade
`engine.legacy_compare` is still externally supported. Until an explicit
retirement decision is made, its facade, report model, compatibility utilities
and transitive pipeline/rule/gate/parser/comma graph must remain. If retirement
is authorized, remove it in the leaf-first order already recorded in
`docs/legacy_comparison_graph_audit.md`, while retaining production and binary
isolation tests.
