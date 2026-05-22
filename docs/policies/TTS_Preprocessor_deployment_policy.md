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
- remote source smoke
- dist binary smoke
- packaged binary smoke
- release binary smoke
- feature-level semantic probe support for binary/API paths

`check_server.sh` is a server health check. It may include a small API sanity
case, but it is not the canonical semantic regression test. Feature semantic
validation belongs in source/main/binary/API matrix probes such as
`scripts/dev_probe_* --binary` and `scripts/dev_probe_* --api`, plus integration
parity tests.

Feature-specific semantic probes should use the shared runtime matrix helper
when possible. Probe output must explicitly name `source`,
`production_source`, `binary`, and `api` paths so source-only validation is not
confused with the production binary/API contract.

## Protected architecture

The deployment architecture must not be changed from source-free server runtime to source-serving runtime without explicit approval.
