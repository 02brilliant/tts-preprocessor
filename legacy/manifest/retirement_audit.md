# Retirement audit

Status: complete (2026-07-15)

## Decision

The historical comparison facility is unsupported. Current policy, runtime,
tests, packaging, release and deployment use only `engine.main.transform`,
`engine.main.transform_debug`, and the current span production graph. Archived
outputs are not a baseline, fallback, or recovery source.

## Moved files

- comparison implementation source: 23
- comparison-only tests: 41
- historical comparison/refactor documents: 12
- total manifest entries: 76

Every archived Python source/test file has a `.retired` suffix. The archive has
no package marker and is outside pytest's configured `tests` collection root.

## Shared/current files retained

- `engine/prosody/paragraph.py`: production paragraph shaping.
- `engine/span_engine/shadow.py`: current provenance validation input.
- `engine/span_engine/tokenizer.py`: current immutable span tokenization.
- `engine/data/*.production.json`: current managed dictionary inventory.
- Golden 13, Policy Alignment Batch 1~8, owning policy/trace tests, and the
  completed empty policy-audit marker.

## Current references removed

- production API guidance to the retired comparison facade;
- comparison facade/report/CLI/gate exports and source paths;
- comparison-only tests and old tokenizer tests;
- mixed-test comparison assertions while retaining production assertions;
- policy mappings and operational documentation for the retired graph;
- stale PyInstaller exclusions (the source files no longer exist in the current
  source tree).

Production archive isolation now uses a current-module allowlist instead of a
list of retired module names. Pytest collection is explicitly rooted at
`tests/`.

## Build/package boundary

The PyInstaller spec has no data glob, hidden import, or source archive input.
Remote deployment uploads only `bin/`, current `engine/`, probes and the package
README template. Release packages contain the binary and README only. The
archive directory is not copied to buildsrc, package, downloads, or deployment
runtime paths.

## Validation

Baseline before retirement:

- source: 6144 passed, 109 deselected;
- existing binary selected set: 109 passed, 6144 deselected;
- source and binary core semantic probes: passed;
- production output differences: zero.

Final validation with the archive present:

- pytest collection: 6133 current tests; no archived test collected;
- source: 6024 passed, 109 deselected;
- explicit fresh binary build and smoke: passed;
- rebuilt binary selected set: 109 passed, 6024 deselected;
- Golden 13 + Batch 1~8 70: 83 source/binary/API/expected outputs byte-exact;
- current source and packaged-binary core semantic probes: passed;
- package payload: README plus executable only;
- PyInstaller archive: 60 current `engine.*` modules, zero module outside the
  current production allowlist;
- required retired-path search outside this archive: zero matches;
- `git diff --check`: passed.

## Archive-directory deletion simulation

The entire archive directory was moved outside the repository. While it was
absent, `scripts/release.py` completed the source suite, explicit PyInstaller
rebuild, binary selected suite, package build, and packaged-binary core semantic
probes. Source core semantic probes also passed. The independent 83-case
source/binary/API/expected comparison was byte-exact, pytest collected the same
6133 current tests, the package and binary archive were clean, and all required
retired-path searches returned zero matches. The directory was then restored.

The simulation proves that deleting this archive does not change current
runtime, test collection, build, package, release, API, or probe behavior.

## Unresolved items

None. The pre-existing deletion of `engine/parsers/dictionary_matcher.py` was
not restored or archived; it already had zero inbound reference before this
retirement task.
