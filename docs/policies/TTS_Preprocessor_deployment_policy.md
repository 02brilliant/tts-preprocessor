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

All platforms use `bin/build_binary_entrypoint.py`, `tts_preprocessor.spec`,
and the shared Python 3.10 `StrEnum` runtime hook.

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
Remote deployment uses binary-only probes and MUST NOT use a source fallback.

`check_server.sh` is a health/sanity check. Linux and macOS downloads, Web, API
docs, and an API transform sanity response are required. Windows download is
optional. It does not replace the canonical semantic regression probes.

## Protected architecture

Changing this source-free binary-serving architecture to a source-serving
runtime requires explicit approval.
