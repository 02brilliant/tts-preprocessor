# Legacy comparison graph audit

Status: complete (2026-07-14)

This audit records which legacy and comparison modules remain reachable after the
policy expectation audit reached the exact empty state (`[]`). It distinguishes
the production transform graph from the explicitly isolated comparison graph.
An empty policy audit is not evidence that a comparison module is unreachable.

## Audit method

The graph was checked with all of the following, rather than static imports
alone:

- Python imports and literal `importlib.import_module(...)` calls under
  `engine/`, `api/`, `bin/`, `scripts/`, and `tests/`;
- package exports and lazy `__getattr__` exports;
- `python -m` entry points and executable `__main__` blocks;
- scripts, workflows, and documentation that invoke comparison tools;
- PyInstaller hidden imports and exclusions in `tts_preprocessor.spec`;
- tests that monkeypatch `sys.modules` or assert production import boundaries;
- direct and transitive imports rooted at `engine.legacy_compare`.

The production executable explicitly excludes the comparison graph. Production
facades also reject comparison rollout modes and point callers to
`engine.legacy_compare` for explicit comparison. These are intentional boundary
contracts, not proof that the comparison graph itself is dead.

## Supported roots and reachability manifest

| Module or package | Direct inbound | Important outbound | Classification | Decision |
| --- | --- | --- | --- | --- |
| `engine.legacy_compare` | comparison and migration tests; documented by the API error and legacy migration audit | lazy imports of legacy pipeline, legacy comma, paragraph splitting, span comparison and production adapter | explicitly supported developer comparison root; excluded from production binary | retain |
| `engine.span_engine.compare` | `engine.legacy_compare`, `compare_cli`, `rollout_gate`, comparison/report tests | production trace plus optional dynamic legacy resolver | supported comparison/report model | retain |
| `engine.span_engine.compare_cli` | direct dynamic imports from CLI contract tests; no workflow, script, package entry point, or `python -m` block found | `engine.span_engine.compare` | importable developer utility; external support status is not conclusive | retain conservatively |
| `engine.span_engine.rollout_gate` | direct dynamic imports from rollout gate tests; no production caller found | `engine.span_engine.compare` | importable developer report/gate utility; external support status is not conclusive | retain conservatively |
| `engine.pipeline.transform_engine` | lazy import from `engine.legacy_compare`; internal callback from `engine.rules.base_rules` | surfaces, rules, gates, numeric/date and unit/currency parsers | comparison-only runtime reachable | retain while comparison root exists |
| `engine.pipeline.surfaces` | legacy transform engine and legacy comma | none inside the audited graph | comparison-only shared model leaf | retain while its two callers exist |
| `engine.rules.base_rules` | legacy transform engine | gates and all three parser modules; callback to legacy transform engine | comparison-only runtime reachable | retain |
| `engine.gates` and `engine.gates.registry` | legacy transform engine and legacy rules | all gate evaluators and gate models | comparison-only aggregation/runtime reachable | retain |
| `engine.gates.counter_gate` | gates package/registry, legacy transform engine and legacy rules | numeric/date parser | comparison-only runtime reachable | retain |
| `engine.gates.time_gate` | gate registry | numeric/date parser | comparison-only runtime reachable | retain |
| `engine.gates.emergency_gate` | gate registry | gate model | comparison-only runtime reachable | retain |
| `engine.gates.event_gate` | gate registry | gate model | comparison-only runtime reachable | retain |
| `engine.gates.generic_gate` | gate registry and legacy rules | gate model | comparison-only runtime reachable | retain |
| `engine.gates.hyphen_gate` | gate registry | gate model | comparison-only runtime reachable | retain |
| `engine.gates.models` | all gate evaluators/registry | none | comparison-only model leaf, but live | retain |
| `engine.parsers.numeric_date_parsers` | legacy transform engine, legacy rules, special parser, unit/currency parser, counter and time gates | none inside the audited graph | comparison-only parser core, transitively reachable | retain |
| `engine.parsers.special_parsers` | legacy rules | numeric/date parser | comparison-only parser leaf, but live | retain |
| `engine.parsers.unit_currency_parsers` | legacy transform engine and legacy rules | numeric/date parser | comparison-only parser leaf, but live | retain |
| `engine.prosody.comma` | direct lazy import from `engine.legacy_compare`; previously also exposed by an unused package lazy attribute | legacy surface model | comparison-only runtime reachable | retain |
| `engine.prosody.paragraph` | production span transform, `engine.legacy_compare`, and tests | no audited legacy dependency | production runtime reachable | retain; never couple its lifetime to legacy comma |
| `engine.prosody.__init__` | normal package initialization | previously exposed a lazy `insert_commas` attribute | production package; lazy attribute had zero callers | retain package, remove only dead lazy export |

