# TTS Preprocessor Deployment Policy

This document is the authoritative deployment/runtime policy for TTS
Preprocessor. It defines MUST / MUST NOT / SHOULD requirements for
source-free production runtime, binary/API contracts, validation ownership, and
protected deployment architecture.

Operator commands, concrete paths, artifact upload steps, and day-to-day
runbook details belong in `docs/deployment_runbook.md`. If this policy
conflicts with a runbook detail, this policy is authoritative for policy
decisions; the runbook is authoritative only for current operational procedure
after it is reconciled with this policy.

## Canonical server runtime model

The production server must not keep source code as the final runtime artifact.

The server deployment flow is:

local source
-> remote temporary buildsrc
-> PyInstaller binary
-> app/packages/tts-preprocessor/bin/tts_preprocessor
-> FastAPI server via TTS_PREPROCESSOR_BINARY
-> /api/transform

`buildsrc` is temporary and must be removed after successful package build.

## Runtime rule

The production API must call the packaged PyInstaller binary via `TTS_PREPROCESSOR_BINARY`.

The production API must not serve transform output by importing `engine.*` source modules from the server filesystem.

If an old or incompatible packaged binary does not support `--rollout-mode` or
`--include-debug`, production runtime must fail as an operational error instead
of falling back to source imports. `TTS_PREPROCESSOR_ALLOW_SOURCE_ROLLOUT_FALLBACK`
is a local/development escape hatch only and must not be enabled in production.

## Official transform entrypoints

The official production source entrypoint is:

```text
engine.main.transform_with_rollout(text, mode="span_default", include_debug=False)
```

This is the source-tree path used to validate production-equivalent output before
building a binary.

The binary runtime entrypoint is:

```text
bin/build_binary_entrypoint.py
-> engine.main.transform_with_rollout(mode="span_default")
```

The API production runtime is:

```text
api.server
-> api.binary_runtime
-> TTS_PREPROCESSOR_BINARY
-> packaged PyInstaller binary
-> bin/build_binary_entrypoint.py
-> engine.main.transform_with_rollout(mode="span_default")
```

`engine.span_engine.transform.transform` is the source transform for span-engine
owner/parser/render development checks. It is not, by itself, the final
production API/binary contract.

`engine.pipeline.transform_engine.transform_text`,
`engine.api_interface.normalize_text`, and `engine.span_engine.production_adapter`
remain compatibility/helper paths. They may be useful in source tests, but
production parity must be judged against the official source entrypoint and the
packaged binary/API runtime.

## Validation rule

Source tests alone are not sufficient for deployment correctness.

Deployment-related changes must preserve:
- remote semantic probe orchestration while `buildsrc` exists
- dist binary semantic probe execution
- packaged binary semantic probe execution
- release packaged binary semantic probe execution
- feature-level semantic probe support for binary/API paths

Local release/build/package responsibility must remain separated:
- `scripts/release.py` owns local release orchestration.
- `scripts/build_package.py` is packaging-only and must not invoke binary build.
- binary build must be performed explicitly before packaging, for example by
  `scripts/release.py` or by an operator following the runbook.

Release/deploy scripts must not own feature-specific expected normalized text.
Feature semantic expectations belong in `tests/probes/` and the `scripts/probes/` probe files that the runner executes.
Release/deploy scripts may orchestrate semantic probes and fail on non-zero exit
status, but they must not duplicate feature policy expected strings.

The canonical semantic probe entrypoint is:

```text
scripts/probes/run_semantic_probes.py
```

This runner defines the core semantic probe suite by default and delegates
feature expectations to the `scripts/probes/` files. Release, deploy, and remote
package build scripts must orchestrate the core runner and judge only its exit
code.

The 12-group scenario regression probe is an extended manual semantic probe,
not a deployment smoke requirement. It can be run directly or through the
runner's `scenario`/`all` suites.

Remote package build must run binary-only semantic probes against the dist
binary and the packaged binary. It must not run source or `production_source`
semantic runners on the remote Python environment.

`check_server.sh` is a server health check. It may include one small API sanity
case, but it is not the canonical semantic regression test. That fixed expected
string is only a wiring canary. Feature semantic validation belongs in
runtime matrix probes labeled `source`, `production_source`, `binary`, and
`api`, such as
`scripts/probes/run_semantic_probes.py --suite core --runtime binary --binary ...`,
`scripts/probes/run_semantic_probes.py --suite core --runtime api --api ...`,
and the manual scenario suite, plus integration parity tests. Existing
individual `scripts/probes/*.py` probe commands remain available for development
and debugging. Canonical feature expectations live in `tests/probes/` and the
probe files consumed by the semantic runner.

Feature-specific semantic probes should use the shared runtime matrix helper
when possible. Probe output must explicitly name `source`,
`production_source`, `binary`, and `api` paths so source-only validation is not
confused with the production binary/API contract.

The old top-level probe command and helper paths have been removed. Use
`scripts/probes/` paths for all probe execution.

## Protected architecture

The deployment architecture must not be changed from source-free server runtime to source-serving runtime without explicit approval.

## Command flow

Concrete command sequences, host-specific URLs, artifact upload steps, and
operator troubleshooting belong in `docs/deployment_runbook.md`. This policy
only defines the decision criteria those commands must satisfy.
