# TTS Preprocessor Deployment Policy

This is the authoritative long-term deployment and runtime policy. Concrete
commands, host addresses, and incident procedures belong in
`docs/deployment_runbook.md`.

## Source-free production runtime

The production API MUST run the packaged PyInstaller executable through
`TTS_PREPROCESSOR_BINARY`:

```text
app/packages/tts-preprocessor/tts-preprocessor
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

Source tests alone are not sufficient. The remote Linux build MUST run the
canonical core semantic runner against:

- the dist binary
- the staging packaged binary
- the published packaged binary

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
sufficient to detect a stale executable. A live API semantic failure retains
the temporary probe/build sources for diagnosis and fails the deployment.

The packaged binary's `--include-debug` payload and API
`include_debug=true` payload may expose `trace.contextual_decision_logs`.
Ordinary binary output and ordinary `/api/transform` responses MUST NOT expose
that field or any decision marker. `shadow_logs` remains the source-preservation
validation stream and MUST NOT be repurposed for contextual decisions.

The optional second-stage LLM receives only the ordinary `normalized_text`
string. Deployment MUST NOT attach `contextual_decision_logs`, candidates,
decision markers, or other rule-engine metadata to that request. The rule
endpoint remains independently usable as a final TTS input path.
The configured default model is `gemma4:31b`; callers may still select another
registered model explicitly. The runtime does not add rule-reading lock
metadata, repeated stability sampling, or automatic retry/fallback generation.

The active prompt MUST present that `normalized_text` as the current execution
payload, outside documentation/example code fences. Response validation MUST
reject any output that changes or removes a source URL, path, filename,
JSON-like block, Markdown inline-code span, SKU-like identifier, or lock token.
This validation is a safety gate; it does not authorize rewriting protected
surfaces or falling back to an unvalidated model response.

`LLM/docs/LLM_prompt.txt` is packaged inside `tts-llm-stage`. Production API
MUST invoke that executable for `/api/llm/models` and `/api/llm/transform`
instead of importing `LLM.*` source. Prompt or model-registry updates therefore
require rebuilding and replacing `tts-llm-stage`. Provider credentials remain
in `config/llm.env` and MUST NOT be embedded in either executable. After
deployment, the active server must be checked through `/api/llm/transform`
when provider credentials and model access are available.

`check_server.sh` is a health/sanity check. Linux and macOS downloads, Web, API
docs, and an API transform sanity response are required. Windows download is
optional. It does not replace the canonical semantic regression probes.

## Protected architecture

Changing this source-free binary-serving architecture to a source-serving
runtime requires explicit approval.
