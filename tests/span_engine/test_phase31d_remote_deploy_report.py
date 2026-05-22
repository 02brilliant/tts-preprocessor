from __future__ import annotations

from pathlib import Path


def test_phase31d_remote_build_script_has_python310_strenum_runtime_hook() -> None:
    script = Path("scripts/build_remote_package.sh").read_text(encoding="utf-8")

    assert 'RUNTIME_HOOK_DIR="$BUILD_SRC_DIR/pyinstaller_runtime_hooks"' in script
    assert 'STR_ENUM_RUNTIME_HOOK="$RUNTIME_HOOK_DIR/enum_strenum_compat.py"' in script
    assert 'if not hasattr(enum, "StrEnum"):' in script
    assert "class StrEnum(str, enum.Enum):" in script
    assert "enum.StrEnum = StrEnum" in script
    assert '--runtime-hook "$STR_ENUM_RUNTIME_HOOK"' in script
