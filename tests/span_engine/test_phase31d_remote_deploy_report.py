from __future__ import annotations

from pathlib import Path


def test_phase31d_remote_build_script_keeps_shared_strenum_runtime_hook() -> None:
    script = Path("scripts/build_remote_package.sh").read_text(encoding="utf-8")
    spec = Path("tts_preprocessor.spec").read_text(encoding="utf-8")
    hook = Path("pyinstaller_runtime_hooks/enum_strenum_compat.py").read_text(
        encoding="utf-8"
    )

    assert (
        'RUNTIME_HOOK="$BUILD_SRC_DIR/pyinstaller_runtime_hooks/'
        'enum_strenum_compat.py"'
    ) in script
    assert 'if not hasattr(enum, "StrEnum"):' not in script
    assert "cat > \"$STR_ENUM_RUNTIME_HOOK\"" not in script
    assert 'if not hasattr(enum, "StrEnum"):' in hook
    assert "class StrEnum(str, enum.Enum):" in hook
    assert "enum.StrEnum = StrEnum" in hook
    assert "tts_preprocessor.spec" in script
    assert "RUNTIME_HOOK = ROOT_DIR" in spec
    assert "runtime_hooks=RUNTIME_HOOKS" in spec
    assert "raise FileNotFoundError" in spec
