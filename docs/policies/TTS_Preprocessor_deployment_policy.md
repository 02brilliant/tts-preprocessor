# TTS Preprocessor Deployment Policy

This document defines the canonical deployment and runtime model.

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

Release/deploy scripts must not own feature-specific expected normalized text.
Feature semantic expectations belong in tests and `scripts/probes/` probe files.
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

`check_server.sh` is a server health check. It may include a small API sanity
case, but it is not the canonical semantic regression test. Feature semantic
validation belongs in source/main/binary/API matrix probes such as
`scripts/probes/run_semantic_probes.py --suite core --runtime binary --binary ...`,
`scripts/probes/run_semantic_probes.py --suite core --runtime api --api ...`,
and the manual scenario suite, plus integration parity tests. Existing
individual `scripts/probes/*.py` probe commands remain available for development
and debugging.

Feature-specific semantic probes should use the shared runtime matrix helper
when possible. Probe output must explicitly name `source`,
`production_source`, `binary`, and `api` paths so source-only validation is not
confused with the production binary/API contract.

The old top-level probe command and helper paths have been removed. Use
`scripts/probes/` paths for all probe execution.

## Protected architecture

The deployment architecture must not be changed from source-free server runtime to source-serving runtime without explicit approval.

## Command flow

Local release package creation is for local validation and manual package
inspection:

```text
bash scripts/build_binary.sh
python scripts/release.py
```

Server deployment should be centered on the remote build/package/restart flow:

```text
bash scripts/deploy_server.sh
bash scripts/check_server.sh
```

After deployment, feature-level API validation must be run through the semantic
probes, for example:

```text
python3 scripts/probes/run_semantic_probes.py --suite core --runtime api --api http://10.20.10.162:8010
```

Manual/extended scenario validation can be run separately:

```text
python3 scripts/probes/scenario_regression.py
python3 scripts/probes/run_semantic_probes.py --suite scenario
python3 scripts/probes/run_semantic_probes.py --suite all
python3 scripts/probes/run_semantic_probes.py --suite scenario --runtime api --api http://10.20.10.162:8010
```

Individual probe execution remains available for development/debugging:

```text
python3 scripts/probes/run_semantic_probes.py --suite core
python3 scripts/probes/decimal_fractional_zero.py
python3 scripts/probes/colon_time_like_policy.py
python3 scripts/probes/large_unit_numeric_surface.py
python3 scripts/probes/json_like_protected_spans.py
```
