# TTS Preprocessor Deployment Policy

## Local packaged command deadline (2026-10-01)

The API's standard/simplified rule commands, including `--include-debug`, have
an approved default deadline of 30 seconds. The shared local command path also
applies this limit to `--list-models`. Configure it in the server environment as
`TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS`; only finite positive seconds
are accepted. Invalid configuration fails before starting a command.
This is an API subprocess guard, not a new executable/CLI option or TTS profile.
On Linux/macOS, each invocation starts its own process session. On timeout the
API kills that invocation's process group (including ordinary descendant
processes), drains its pipes and reaps the direct child. A parent exiting first
does not prevent cleanup of descendants that retain its pipes. It does not
terminate the API's process group or another request's process.
Timeout raises a distinct runtime error and returns HTTP 504 with the existing
`detail` error schema. No partial output, original-as-success fallback, automatic
retry or new success response fields are allowed. Normal command failures remain
HTTP 500. This does not change stage 0 passthrough, integrated LLM's 20-second
deadline or its existing 5-second rules-only recovery contract.
The API continues to execute packaged binaries without importing engine source.

## Internal presentation coordinates (2026-10-01)

The shared `engine.text_alignment` helper carries bracket/newline/paragraph
coordinates without importing an alternate engine or adding dependencies.
It is statically imported by the existing transform graph and included in the
source/frozen module-boundary inventory. Presentation maps are private metadata;
the public TransformOutput fields and API/CLI/debug schemas remain unchanged.
Fresh-runtime tests cover paragraph-first imports to prevent circular imports.
All four executables retain the existing build and source-free runtime contract;
frozen-runtime verification remains a release gate, not a macOS source check.

## Always-on numeric long-vowel rendering (2026-10-01)

The four existing packaged executables apply the same generated numeric `~`
policy. No feature flag, environment variable, public argument, extra executable
or TTS profile is introduced. Stage 0 remains passthrough. The existing
`numeric_vowels.json` asset now includes three closed month evidence records.
The shared renderer is imported by the existing rule and residual-selection paths.
API-to-binary routing and source-free production are unchanged. Source tests and
local source semantic probes validate output and packaging declarations; they do
not replace frozen-runtime release gates or establish TTS acoustic performance.

## Numeric evidence asset (2026-10-01)

All four existing executable specs include the package-local asset
`engine/span_engine/data/numeric_vowels.json`. The internal loader resolves it
relative to its bundled module, with no dictionary network call at runtime.
Adding this asset does not change source-free production, executable names,
API-to-binary routing, or build ownership. Source tests check all four specs and
the loader schema. Source validation on macOS does not establish Linux frozen
runtime validity; binary-runtime verification belongs to the existing release gates.
The numeric metadata change itself does not require running deployment scripts.

This is the authoritative long-term deployment and runtime policy. Concrete
commands, host addresses, and incident procedures belong in
`docs/deployment_runbook.md`.

## Source-free production runtime

The production API MUST run the packaged PyInstaller executable through
`TTS_PREPROCESSOR_BINARY`:

```text
app/packages/tts-preprocessor/tts-preprocessor-standard
```

The API MUST NOT import `engine.*` to serve production transformations. The
final operating area MUST NOT expose the transformation source tree, tests, or
Python transformation source beside the executable. Temporary `buildsrc` and
staging artifacts MUST be removed after final verification succeeds.

The official build entrypoint remains:

```text
bin/build_binary_entrypoint.py
-> engine.main.transform
```

## Build ownership

| Target | Authoritative build location | Artifact |
|---|---|---|
| Linux production | Existing Ubuntu 22.04 production-server `buildenv` | `tts-preprocessor-linux.zip` |
| macOS Apple Silicon | Apple Silicon Mac project `.venv` | `tts-preprocessor-macos.zip` |
| Windows | GitHub Actions `windows-latest` | `tts-preprocessor-windows.zip` |

Linux production binaries MUST NOT be built on macOS or GitHub Actions. The
existing server `buildenv` MUST be validated and used without creating,
installing, or upgrading it.

All platforms use `bin/build_binary_entrypoint.py` and
`tts_preprocessor.spec`. Python 3.13 provides `enum.StrEnum` natively, so no
StrEnum compatibility runtime hook is packaged.

## Python runtime baseline

