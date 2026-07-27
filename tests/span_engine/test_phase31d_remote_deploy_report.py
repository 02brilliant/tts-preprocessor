from __future__ import annotations

from pathlib import Path


def test_phase31d_remote_build_uses_native_python313_strenum() -> None:
    script = Path("scripts/build_remote_package.sh").read_text(encoding="utf-8")
    spec = Path("tts_preprocessor.spec").read_text(encoding="utf-8")

    assert "pyinstaller_runtime_hooks" not in script
    assert "tts_preprocessor.spec" in script
    assert "pyinstaller_runtime_hooks" not in spec
    assert "runtime_hooks=[]" in spec
