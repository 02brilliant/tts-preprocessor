from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT = ROOT_DIR / "scripts/build_remote_package.sh"
DEPLOY_ID = "20260723T153012Z-12345-d7bb338"


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(textwrap.dedent(contents).lstrip(), encoding="utf-8")
    path.chmod(0o755)


def _prepare_remote_tree(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "remote-root"
    scripts_dir = root / "scripts"
    buildsrc = root / "buildsrc"
    buildenv_bin = root / "buildenv" / "bin"
    package_dir = root / "app/packages/tts-preprocessor"
    downloads_dir = root / "app/downloads"
    fake_bin = tmp_path / "fake-bin"

    scripts_dir.mkdir(parents=True)
    buildenv_bin.mkdir(parents=True)
    (buildsrc / "engine").mkdir(parents=True)
    (buildsrc / "bin").mkdir()
    (buildsrc / "docs").mkdir()
    (buildsrc / "scripts/probes").mkdir(parents=True)
    (buildsrc / "pyinstaller_runtime_hooks").mkdir()
    package_dir.mkdir(parents=True)
    downloads_dir.mkdir(parents=True)
    fake_bin.mkdir()

    shutil.copy2(SCRIPT, scripts_dir / SCRIPT.name)
    (buildsrc / "bin/build_binary_entrypoint.py").write_text(
        "raise SystemExit('fixture only')\n", encoding="utf-8"
    )
    (buildsrc / "tts_preprocessor.spec").write_text(
        "# fixture spec\n", encoding="utf-8"
    )
    (buildsrc / "docs/Release_Package_README.txt").write_text(
        "new readme\n", encoding="utf-8"
    )
    (buildsrc / "scripts/probes/run_semantic_probes.py").write_text(
        "# intercepted by fake buildenv python\n", encoding="utf-8"
    )
    (buildsrc / "pyinstaller_runtime_hooks/enum_strenum_compat.py").write_text(
        "# fixture hook\n", encoding="utf-8"
    )

    old_binary = package_dir / "tts-preprocessor"
    old_binary.write_bytes(b"old-package")
    old_binary.chmod(0o755)
    (package_dir / "README.txt").write_text("old readme\n", encoding="utf-8")
    (downloads_dir / "tts-preprocessor-linux.zip").write_bytes(b"old-linux-zip")
    (downloads_dir / "tts-preprocessor-macos.zip").write_bytes(b"old-macos")
    (downloads_dir / "tts-preprocessor-windows.zip").write_bytes(b"old-windows")
    (downloads_dir / "keep-me.txt").write_text("keep\n", encoding="utf-8")

    _write_executable(buildenv_bin / "pip", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(
        buildenv_bin / "python",
        f"""
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "${{1:-}}" == "-c" ]]; then
          printf '%s\\n' "${{FAKE_PYTHON_RUNTIME:-3.13:0}}"
          exit 0
        fi
        if [[ "${{1:-}}" == "-" ]]; then
          if [[ "${{FAKE_ZIP_INVALID:-0}}" == "1" ]]; then
            printf 'not-a-zip' > "$3"
            exit 0
          fi
          exec "{sys.executable}" "$@"
        fi
        binary_path=""
        while [[ $# -gt 0 ]]; do
          if [[ "$1" == "--binary" ]]; then
            binary_path="$2"
            break
          fi
          shift
        done
        case "${{FAKE_PROBE_FAILURE:-none}}" in
          dist)
            [[ "$binary_path" == */dist/tts_preprocessor ]] && exit 31
            ;;
          prepared)
            [[ "$binary_path" == *".tts-preprocessor.prepare."* ]] && exit 32
            ;;
          published)
            [[ "$binary_path" == */app/packages/tts-preprocessor/tts-preprocessor ]] && exit 33
            ;;
        esac
        exit 0
        """,
    )
    _write_executable(
        buildenv_bin / "pyinstaller",
        """
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "${1:-}" == "--version" ]]; then
          printf '%s\n' "6.21.0"
          exit 0
        fi
        mkdir -p dist
        printf '%s\n' "new-package" > dist/tts_preprocessor
        chmod +x dist/tts_preprocessor
        """,
    )

    real_mv = shutil.which("mv")
    assert real_mv
    _write_executable(
        fake_bin / "mv",
        f"""
        #!/usr/bin/env bash
        set -euo pipefail
        joined=" $* "
        if [[ "${{FAKE_MV_FAILURE:-none}}" == "package" \
          && "$joined" == *".tts-preprocessor.prepare.{DEPLOY_ID}/tts-preprocessor "* \
          && "$joined" == *"/app/packages/tts-preprocessor "* ]]; then
          exit 41
        fi
        if [[ "${{FAKE_MV_FAILURE:-none}}" == "archive" \
          && "$joined" == *".tts-preprocessor-linux.prepare.{DEPLOY_ID}.zip "* ]]; then
          exit 42
        fi
        exec "{real_mv}" "$@"
        """,
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return root, env


def _run_remote_build(
    root: Path,
    env: dict[str, str],
    action: str,
    deploy_id: str = DEPLOY_ID,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(root / "scripts" / SCRIPT.name), action, deploy_id],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_old_release_preserved(root: Path) -> None:
    assert (
        root / "app/packages/tts-preprocessor/tts-preprocessor"
    ).read_bytes() == b"old-package"
    assert (
        root / "app/downloads/tts-preprocessor-linux.zip"
    ).read_bytes() == b"old-linux-zip"
    assert (
        root / "app/downloads/tts-preprocessor-macos.zip"
    ).read_bytes() == b"old-macos"
    assert (
        root / "app/downloads/tts-preprocessor-windows.zip"
    ).read_bytes() == b"old-windows"


def _prepare_successfully(root: Path, env: dict[str, str]) -> None:
    result = _run_remote_build(root, env, "prepare")
    assert result.returncode == 0, result.stderr


def test_dist_probe_failure_cleans_staging_and_preserves_release(tmp_path: Path) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    env["FAKE_PROBE_FAILURE"] = "dist"

    result = _run_remote_build(root, env, "prepare")

    assert result.returncode != 0
    _assert_old_release_preserved(root)
    assert not (
        root / f"app/packages/.tts-preprocessor.prepare.{DEPLOY_ID}"
    ).exists()
    assert not (
        root / f"app/downloads/.tts-preprocessor-linux.prepare.{DEPLOY_ID}.zip"
    ).exists()


def test_python_version_mismatch_fails_before_build(tmp_path: Path) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    env["FAKE_PYTHON_RUNTIME"] = "3.10:0"

    result = _run_remote_build(root, env, "prepare")

    assert result.returncode != 0
    assert "standard-GIL Python 3.13.x" in result.stderr
    _assert_old_release_preserved(root)


def test_prepared_probe_failure_cleans_staging_and_preserves_release(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    env["FAKE_PROBE_FAILURE"] = "prepared"

    result = _run_remote_build(root, env, "prepare")

    assert result.returncode != 0
    _assert_old_release_preserved(root)
    assert not (
        root / f"app/packages/.tts-preprocessor.prepare.{DEPLOY_ID}"
    ).exists()


def test_zip_validation_failure_cleans_staging_and_preserves_release(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    env["FAKE_ZIP_INVALID"] = "1"

    result = _run_remote_build(root, env, "prepare")

    assert result.returncode != 0
    _assert_old_release_preserved(root)
    assert not (
        root / f"app/downloads/.tts-preprocessor-linux.prepare.{DEPLOY_ID}.zip"
    ).exists()


def test_prepare_success_leaves_verified_deploy_specific_staging(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)

    _prepare_successfully(root, env)

    _assert_old_release_preserved(root)
    prepare_parent = (
        root / f"app/packages/.tts-preprocessor.prepare.{DEPLOY_ID}"
    )
    assert (prepare_parent / "tts-preprocessor/tts-preprocessor").is_file()
    marker = (prepare_parent / "prepare.marker").read_text(encoding="utf-8")
    assert f"deploy_id={DEPLOY_ID}" in marker
    assert "archive_sha256=" in marker
    assert (
        root / f"app/downloads/.tts-preprocessor-linux.prepare.{DEPLOY_ID}.zip"
    ).is_file()


def test_stale_deploy_marker_is_rejected_before_production_changes(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    _prepare_successfully(root, env)
    stale_id = "stale-deploy"
    old_parent = root / f"app/packages/.tts-preprocessor.prepare.{DEPLOY_ID}"
    stale_parent = root / f"app/packages/.tts-preprocessor.prepare.{stale_id}"
    old_parent.rename(stale_parent)
    old_archive = (
        root / f"app/downloads/.tts-preprocessor-linux.prepare.{DEPLOY_ID}.zip"
    )
    stale_archive = (
        root / f"app/downloads/.tts-preprocessor-linux.prepare.{stale_id}.zip"
    )
    old_archive.rename(stale_archive)

    result = _run_remote_build(root, env, "publish", stale_id)

    assert result.returncode != 0
    assert "Invalid or stale prepare marker" in result.stderr
    _assert_old_release_preserved(root)


def test_marker_digest_mismatch_is_rejected_before_production_changes(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    _prepare_successfully(root, env)
    archive_path = (
        root / f"app/downloads/.tts-preprocessor-linux.prepare.{DEPLOY_ID}.zip"
    )
    archive_path.write_bytes(archive_path.read_bytes() + b"tampered")

    result = _run_remote_build(root, env, "publish")

    assert result.returncode != 0
    assert "SHA-256 does not match" in result.stderr
    _assert_old_release_preserved(root)


def test_publish_switches_only_linux_artifacts_without_rollback(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    _prepare_successfully(root, env)

    result = _run_remote_build(root, env, "publish")

    assert result.returncode == 0, result.stderr
    assert (
        root / "app/packages/tts-preprocessor/tts-preprocessor"
    ).read_text(encoding="utf-8") == "new-package\n"
    assert (root / "app/downloads/tts-preprocessor-linux.zip").is_file()
    assert (
        root / "app/downloads/tts-preprocessor-macos.zip"
    ).read_bytes() == b"old-macos"
    assert (
        root / "app/downloads/tts-preprocessor-windows.zip"
    ).read_bytes() == b"old-windows"
    assert (root / "app/downloads/keep-me.txt").read_text(
        encoding="utf-8"
    ) == "keep\n"


def test_publish_failure_does_not_attempt_automatic_restore(tmp_path: Path) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    _prepare_successfully(root, env)
    env["FAKE_MV_FAILURE"] = "archive"

    result = _run_remote_build(root, env, "publish")

    assert result.returncode != 0
    assert not (root / "app/downloads/tts-preprocessor-linux.zip").exists()
    assert (
        root / "app/packages/tts-preprocessor/tts-preprocessor"
    ).read_text(encoding="utf-8") == "new-package\n"
    assert "may be partially updated" in result.stderr
    assert "run the full deployment again" in result.stderr
    assert (
        root / "app/downloads/tts-preprocessor-macos.zip"
    ).read_bytes() == b"old-macos"


def test_published_probe_failure_keeps_partial_publish_and_reports_it(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    _prepare_successfully(root, env)
    env["FAKE_PROBE_FAILURE"] = "published"

    result = _run_remote_build(root, env, "publish")

    assert result.returncode != 0
    assert (
        root / "app/packages/tts-preprocessor/tts-preprocessor"
    ).read_text(encoding="utf-8") == "new-package\n"
    assert (root / "app/downloads/tts-preprocessor-linux.zip").is_file()
    assert "published packaged binary semantic probes failed" in result.stderr
    assert "may be partially updated" in result.stderr


def test_cleanup_is_idempotent_and_never_removes_production_artifacts(
    tmp_path: Path,
) -> None:
    root, env = _prepare_remote_tree(tmp_path)
    _prepare_successfully(root, env)

    first = _run_remote_build(root, env, "cleanup")
    second = _run_remote_build(root, env, "cleanup")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    _assert_old_release_preserved(root)
    assert not (root / "buildsrc").exists()
    assert not (
        root / f"app/packages/.tts-preprocessor.prepare.{DEPLOY_ID}"
    ).exists()