Development, tests, the macOS and Windows builds, the Linux production build,
and the source API runtime use standard-GIL CPython 3.13. `.python-version` and
CI pin the currently validated patch release, while build and deployment
preflight checks accept the supported `>=3.13,<3.14` series so that security
patch updates do not require a policy change.

The production server has two independently managed environments:

- `~/tts-preprocessor/.venv` runs the source API and MUST NOT import
  `engine.*` for transformations.
- `~/tts-preprocessor/buildenv` builds the source-free Linux executable.

Both environments MUST use standard-GIL Python 3.13. Deployment validates both
but MUST NOT create, install into, or upgrade either environment. Environment
replacement and rollback are operator-owned pre-deployment procedures.

## Prepare and publish boundary

Linux prepare and the macOS Apple Silicon build MAY run in parallel. Until both
builds and all pre-publish validations succeed, deployment MUST NOT:

- stop the existing server
- change or remove the production Linux executable
- change or remove the production Linux ZIP
- remove the existing macOS or Windows ZIP
- upload a new desktop ZIP

A prepare or macOS build failure MUST remove only the new temporary buildsrc and
staging artifacts. The existing server and all published artifacts remain
unchanged.

Only after both builds succeed may deployment stop the server and enter
publish. Linux publish MUST revalidate its deploy-ID marker, staging paths,
archive SHA-256, archive structure, and executable before changing production
paths.

## Publish failure policy

The server MUST be stopped before Linux publish begins. Publish uses
same-filesystem staging and `mv`, but package and ZIP replacement are not a
single transaction.

Deployment MUST NOT implement automatic backup restoration, rollback state
machines, deployment locks, or a generic transaction system. If publish or a
later artifact step fails:

- commands stop immediately
- the server is not started
- the current partial state is reported
- no speculative artifact deletion or restoration is attempted
- the operator is instructed to run the full deployment again

After Linux publish succeeds, the exact stale macOS and Windows ZIP files are
removed. No wildcard or whole-download-directory deletion is permitted. The
new macOS ZIP MUST come from the same local worktree build, be uploaded through
a temporary name, revalidated remotely, and moved to its final name before the
server starts.

Windows remains a separate manual GitHub Actions build and Windows-only upload
after commit and push. Integrated Linux/macOS deployment MUST NOT build or
upload Windows.

## Validation ownership

Source tests alone are not sufficient. Before the Darwin deployer rsyncs
build sources, it MUST run the canonical core semantic suite against the
local worktree source facade. This catches probe/engine drift before any
remote package is built. The remote Linux build MUST then run the same
canonical core semantic runner against the dist binary. Staging and
published copies MUST match that probed dist by SHA-256 and still pass
simplified smoke plus LLM `--check`; they MUST NOT rerun the full core
suite against identical bytes.

The canonical runner is:

```text
scripts/probes/run_semantic_probes.py
```

Feature expectations live in the probe files consumed by that runner and the
related policy/regression tests, not in release or deployment shell scripts.
Deployment MUST transfer the complete `scripts/probes/` directory as one
canonical probe set; maintaining a second filename allowlist in the deployment
script is forbidden because it can omit a newly registered core probe.
Remote deployment uses binary-only probes and MUST NOT use a source fallback.
The local pre-rsync gate uses the worktree source facade and MUST NOT be
treated as a substitute for the later binary and live-API gates.

Uncommitted and untracked files under `engine/`, `bin/`, `LLM/`, the
PyInstaller spec files, and `scripts/probes/` are part of the packaged
worktree. When any of those paths are dirty, the deploy ID MUST include a
`-dirty` marker and the deployer MUST print the packaged-path status. A
clean HEAD commit hash alone MUST NOT be read as proof that the running
binary matches the operator's latest local edits.

## Retired transition surfaces

Full activation has one production binary path and one mode-less source
facade. The following transition surfaces are removed and MUST NOT be
reintroduced:

- source debug fallback for packaged binaries without `--include-debug`
- adapter-level rollout/payload wrappers and ignored prosody switches
- ignored positional version arguments in local release/package scripts
- dual-run or shadow-mode output selection

An executable that lacks the current debug contract is stale and MUST fail
validation so that it can be rebuilt. The API runtime MUST NOT import
`engine.*` as a fallback. `engine.span_engine.shadow` remains in use solely for
source-preservation validation; it is not a rollout mechanism.

