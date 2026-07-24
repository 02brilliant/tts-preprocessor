from __future__ import annotations

import os
import platform
import shutil
import signal
import stat
import subprocess
import textwrap
import time
import zipfile
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_DEPLOY = ROOT_DIR / "scripts/deploy_server.sh"


def _write_executable(path: Path, contents: str) -> None:
    normalized = textwrap.dedent(contents).lstrip().replace(
        "#!/usr/bin/env bash", "#!/bin/bash"
    )
    path.write_text(normalized, encoding="utf-8")
    path.chmod(0o755)


def _prepare_deploy_tree(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    for directory in (
        "scripts",
        "scripts/probes",
        "api",
        "web",
        "engine",
        "bin",
        "pyinstaller_runtime_hooks",
        "docs",
        "downloads",
        "LLM/docs",
    ):
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_DEPLOY, tmp_path / "scripts/deploy_server.sh")
    for relative in (
        "scripts/build_macos_package.sh",
        "scripts/build_remote_package.sh",
        "scripts/upload_desktop_packages.sh",
        "scripts/start_server.sh",
        "scripts/stop_server.sh",
        "scripts/check_server.sh",
        "scripts/probes/__init__.py",
        "scripts/probes/runtime_matrix.py",
        "scripts/probes/run_semantic_probes.py",
        "scripts/probes/decimal_fractional_zero.py",
        "scripts/probes/colon_time_like_policy.py",
        "scripts/probes/large_unit_numeric_surface.py",
        "scripts/probes/json_like_protected_spans.py",
        "tts_preprocessor.spec",
        "bin/build_binary_entrypoint.py",
        "pyinstaller_runtime_hooks/enum_strenum_compat.py",
        "docs/Release_Package_README.txt",
        "LLM/__init__.py",
        "LLM/client.py",
        "LLM/config.py",
        "LLM/gemini_client.py",
        "LLM/models.json",
        "LLM/prompt_template.py",
        "LLM/docs/LLM_prompt.txt",
    ):
        target = tmp_path / relative
        if not target.exists():
            target.write_text("fixture\n", encoding="utf-8")
    (tmp_path / ".venv").symlink_to(ROOT_DIR / ".venv", target_is_directory=True)

    archive_path = tmp_path / "downloads/tts-preprocessor-macos.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        executable = zipfile.ZipInfo("tts-preprocessor")
        executable.create_system = 3
        executable.external_attr = (stat.S_IFREG | 0o755) << 16
        archive.writestr(executable, b"mac-binary")
        archive.writestr("README.txt", b"readme")

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_executable(
        fake_bin / "uname",
        """
        #!/usr/bin/env bash
        if [[ "$1" == "-s" ]]; then printf 'Darwin\n'; else printf 'arm64\n'; fi
        """,
    )
    _write_executable(
        fake_bin / "git",
        """
        #!/usr/bin/env bash
        printf 'd7bb338\n'
        """,
    )
    _write_executable(
        fake_bin / "rsync",
        f"""
        #!/usr/bin/env bash
        printf 'rsync\\n' >> "{calls}"
        """,
    )
    _write_executable(
        fake_bin / "scp",
        f"""
        #!/usr/bin/env bash
        printf 'macos-scp\\n' >> "{calls}"
        exit "${{FAKE_SCP_STATUS:-0}}"
        """,
    )
    _write_executable(
        fake_bin / "curl",
        "#!/usr/bin/env bash\nprintf '200'\n",
    )
    _write_executable(
        fake_bin / "bash",
        f"""
        #!/usr/bin/env bash
        case "${{1:-}}" in
          */build_macos_package.sh)
            printf 'macos-build-start\\n' >> "{calls}"
            trap 'printf "macos-build-terminated\\n" >> "{calls}"; exit 143' TERM INT
            sleep "${{FAKE_MACOS_DELAY:-0}}"
            printf 'macos-build-end\\n' >> "{calls}"
            exit "${{FAKE_MACOS_STATUS:-0}}"
            ;;
          */check_server.sh)
            printf 'final-check\\n' >> "{calls}"
            exit "${{FAKE_CHECK_STATUS:-0}}"
            ;;
        esac
        exec /bin/bash "$@"
        """,
    )
    _write_executable(
        fake_bin / "ssh",
        f"""
        #!/usr/bin/env bash
        payload="$(mktemp)"
        cat > "$payload"
        action=""
        for value in "$@"; do
          case "$value" in
            prepare|publish|cleanup) action="$value" ;;
          esac
        done
        case "$action" in
          prepare)
            printf 'linux-prepare-start\\n' >> "{calls}"
            trap 'printf "linux-prepare-terminated\\n" >> "{calls}"; rm -f "$payload"; exit 143' TERM INT
            sleep "${{FAKE_LINUX_DELAY:-0}}"
            printf 'linux-prepare-end\\n' >> "{calls}"
            rm -f "$payload"
            exit "${{FAKE_LINUX_PREPARE_STATUS:-0}}"
            ;;
          publish)
            printf 'linux-publish\\n' >> "{calls}"
            rm -f "$payload"
            exit "${{FAKE_PUBLISH_STATUS:-0}}"
            ;;
          cleanup)
            printf 'linux-cleanup\\n' >> "{calls}"
            rm -f "$payload"
            exit "${{FAKE_CLEANUP_STATUS:-0}}"
            ;;
          *)
            if grep -q 'buildenv_dir=' "$payload"; then
              printf 'remote-preflight\\n' >> "{calls}"
              status="${{FAKE_PREFLIGHT_STATUS:-0}}"
            elif grep -q 'staged_scripts_dir=' "$payload"; then
              printf 'install-server-scripts\\n' >> "{calls}"
              status="${{FAKE_SCRIPT_INSTALL_STATUS:-0}}"
            elif grep -q 'stop_server.sh' "$payload"; then
              printf 'server-stop\\n' >> "{calls}"
              status="${{FAKE_STOP_STATUS:-0}}"
            elif grep -q 'name __pycache__' "$payload"; then
              printf 'python-bytecode-cleanup\\n' >> "{calls}"
              status="${{FAKE_BYTECODE_CLEANUP_STATUS:-0}}"
            elif grep -q 'tts-preprocessor-windows.zip' "$payload"; then
              printf 'delete-desktop\\n' >> "{calls}"
              status="${{FAKE_DELETE_STATUS:-0}}"
            elif grep -q 'Unexpected uploaded macOS ZIP contents' "$payload"; then
              printf 'macos-remote-publish\\n' >> "{calls}"
              status="${{FAKE_MACOS_REMOTE_STATUS:-0}}"
            elif grep -q 'app/engine' "$payload"; then
              printf 'source-free-cleanup\\n' >> "{calls}"
              status=0
            elif grep -q 'start_server.sh' "$payload"; then
              printf 'server-start\\n' >> "{calls}"
              status="${{FAKE_START_STATUS:-0}}"
            elif grep -q 'rm -f -- "$temp_path"' "$payload"; then
              printf 'macos-temp-cleanup\\n' >> "{calls}"
              status=0
            else
              printf 'ssh-preflight-or-prepare-dir\\n' >> "{calls}"
              status=0
            fi
            ;;
        esac
        rm -f "$payload"
        exit "$status"
        """,
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return tmp_path / "scripts/deploy_server.sh", env, calls


def _run_deploy(
    script: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(script)],
        cwd=script.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _events(calls: Path) -> list[str]:
    return calls.read_text(encoding="utf-8").splitlines()


def _assert_not_run(events: list[str], *forbidden: str) -> None:
    for event in forbidden:
        assert event not in events


def test_deploy_contract_has_stop_before_publish_and_deploy_id() -> None:
    deploy = SOURCE_DEPLOY.read_text(encoding="utf-8")

    linux_start = deploy.index("run_remote_build_action prepare")
    macos_start = deploy.index('bash "$MACOS_BUILD_SCRIPT"')
    first_wait = deploy.index('wait "$LINUX_BUILD_PID"')
    stop = deploy.index("if ! stop_remote_server")
    bytecode_cleanup = deploy.index("if ! clear_remote_python_bytecode")
    publish = deploy.index("if ! run_remote_build_action publish")
    install_scripts = deploy.index("if ! install_remote_server_scripts")
    desktop_delete = deploy.index(
        '"$downloads_dir/tts-preprocessor-macos.zip"'
    )
    scp = deploy.index('scp -- "$LOCAL_MACOS_ARCHIVE"')
    start = deploy.index("if ! start_remote_server")
    check = deploy.index('bash "$CHECK_SERVER_SCRIPT"')

    assert linux_start < first_wait
    assert macos_start < first_wait
    assert (
        first_wait
        < stop
        < bytecode_cleanup
        < publish
        < install_scripts
        < desktop_delete
        < scp
        < start
        < check
    )
    assert '"$downloads_dir/tts-preprocessor-windows.zip"' in deploy
    assert "*.zip" not in deploy
    assert "prepare-$DEPLOY_ID.log" in deploy
    assert '"$action" "$deploy_id"' in deploy
    assert "--platform windows" not in deploy
    assert '"$REMOTE_APP_DIR/api"' in deploy
    assert '"$REMOTE_LLM_DIR"' in deploy
    assert 'find "$api_dir" "$llm_dir"' in deploy
    assert "-name __pycache__" in deploy
    assert "--delete-excluded" not in deploy


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_remote_preflight_failure_stops_before_source_sync(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_PREFLIGHT_STATUS"] = "40"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert events == ["remote-preflight"]
    _assert_not_run(
        events,
        "rsync",
        "linux-prepare-start",
        "macos-build-start",
        "server-stop",
    )


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
@pytest.mark.parametrize(
    ("failure_variable", "failure_value"),
    [
        ("FAKE_MACOS_STATUS", "42"),
        ("FAKE_LINUX_PREPARE_STATUS", "43"),
    ],
)
def test_parallel_build_failure_waits_both_then_cleans_without_stopping_server(
    tmp_path: Path,
    failure_variable: str,
    failure_value: str,
) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env[failure_variable] = failure_value
    if failure_variable == "FAKE_LINUX_PREPARE_STATUS":
        env["FAKE_MACOS_DELAY"] = "0.2"
    else:
        env["FAKE_LINUX_DELAY"] = "0.2"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert "linux-prepare-end" in events
    assert "macos-build-end" in events
    assert events.index("linux-prepare-end") < events.index("linux-cleanup")
    assert events.index("macos-build-end") < events.index("linux-cleanup")
    _assert_not_run(
        events,
        "server-stop",
        "linux-publish",
        "delete-desktop",
        "macos-scp",
        "server-start",
    )
    assert "existing server and production artifacts were retained" in result.stderr
    assert "linux-prepare-" in result.stderr
    assert "macos-build-" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_term_terminates_parallel_children_without_stop_or_publish(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_LINUX_DELAY"] = "10"
    env["FAKE_MACOS_DELAY"] = "10"
    process = subprocess.Popen(
        ["/bin/bash", str(script)],
        cwd=script.parent.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if calls.exists():
            started = _events(calls)
            if (
                "linux-prepare-start" in started
                and "macos-build-start" in started
            ):
                break
        time.sleep(0.05)
    else:
        process.kill()
        raise AssertionError("parallel fixture workers did not start")

    process.send_signal(signal.SIGTERM)
    _, stderr = process.communicate(timeout=5)

    assert process.returncode != 0
    events = _events(calls)
    assert "linux-prepare-terminated" in events
    assert "macos-build-terminated" in events
    _assert_not_run(
        events,
        "server-stop",
        "linux-publish",
        "delete-desktop",
        "server-start",
    )
    assert "terminating parallel build children" in stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_server_stop_failure_prevents_publish_and_cleans_staging(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_STOP_STATUS"] = "51"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert "server-stop" in events
    assert "linux-cleanup" in events
    _assert_not_run(
        events,
        "python-bytecode-cleanup",
        "linux-publish",
        "delete-desktop",
        "macos-scp",
        "server-start",
    )


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_publish_failure_leaves_server_stopped_and_desktops_untouched(
    tmp_path: Path,
) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_PUBLISH_STATUS"] = "52"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert events.index("server-stop") < events.index("linux-publish")
    _assert_not_run(events, "delete-desktop", "macos-scp", "server-start")
    assert "server remains stopped" in result.stderr
    assert "run the full deployment again" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_bytecode_cleanup_failure_prevents_publish_and_restart(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_BYTECODE_CLEANUP_STATUS"] = "58"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert events.index("server-stop") < events.index("python-bytecode-cleanup")
    assert "linux-cleanup" in events
    _assert_not_run(
        events,
        "linux-publish",
        "delete-desktop",
        "macos-scp",
        "server-start",
    )
    assert "Python bytecode cleanup failed" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_desktop_delete_failure_stops_before_upload_and_start(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_DELETE_STATUS"] = "53"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert events.index("linux-publish") < events.index("delete-desktop")
    _assert_not_run(events, "macos-scp", "server-start")
    assert "Linux publish succeeded" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_server_script_install_failure_stops_before_desktop_changes(
    tmp_path: Path,
) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_SCRIPT_INSTALL_STATUS"] = "57"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert events.index("linux-publish") < events.index("install-server-scripts")
    _assert_not_run(events, "delete-desktop", "macos-scp", "server-start")
    assert "server script installation failed" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
@pytest.mark.parametrize(
    "failure_variable",
    ["FAKE_SCP_STATUS", "FAKE_MACOS_REMOTE_STATUS"],
)
def test_macos_upload_failure_never_starts_server(
    tmp_path: Path,
    failure_variable: str,
) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env[failure_variable] = "54"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert "linux-publish" in events
    assert "delete-desktop" in events
    assert "macos-scp" in events
    _assert_not_run(events, "server-start")
    assert "server remains stopped" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_successful_deploy_orders_all_operations_and_cleanup(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)

    result = _run_deploy(script, env)

    assert result.returncode == 0, result.stderr
    events = _events(calls)
    stop = events.index("server-stop")
    publish = events.index("linux-publish")
    bytecode_cleanup = events.index("python-bytecode-cleanup")
    install_scripts = events.index("install-server-scripts")
    delete = events.index("delete-desktop")
    scp = events.index("macos-scp")
    macos_publish = events.index("macos-remote-publish")
    source_cleanup = events.index("source-free-cleanup")
    start = events.index("server-start")
    check = events.index("final-check")
    cleanup = events.index("linux-cleanup")
    assert (
        stop
        < bytecode_cleanup
        < publish
        < install_scripts
        < delete
        < scp
        < macos_publish
        < source_cleanup
        < start
        < check
        < cleanup
    )


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_start_or_final_check_failure_never_runs_rollback(tmp_path: Path) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_CHECK_STATUS"] = "55"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert "server-start" in events
    assert "final-check" in events
    assert "linux-cleanup" not in events
    assert "rollback" not in SOURCE_DEPLOY.read_text(encoding="utf-8").lower()
    assert "final verification failed" in result.stderr


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64",
    reason="deploy execution fixtures require the project Apple Silicon environment",
)
def test_cleanup_failure_preserves_running_deployment_and_reports_retry(
    tmp_path: Path,
) -> None:
    script, env, calls = _prepare_deploy_tree(tmp_path)
    env["FAKE_CLEANUP_STATUS"] = "56"

    result = _run_deploy(script, env)

    assert result.returncode != 0
    events = _events(calls)
    assert "server-start" in events
    assert "final-check" in events
    assert "linux-cleanup" in events
    assert "running service was retained" in result.stderr
    assert "build_remote_package.sh cleanup" in result.stderr