`engine.parsers.dictionary_matcher` is absent in the current worktree and has no
remaining inbound reference. Its deletion predates this audit, so this task does
not claim it as a newly removed file.

## Dynamic and packaging boundaries

`engine.span_engine.compare.get_optional_legacy_transform()` attempts a dynamic
import of `engine.pipeline.core`. That module does not exist in the current tree,
so the resolver returns `None`. This is observable comparison-tool behavior and
is retained until the comparison API itself is explicitly revised. It does not
make the real `engine.pipeline.transform_engine` graph unreachable, because
`engine.legacy_compare.transform_for_comparison()` imports that graph directly.

No lazy export, hidden import, workflow command, script command, documented
`python -m` invocation, or package entry point was found for `compare_cli` or
`rollout_gate`. Both nevertheless have executable, importable APIs covered by
tests. Because external support cannot be disproved from repository evidence,
the conservative rule is to retain those roots.

`tts_preprocessor.spec` excludes `engine.legacy_compare`, `engine.pipeline`,
`engine.parsers`, `engine.rules`, `engine.gates`, `engine.prosody.comma`, and all
three comparison/report modules. Those exclusions remain valuable defense in
depth: the production archive must not gain the comparison graph merely because
a future import changes.

## Deletion candidates and order

The leaf-first audit produced only two independently proven dead paths:

1. the empty-audit masking loader and expectation bypass in
   `tests/_policy_case.py`;
2. the zero-caller lazy `engine.prosody.insert_commas` package export.

After removing those paths, no file in the requested legacy comparison graph is
a safe deletion candidate. The remaining parser/rule/gate/pipeline/comma modules
are transitively reachable from the explicitly retained
`engine.legacy_compare` root. Retiring them would first require a separate,
user-visible decision to retire that comparison facility and its tests.

If that decision is made later, the safe file-removal order is:

1. externally unsupported leaf utilities and their obsolete behavior tests;
2. `engine.prosody.comma`, individual gates, and individual parser leaves after
   their inbound count reaches zero;
3. `engine.rules.base_rules` and `engine.pipeline.surfaces`;
4. `engine.pipeline.transform_engine`;
5. only then `engine.legacy_compare`, followed by any now-unused compare/gate
   report roots.

At every step, the production import-boundary tests and PyInstaller isolation
checks should remain. They express the supported production architecture rather
than the behavior of the old implementation.

## Production P1 follow-up

Production Refactor Batch P1 did not change this comparison graph. The new
`engine.span_engine.prosody_support` module is production-only and is consumed
by the two production prosody adapters. The three removed private functions
belonged only to production owner modules and had zero inbound reference.
`engine.legacy_compare` and every comparison-reachable pipeline/rule/gate/parser
and comma module remain present with the same reachability classification.

## Support-decision execution (2026-07-15)

`docs/comparison_tool_support_decision.md` resolves the repository-evidence
question as **retain and isolate**. The supported developer import facade is
`engine.legacy_compare`; `engine.span_engine.compare` remains its report
implementation. `compare_cli` and `rollout_gate` remain importable compatibility
utilities, but no shell, package-entrypoint, workflow, or deployment support was
found or added. Production continues to reject comparison modes and exclude the
entire graph from its executable archive.

The retained graph was pruned only below its importable roots. Leaf-first AST and
exact-text audits removed 3 private functions and 2 private constants from the
legacy pipeline, 22 private functions and 2 private constants from legacy comma
prosody, and 17 private functions and 17 private constants from legacy rules.
Imports used only by those leaves were also removed. Repeating the audit after
each cascade found no remaining private top-level zero-reference function or
private zero-load module assignment in those three files. No comparison module,
parser, rule, gate, facade, report model, CLI utility, or rollout utility was
deleted.

The facade now declares its exact public Python surface with `__all__`, backed by
characterization tests for modes, injection, production rejection guidance, and
structured error behavior. Retirement of this facade remains an explicit future
product decision, not a consequence of production isolation.


## P8 final reachability recheck

The BOM-aware AST graph, literal dynamic-import scan, package export scan,
PyInstaller check and repository-text audit again found no zero-reach module in
the retained comparison graph and no private top-level zero-reference function.
P8 removed only unused imported names from the rollout utility and exact
duplicate tests whose owning comparison/import-boundary copy remains. The
production archive exclusions and facade smoke tests are unchanged. Thus the
graph remains fully isolated from production but not dead; retiring it is still
a separate product and external-compatibility decision.
