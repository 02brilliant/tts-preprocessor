# Comparison tool support decision

Status: Checkpoints A and B complete (2026-07-15)

## Decision

Retain and isolate the comparison facility. Repository evidence does not
authorize an external compatibility break:

- the current production API rejection message intentionally directs comparison
  users to `engine.legacy_compare`;
- the main policy identifies `engine.legacy_compare` as the explicit comparison
  root;
- the facade, report model, artifact writers, and injected-legacy behavior have
  executable contract tests;
- the production source, API, CLI, and PyInstaller archive deliberately exclude
  the comparison graph.

The facility is a Python developer API, not a production mode. There is no
console-script metadata, package entry point, documented `python -m` command,
module `__main__` block, workflow invocation, or deployment script for the
comparison CLI or rollout gate. Historical phase names do not make those
utilities production surfaces.

## Supported and unsupported surfaces

| Root | Evidence | Classification | Disposition |
| --- | --- | --- | --- |
| `engine.legacy_compare` | current API guidance, policy mapping, direct contract tests | documented developer comparison facade | retain and declare its public Python surface |
| `engine.span_engine.compare` | used by the facade, report/gate utilities, artifact and classifier tests; explicit `__all__` | supported comparison report implementation API | retain, comparison-only |
| `engine.span_engine.compare_cli` | programmatic tests only; no console/module/package entry point | importable compatibility utility, not an official shell CLI | retain without adding an entry point |
| `engine.span_engine.rollout_gate` | programmatic artifact/gate tests only; no workflow or production caller | importable compatibility utility, not a deployment gate | retain without production integration |
| `engine.pipeline`, `engine.rules`, `engine.gates`, `engine.parsers` | reachable from the real legacy baseline | transitive comparison implementation | retain while facade baseline is supported; remove only proven private dead leaves |
| `engine.prosody.comma` | directly imported by the comparison facade | transitive comparison implementation | retain implementation; remove only proven private dead leaves |
| `engine.prosody.paragraph` | production transform and comparison facade | production supported | retain independently of legacy comma |

Production explicitly does not support `legacy_default`,
`span_shadow_compare`, or a `rollout_mode` request field. These modes are
accepted only by the comparison facade. The production binary contains no
comparison or legacy implementation modules.

## Developer facade contract

The supported import root is `engine.legacy_compare`. Its public Python
operations are:

- `transform_for_comparison(text)` for the isolated legacy baseline;
- `transform_with_comparison_rollout(text, mode=..., include_debug=...)` for a
  text result or rollout-shaped debug payload;
- `normalize_comparison_mode(mode)` for the two comparison-only mode names;
- `run_comparison_rollout(...)` and `run_shadow_compare(...)` for structured
  comparison dictionaries;
- `build_shadow_compare_payload(payload, ...)` for a validated mapping input.

Only `legacy_default` and `span_shadow_compare` are valid comparison modes.
Non-string mode or text values raise `TypeError`; unsupported modes raise
`ValueError`; a non-debug facade call raises `RuntimeError` when its selected
comparison transform fails. Debug/report calls retain their structured error
fields.

`engine.span_engine.compare_cli.run_compare_cli(argv)` remains callable for
compatibility and tests, but there is no supported shell command. Similarly,
`engine.span_engine.rollout_gate` remains a programmatic report evaluator and
artifact writer, not a release or deployment gate.

## Isolation contract

- `engine.main`, `engine.api_interface`, `api.server`, binary runtime, and the
  production executable must not import the comparison graph.
- Importing the report/facade modules must not eagerly import the legacy
  pipeline; the baseline is loaded only when actually requested.
- `tts_preprocessor.spec` exclusions remain defense in depth even for removed
  or currently unreachable legacy names.
- Production rejection of `rollout_mode` continues to point explicit Python
  comparison users to `engine.legacy_compare` without exposing comparison in
  the API.

## Verified private dead-leaf result

Repository-wide AST name/attribute counts, exact textual searches, and staged
legacy-baseline tests proved the following private leaves unreachable:

- `engine.pipeline.transform_engine`: 3 private functions and 2 private regex
  constants;
- `engine.prosody.comma`: 22 private functions and 2 private constants;
- `engine.rules.base_rules`: 17 private functions and 17 private constants.

They were removed leaf-first. Imports used only by those symbols were removed
in the same file. A repeated AST and repository-text audit now finds zero
private top-level function or private module assignment with no load in these
three files. No module file was deleted: every requested legacy implementation
module remains transitively reachable from the retained facade.

## Leaf-first execution order

1. Declare and test the minimal `engine.legacy_compare` public surface and exact
   production boundary.
2. Remove the three zero-reference pipeline private leaves and validate the
   actual legacy baseline.
3. Remove zero-reference legacy comma private leaves and validate comparison
   prosody output.
4. Remove zero-reference legacy rule private leaves and validate the entire
   legacy baseline and report/gate utilities.
5. Repeat repository-wide static/dynamic/export reachability; do not delete a
   module or importable compatibility root.

The facade now declares its exact public surface through `engine.legacy_compare.__all__`.
Characterization tests pin that export list, accepted modes, injected-baseline
behavior, production API rejection message, and structured error payload.

Retirement of the facade and its transitive graph remains a separate explicit
product decision. This batch does not create a deprecation clock or infer one
from the absence of a shell entry point.

## Execution validation

- Comparison/support characterization, Batch 1 through 8, Golden, empty-audit,
  and production-isolation checkpoint: 117 tests passed.
- Full source suite: 6,177 passed and 109 binary tests deselected. The four new
  tests pin the retained facade contract.
- Explicit PyInstaller rebuild and smoke: passed. Rebuilt-binary selected set:
  109 passed and 6,177 source tests deselected.
- Golden 13 plus Batch 1 through 8 (70 cases): all 83 source, rebuilt-binary,
  API, and expected strings were byte-exact. Production output differences and
  new allowed diffs: zero.
- Binary archive and production import-boundary recheck: 23 tests passed; no
  comparison module entered the production archive.
- Fixed 83-case in-process samples, using 20 corpus rounds per sample, were
  1244.99, 1234.25, 1690.11, 1242.47, and 1814.76 microseconds per input. The
  median/min/max were 1244.99/1234.25/1814.76. The median is about 4.0 percent
  above the 1197.05 reference and below the five-percent stop threshold. The two
  high samples are consistent with uncontrolled WSL/CPU scheduling; this batch
  removes comparison-only code that production does not import.

`tests/_policy_case.py` remains an exact assertion helper with no masking. The
legacy policy audit remains the JSON empty array, and all Batch fixture states
remain unchanged.


## P8 closing audit

The final P8 graph audit revalidated the **retain and isolate** decision. It
removed only two unused report-export imports from `rollout_gate`; the exports
remain live and public in `engine.span_engine.compare`. The facade, report
model, compatibility CLI utility, rollout utility and all transitively reachable
legacy implementation modules remain present. Duplicate historical tests were
consolidated only where an identical comparison or production contract remains
in an owning test. No supported comparison behavior or import surface changed.
