"""Deploy ID must carry a -dirty marker for packaged worktree dirtiness.

Policy: uncommitted/untracked files under engine/, bin/, LLM/, PyInstaller
specs, and scripts/probes/ require deploy_id ...-dirty and packaged-path status
output. Paths outside that set must not force the marker.
"""

from __future__ import annotations

import importlib.util
import platform
import re
from pathlib import Path

import pytest


def _load_deploy_server_contract():
    path = Path(__file__).with_name("test_deploy_server_contract.py")
    spec = importlib.util.spec_from_file_location(
        "deploy_server_contract_helpers", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DEPLOY = _load_deploy_server_contract()
SOURCE_DEPLOY = _DEPLOY.SOURCE_DEPLOY
_prepare_deploy_tree = _DEPLOY._prepare_deploy_tree
_run_deploy = _DEPLOY._run_deploy
_write_executable = _DEPLOY._write_executable


PACKAGED_PATHSPEC = (
    "engine",
    "bin",
    "LLM",
    "tts_preprocessor.spec",
    "tts_preprocessor_simplified.spec",
    "tts_preprocessor_llm_minimal.spec",
    "tts_preprocessor_llm_natural.spec",
    "scripts/probes",
)

DEPLOY_ID_RE = re.compile(
    r"^\[deploy\] Deploy ID: (?P<deploy_id>[A-Za-z0-9._-]+)\s*$",
    re.MULTILINE,
)


def _install_pathspec_aware_fake_git(*, tmp_path: Path) -> None:
    """Emit FAKE_GIT_PORCELAIN only when it matches packaged status pathspecs."""

    _write_executable(
        tmp_path / "fake-bin" / "git",
        r"""
        #!/usr/bin/env bash
        while [[ "${1:-}" == "-C" ]]; do
          shift 2
        done
        case "${1:-}" in
          rev-parse) printf 'd7bb338\n' ;;
          status)
            shift
            while [[ $# -gt 0 && "$1" != "--" ]]; do
              shift
            done
            if [[ "${1:-}" == "--" ]]; then
              shift
            fi
            porcelain="${FAKE_GIT_PORCELAIN:-}"
            if [[ -z "$porcelain" ]]; then
              exit 0
            fi
            # porcelain is "XY path" (two status chars, space, then path)
            dirty_path="${porcelain:3}"
            matched=0
            for spec in "$@"; do
              case "$dirty_path" in
                "$spec"|"$spec"/*)
                  matched=1
                  break
                  ;;
              esac
            done
            if [[ "$matched" -eq 1 ]]; then
              printf '%s\n' "$porcelain"
            fi
            exit 0
            ;;
          *) printf 'd7bb338\n' ;;
        esac
        """,
    )


def _deploy_id_from_stdout(stdout: str) -> str:
    match = DEPLOY_ID_RE.search(stdout)
    assert match is not None, f"Deploy ID not found in stdout:\n{stdout}"
    return match.group("deploy_id")


def test_deploy_script_documents_dirty_marker_contract() -> None:
    deploy = SOURCE_DEPLOY.read_text(encoding="utf-8")

    assert 'SOURCE_REVISION="${SOURCE_REVISION}-dirty"' in deploy
    assert "Packaging uncommitted or untracked files from the worktree." in deploy
    assert "Production serves the rebuilt binary, not live engine source." in deploy
    assert "DEPLOY_ALLOW_DIRTY=1" in deploy
    assert "enforce_clean_packaged_tree" in deploy
    status_block_start = deploy.index("PACKAGED_TREE_STATUS=\"$(")
    status_block_end = deploy.index(")\"", status_block_start)
    status_block = deploy[status_block_start:status_block_end]
    for path in PACKAGED_PATHSPEC:
        assert path in status_block


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
@pytest.mark.parametrize(
    ("porcelain", "expect_dirty"),
    [
        ("", False),
        (" M engine/foo.py", True),
        ("?? scripts/probes/new_probe.py", True),
        (" M docs/TTS_Preprocessor_policy.md", False),
        (" M tests/policy/test_api_debug_surface_contract.py", False),
    ],
)
def test_deploy_id_dirty_marker_follows_packaged_pathspec(
    tmp_path: Path,
    porcelain: str,
    expect_dirty: bool,
) -> None:
    script, env, _calls = _prepare_deploy_tree(tmp_path)
    _install_pathspec_aware_fake_git(tmp_path=tmp_path)
    env["FAKE_GIT_PORCELAIN"] = porcelain
    env["FAKE_LOCAL_PROBE_STATUS"] = "41"
    if expect_dirty:
        env["DEPLOY_ALLOW_DIRTY"] = "1"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    deploy_id = _deploy_id_from_stdout(result.stdout)
    if expect_dirty:
        assert deploy_id.endswith("d7bb338-dirty")
        assert (
            "Packaging uncommitted or untracked files from the worktree."
            in result.stdout
        )
        assert (
            "Production serves the rebuilt binary, not live engine source."
            in result.stdout
        )
        assert porcelain.strip() in result.stdout
    else:
        assert deploy_id.endswith("d7bb338")
        assert not deploy_id.endswith("dirty")
        assert (
            "Packaging uncommitted or untracked files from the worktree."
            not in result.stdout
        )


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_packaged_dirty_tree_blocks_without_allow_override(tmp_path: Path) -> None:
    script, env, _calls = _prepare_deploy_tree(tmp_path)
    _install_pathspec_aware_fake_git(tmp_path=tmp_path)
    env["FAKE_GIT_PORCELAIN"] = " M engine/foo.py"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    assert "Packaged paths are dirty" in result.stderr
    assert "DEPLOY_ALLOW_DIRTY=1" in result.stderr
