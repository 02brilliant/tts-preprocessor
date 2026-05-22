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
    assert "$REMOTE_APP_DIR/engine" in deploy
    assert "$REMOTE_APP_DIR/docs" in deploy
    assert "$REMOTE_SCRIPTS_DIR/build_remote_package.sh" in deploy
    assert "$VERSION" not in deploy
    assert "$REMOTE_SCRIPTS_DIR/stop_server.sh" in deploy
    assert "$REMOTE_SCRIPTS_DIR/start_server.sh" in deploy
    assert 'rm -rf "$BUILD_SRC_DIR"' in remote_build