After the server starts, deployment MUST run the same core suite through the
live API before deleting temporary `buildsrc`. This API gate verifies that the
running process actually selected the just-published
`TTS_PREPROCESSOR_BINARY`; download checks and a single wiring canary are not
sufficient to detect a stale executable. Core probes MUST include registered
unit surfaces that a committed-HEAD binary would leave literal, currently
`1㎘당`, `1만㎡`, `수 km`, `지상 3층`, `3.5만kg`, and `45~50만kg`. A live API
semantic failure retains
the temporary probe/build sources for diagnosis and fails the deployment.

The packaged binary's `--include-debug` payload and API
`include_debug=true` payload may expose `trace.contextual_decision_logs`.
Ordinary binary output and ordinary `/api/transform` responses MUST NOT expose
that field or any decision marker. `shadow_logs` remains the source-preservation
validation stream and MUST NOT be repurposed for contextual decisions.

The level-3 and level-4 LLMs receive the ordinary stage base text plus a closed
selection plan containing only candidate IDs, normalized coordinates, finite
outputs, and concise guidance. Level 4 first applies and locks its deterministic
pronunciation overlay. Deployment MUST NOT attach `contextual_decision_logs`,
trace markers, or other rule-engine metadata to the model request. The
integrated runtime may retain an internal normalized-coordinate provenance
snapshot for deterministic response validation. The rule endpoint remains
independently usable as a final TTS input path.
The configured default model is `gemma4-31B-it (vLLM)`; callers may still select another
registered model explicitly. The runtime does not expose rule-reading lock
metadata, use repeated stability sampling, or automatically retry. Levels 3 and 4
fall back to their locked `stage3_base_text` or `stage4_base_text` after a
contract failure, provider timeout, unusable response, or provider outage. A
failed batch does not discard independently validated batches.

Provider deadlines default to 15 seconds. The API limits an integrated LLM
process to 20 seconds and then invokes the same packaged executable with
`--rules-only`, limited to 5 seconds. This preserves the selected stage's
deterministic preprocessing without importing transformation source. Each API
process admits at most four in-flight LLM calls per model. Three consecutive
failures open that model's circuit for 30 seconds; circuit-open and overloaded
requests immediately use the packaged rules-only path. These controls do not
retry the LLM request.

Only code-composed `speech_text` may reach the public API, Web display, copy
surface, or TTS input. Raw/rejected model text, wrappers, JSON, explanations,
and tags MUST NOT be returned through those paths. Public diagnostics are
limited to status/reason fields and optional validation code, severity, and
message without the rejected output.

The active prompt MUST present that `normalized_text` as the current execution
payload, outside documentation/example code fences. Response validation MUST
reject any output that changes or removes a source URL, path, filename,
JSON-like block, Markdown inline-code span, SKU-like identifier, or lock token.
This validation is a safety gate; it does not authorize rewriting protected
surfaces or falling back to an unvalidated model response.

`LLM/docs/LLM_prompt.txt` and `LLM/docs/LLM_prompt_lv3.txt` are packaged only in
levels 3 and 4 respectively. Each integrated executable takes original text, runs
the full level-2 rule engine exactly once, then invokes and validates its fixed
prompt. Production API MUST invoke exactly one selected executable through
`/api/transform` instead of importing `engine.*` or `LLM.*` source. No standalone
`tts-llm-stage` artifact is published. Provider credentials remain in
`config/llm.env` and MUST NOT be embedded in an executable. Public levels are 0,
1, 2, 3, and 4. The level-4 executable packages the shared closed-selection
pipeline and the
unified exact pronunciation registry `LLM/data/stage4_pronunciations.json`, and
applies it once before the model call. Both LLM executables return only
candidate IDs and option indexes; code composes the final speech text.

Every OS package also includes `tts-preprocessor-simplified` beside
`tts-preprocessor-standard`. Both binaries use the same rule engine and managed dictionaries;
the simplified executable disables only general English pronunciation fallbacks.
The existing build and deployment commands build and validate both rule binaries
together with the level-3 and level-4 integrated executables.

`check_server.sh` is a health/sanity check. Linux and macOS downloads, Web, API
docs, and an API transform sanity response are required. Windows download is
optional. It does not replace the canonical semantic regression probes.

## Protected architecture

Changing this source-free binary-serving architecture to a source-serving
runtime requires explicit approval.
