# Legacy Test Migration Audit

Updated: 2026-07-15

This document records structural migration status only. The authoritative behavior remains the policy documents under docs/policies and the fixed span_default snapshots.

## Current batch

The trial migration found 97 assertions where the legacy expectation differed from the current span output.

- 31 assertions were confirmed by the current policy and migrated to engine.main.transform ownership.
- At that checkpoint, 66 assertions remained on the comparison-only legacy path pending a narrower policy audit; the later direct-import migration below moved the retained expectations into the fixed audit fixture.
- Three additional dual-path test files dropped redundant legacy assertions after their span coverage was verified.
- No span-engine behavior was changed during this migration.

Migrated policy groups:

- counter threshold and suffix spacing: "31명 -> 서른한 명", "31권 -> 서른한 권", "112명 -> 백십이 명"
- current numeric/currency/unit ownership: "1.5조 원 -> 일쩜오 조 원", "₩100.5 -> 백쩜오 원", ambiguous "220V" preserve
- lexical boundary policy: middle-dot preservation, K-Hangul compact reading, non-K single-letter hyphen preservation
- shared-suffix month ranges: "1~11월 -> 일월에서 십일월"
- managed code/dictionary/particle behavior: "D-14 -> 디 십사", "S&P 500 -> 에스앤피 오백", safe generated-surface particle correction
- dotted event context: "12.3 비상계엄은 유지한다 -> 십이삼 비상계엄은 유지한다"

## Policy Alignment Batch 1 resolved decisions

The four implementation conflicts recorded on 2026-07-14 are resolved and removed from the deferred audit.

1. Standalone basic clock boundaries
   - canonical: "0:00 -> 영시", "24:00 -> 이십사시"
2. Spaced numeric hyphen blocks
   - canonical: "1 - 2 - 3 -> 일 - 이 - 삼"
   - the exact source ` - ` separator is retained
3. Registered English unit caret power
   - a numeric prefix plus a registered ASCII-letter unit immediately followed by `^2`/`^3` uses 제곱/세제곱 reading
   - canonical representative: "7m^3 -> 칠 세제곱미터"
   - numeric/ASCII-letter invalid tails remain on their previous processing paths
4. Hangul internal exception recovery
   - only the final failed source segment is preserved; successful segments keep their readings
   - whole-input preserve is limited to no-Hangul global bypass or an entirely absolute-preserve input

## Policy Alignment Batch 2 resolved decisions

Fourteen leading-zero and owner-override rows are resolved by promoting the
current span behavior; this batch has no runtime output diff.

- Bare `01`, `003`, `007`, and `0001` preserve source bytes.
- `ID: 00123` keeps the colon and numeric payload while the registered acronym may read as `아이디`.
- `01명`, `03kg`, `₩01,000`, `09시`, and `07시 05분` preserve under their owner-specific leading-zero boundaries.
- `01월`, `03일`, dotted dates, and phone digit blocks remain narrow registered exceptions.
- `tests/fixtures/batch2_allowed_output_diffs.json` records 14 stable decisions and zero allowed diffs.
- The 14 resolved rows moved to owning policy and trace tests; 46 `needs_policy_audit` rows remain.


## Policy Alignment Batch 3 resolved decisions

Sixteen time, colon, suffix-clock, and phonetic rows are resolved by promoting
the current span behavior; this batch has no runtime output diff.

- `N시` keeps canonical generated spacing before the original `시`, including 오후/밤 context and attached particles.
- Exact zero minutes are omitted after successful time claims, and valid `24:MM` remains strong time.
- One-digit minutes are non-time-like; bare and contextual score/ratio pairs use the semantic-pair owner and `대` rendering.
- `H:MM:SS` and `HH:MM:SS` timecode-like surfaces preserve atomically, including inside ordinary Korean sentences.
- Phonetic processing does not remove suffix-clock owner spacing.
- `tests/fixtures/batch3_allowed_output_diffs.json` records 16 stable decisions and zero allowed diffs.
- The 16 resolved rows moved to owning policy and trace tests; 30 `needs_policy_audit` rows remain.


## Policy Alignment Batch 4 resolved decisions

Eight middle-dot, leading-zero, and dotted-event rows are resolved. Seven
promote current span output and one exact asymmetric spaced-middle-dot boundary
changes at runtime.

- Contiguous middle-dot block modes and leading-zero readings are fixed in the owning matrix.
- Leading-zero suffix-clock and unit guards prevent partial middle-dot readings.
- Strong dotted-event and independent decimal claims remain span-local.
- `tests/fixtures/batch4_allowed_output_diffs.json` records 7 stable decisions and 1 applied exact diff.
- The eight resolved rows moved to owning policy and trace tests; 22 `needs_policy_audit` rows remain.


## Policy Alignment Batch 5 resolved decisions

Five protected-bracket, signed-currency, decimal-precision, and embedded-code
rows are resolved by promoting current span output without a runtime diff.

- Square-bracket interiors remain absolute preserve before currency claims.
- Signed currency and unbounded fractional decimal policies own their complete surfaces.
- `A112` belongs to the single-letter alnum code owner rather than emergency fallback.
- `tests/fixtures/batch5_allowed_output_diffs.json` records 5 stable decisions and zero allowed diffs.
- The five resolved rows moved to owning policy and trace tests; 17 `needs_policy_audit` rows remain.



## Policy Alignment Batch 6 resolved decisions

Six large-number, ordinal, approximate-marker, and counter rows are resolved by
promoting current span output without a runtime diff.

