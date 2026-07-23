from __future__ import annotations

from pathlib import Path


def test_phase31c_deploy_script_target_and_remote_build_cleanup_contract() -> None:
    deploy = Path("scripts/deploy_server.sh").read_text(encoding="utf-8")
    remote_build = Path("scripts/build_remote_package.sh").read_text(encoding="utf-8")

    assert 'REMOTE_USER="brilliant"' in deploy
    assert 'REMOTE_HOST="10.20.10.162"' in deploy
    assert 'REMOTE_BASE_DIR="~/tts-preprocessor"' in deploy
    assert 'REMOTE_APP_DIR="$REMOTE_BASE_DIR/app"' in deploy
    assert 'REMOTE_BUILD_SRC_DIR="$REMOTE_BASE_DIR/buildsrc"' in deploy
    assert 'rsync "${RSYNC_COMMON_ARGS[@]}" "$ROOT_DIR/engine/" "$SSH_TARGET:$REMOTE_BUILD_SRC_DIR/engine/"' in deploy
    assert '"$remote_base_dir/app/engine"' in deploy
    assert '"$remote_base_dir/app/docs"' in deploy
    assert "run_remote_build_action prepare" in deploy
    assert "run_remote_build_action publish" in deploy
    assert "$VERSION" not in deploy
    assert 'bash "$remote_base_dir/scripts/stop_server.sh"' in deploy
    assert 'bash "$remote_base_dir/scripts/start_server.sh"' in deploy
    assert '"$BUILD_SRC_DIR"' in remote_build
    assert 'ARCHIVE_NAME="tts-preprocessor-linux.zip"' in remote_build
    assert 'find "$DOWNLOADS_DIR"' not in remote_build
    assert 'mv -- "$PREPARED_ARCHIVE" "$ARCHIVE_PATH"' in remote_build
    assert "tts-preprocessor-macos.zip" not in remote_build
    assert "tts-preprocessor-windows.zip" not in remote_build
    assert "*.zip" not in remote_build
    assert (
        remote_build.index('mv -- "$PREPARED_ARCHIVE" "$ARCHIVE_PATH"')
        < remote_build.index(
            'run_semantic_probe_set "$PACKAGE_DIR/tts-preprocessor" '
            '"published packaged binary"'
        )
    )
    assert '"$downloads_dir/tts-preprocessor-macos.zip"' in deploy
    assert '"$downloads_dir/tts-preprocessor-windows.zip"' in deploy
    assert "run_remote_build_action cleanup" in deploy
    assert 'python3 -m venv "$BUILD_ENV_DIR"' not in remote_build
    assert "install --quiet --upgrade pip pyinstaller" not in remote_build
    assert '"$BUILD_ENV_DIR/bin/python"' in remote_build
    assert '"$BUILD_ENV_DIR/bin/pip"' in remote_build
    assert '"$BUILD_ENV_DIR/bin/pyinstaller"' in remote_build
    assert "rollback_publish" not in remote_build
    assert "PACKAGE_BACKUP" not in remote_build
    assert "archive_sha256=" in remote_build
