from __future__ import annotations

import ast
from pathlib import Path


def test_phase31b_api_server_route_contract_still_binary_backed() -> None:
    server_text = Path("api/server.py").read_text(encoding="utf-8")
    tree = ast.parse(server_text)
    imports: list[str] = []
    post_routes: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "post"
                and isinstance(func.value, ast.Name)
                and func.value.id == "app"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                post_routes.append(str(node.args[0].value))

    assert "api.binary_runtime" in imports
    assert all(not name.startswith("engine") for name in imports)
    assert post_routes == ["/api/transform"]
    assert "run_transform_binary" in server_text
    assert "run_transform_binary_with_rollout" in server_text


def test_phase31b_start_server_uses_packaged_binary() -> None:
    start_script = Path("scripts/start_server.sh").read_text(encoding="utf-8")

    assert "packages/tts-preprocessor/bin/tts_preprocessor" in start_script
    assert 'TTS_PREPROCESSOR_BINARY="$LATEST_BINARY"' in start_script
    assert '"$PYTHON_BIN" -m api.server' in start_script