- Ordinary numeric reading supports large groups through `경`; unsupported `해`-width input preserves at the narrow fallback boundary.
- Prefixed ordinals generate canonical spacing after `제`.
- Compact large-unit readings keep attached `여`, comma decimals use compact ordinary integer rendering, and counter owners retain generated suffix spacing.
- `tests/fixtures/batch6_allowed_output_diffs.json` records 6 stable decisions and zero allowed diffs.
- The six resolved rows moved to owning policy and trace tests; 11 `needs_policy_audit` rows remain.


## Policy Alignment Batch 7 resolved decisions

Five prosody insertion rows are resolved by promoting current span output
without a runtime diff.

- Topic length and following frame phrases do not enable a broad comma heuristic.
- Sentence-initial `한편` is not an unconditional comma connector.
- A valid two-clause `-지만` boundary emits source-mapped generated punctuation after numeric and lexical owners render.
- `tests/fixtures/batch7_allowed_output_diffs.json` records 5 stable decisions and zero allowed diffs.
- The five resolved rows moved to owning policy and provenance tests; 6 `needs_policy_audit` rows remain.


## Policy Alignment Batch 8 resolved decisions

Six typed lexical, restricted hyphen range, and shared-month range rows are
resolved by promoting current span output without a runtime diff.

- Registered `장` licenses the narrow `12-15장` range; generic/unsafe hyphens preserve.
- Lexical middle dots remain source-exact while K-Hangul and dictionary owners retain precedence.
- All four owner-local tilde aliases apply the shared `월` reading to both operands.
- `tests/fixtures/batch8_allowed_output_diffs.json` records 6 stable decisions and zero allowed diffs.
- The six resolved rows remain in owning policy/trace tests; the deferred audit is now `[]`.


## Deferred clarification groups

No deferred clarification rows remain. This audit completion does not authorize immediate deletion of the comparison-only legacy graph; import reachability and comparison coverage must be audited separately.



## Direct legacy-import test migration

Completed on 2026-07-14:

- 25 test files that directly imported legacy pipeline, surface, rule, or comma modules now have zero direct legacy imports.
- Simple output contracts call engine.main.transform.
- Surface, owner, particle, and gate contracts use engine.span_engine.transform_with_trace, ClaimedRange, RenderPiece, and the span Surface model.
- Direct comma contracts use the span prosody adapters over source-mapped RenderPiece values, keeping prosody assertions separate from numeric normalization.
- No span-engine runtime behavior was changed.

The migration originally recorded 90 legacy-policy expectation pairs. After promoting 26 fixed span outputs and resolving Policy Alignment Batches 1 through 8, tests/fixtures/legacy_policy_expectation_audit.json is the exact empty JSON array `[]`.

- 0 remain classified as canonical_span; canonical rows belong in the owning policy tests, not the deferred audit.
- 0 remain classified as confirmed_policy_conflict; the four Batch 1 decisions now live in canonical policy tests and the applied allowed-diff fixture.
- 0 are classified as needs_policy_audit.
- The completed fixture contains no disposition rows; historical non-empty rows stored both `policy_expected` and `span_expected`.
- The empty-state regression test requires an exact `[]` fixture and an empty disposition set; resolved behavior remains covered by Batch 1 through 8 fixtures and owning tests.

Reference audit after the batch:

- Test code has zero direct imports from engine.pipeline, engine.rules, engine.prosody.comma, or engine.parsers.*.
- The module-by-module result is recorded in docs/legacy_comparison_graph_audit.md.
- engine.pipeline.transform_engine, engine.pipeline.surfaces, engine.rules.base_rules, the three legacy parser modules, and engine.prosody.comma still reference one another inside the comparison-only legacy graph.
- engine.legacy_compare intentionally remains the root of that comparison-only graph.
- The unused package-level engine.prosody.insert_commas lazy export was removed; engine.legacy_compare continues to import the comparison implementation directly.
- No comparison implementation file is a deletion candidate. Deletion must wait until comparison coverage is moved or retired and each module has zero real imports.

The policy-case helper now performs direct exact equality only. Its empty-audit JSON loading and expectation masking path was removed after the fixture became exact `[]`.

Targeted validation: 585 tests passed for the 25 migrated files plus the fixed audit baseline.


## Mode-less production facade migration

Completed on 2026-07-14:

- engine.main.transform(text) is the official production source facade.
- engine.main.transform_debug(text) is the mode-less debug facade.
- production_adapter exposes only transform_for_production and transform_payload; its rollout mode/controller helpers were removed.
- CLI and PyInstaller no longer accept --rollout-mode.
- API requests no longer declare rollout_mode; extra rollout_mode fields are rejected before binary execution.
- api.binary_runtime exposes separate text and debug helpers without a mode argument.
- The one-cycle rollout compatibility shim has now been removed from engine.main.
- engine.legacy_compare remains comparison-only and is not imported by the production source/binary/API graph.
- Existing output snapshots were not changed.

Removal result:

1. production code, probes, policy docs, and tests have zero calls to the former shim;
2. source callers use transform or transform_debug;
3. dedicated compatibility tests were replaced by mode-less facade export tests;
4. comparison tooling remains separate and was not folded back into engine.main.

Validation before shim removal: 5,997 tests passed, including source/binary/API golden parity and PyInstaller archive isolation.
Validation after shim removal: 5,991 tests passed; the six removed tests covered only the deleted shim contract.


## P8 final test-graph cleanup

The closing refactor audit reconfirmed that every Batch 1 through 8 decision is
retained in its exact fixture and owning policy/trace coverage, and that the
legacy audit is still the exact empty array. Historical phase tests were not
removed by name. Only byte-identical test functions with the same callable,
inputs, expected values and assertions were consolidated, and every group keeps
one canonical public API, policy, trace or import-boundary copy. Batch test
bodies that look structurally identical remain separate because each binds a
different fixture. `tests/_policy_case.py` still performs direct equality with
no audit or expected-value masking.
